# aria/chess_coach/analysis.py
#
# Analyse moteur d'une partie PGN (sprint 26, tronçon 01).
#
# Chaîne : parse_pgn → detect_color → analyze_game → select_critical.
# Toutes les mesures de qualité sont exprimées en points de « % de gain »
# (formule Lichess), du point de vue du joueur qui joue le coup.
# Module pur : aucun import mémoire / LLM / exécution.

import io
import math
import queue
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import chess
import chess.engine
import chess.pgn

from chess_coach.motifs import tag_motifs
from chess_coach.openings import detect_opening, opening_group
from config import config
from logger import get_logger

log = get_logger(__name__)

# Borne des évaluations en centipions avant conversion en % de gain.
_CP_CLAMP = 1000
# Valeur d'un mat converti en centipions (puis borné à ±_CP_CLAMP).
_MATE_SCORE = 100000
# Valeurs des pièces non-pions pour la détection de finale.
_PIECE_VALUES = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}

# Règle « avantage clair, visible pour un humain » (sprint 27, tronçon 08).
# Ligne montrée : plafond normal 10 demi-coups, prolongée au-delà seulement
# tant que les coups sont forcés, borne dure 16. Seuils révisables au run live.
_CLEAR_MAX = 10
_CLEAR_HARD_MAX = 16
_CRUSHING_WIN = 80
_DEVELOPMENT_GAP = 2
_ACTIVITY_GAP = 10
# Longueur de ligne affichée pour les sortes a / b (inchangée).
_PV_DISPLAY = 6
# Suites comparées d'une erreur (sprint 50) : borne en demi-coups, pour tenir dans une légende.
_FORCING_MAX = 10
_FORCING_TIME = 0.15

# Options Stockfish du live et de position_eval (sprint 27) : la machine a 16 cœurs.
ENGINE_OPTIONS = {"Threads": 8, "Hash": 256}
# Marge de réponse de Stockfish, en secondes, au-delà du temps demandé (10 s par défaut).
# La machine peut geler plus de 10 s sous pression mémoire : mieux vaut attendre que perdre l'analyse.
ENGINE_TIMEOUT = 60
# Parties envoyées (sprint 49) : nœuds fixes, 1 thread et hash vidé à chaque appel rendent
# le résultat reproductible ; 8 Stockfish en parallèle compensent la perte de vitesse.
STABLE_ENGINE_OPTIONS = {"Threads": 1, "Hash": 16}
_STABLE_ENGINES = 8
# Nœuds accordés par seconde demandée : les durées des appelants deviennent des nœuds.
_NODES_PER_SECOND = 590000
# Plafond en secondes, jamais atteint en marche normale : python-chess n'applique aucun
# timeout sans limite de temps, un gel de Stockfish bloquerait l'analyse sans fin.
_STABLE_TIME_CAP = 60

# Nom de Nico dans les en-têtes White / Black ; ses pseudos sont dans config.chess_usernames.
NICO_NAME = "Nico"
# Budget de miniatures d'une partie, et premier coup montré (sprint 46).
_CRITICAL_BUDGET = 4
_CRITICAL_FIRST_MOVE = 4
# Göring joué par Nico : ses 6 premiers coups sont le concept du gambit, pas une décision.
_GORING_FIRST_MOVE = 7
# Un coup est une habitude de répertoire dès 2 parties précédentes avec les mêmes coups.
_KNOWN_MOVE_GAMES = 2
_COLOR_RE = re.compile(r"je joue (?:avec )?(?:les )?(noirs|blancs)", re.IGNORECASE)


@dataclass
class PlyAnalysis:
    """Analyse d'un demi-coup joué."""
    ply: int
    move_number: int
    color: str
    san: str
    uci: str
    fen_before: str
    win_before: float
    win_after: float
    loss: float
    best_san: str
    best_uci: str
    pv_san: list
    second_gap: float | None
    quality: str
    phase: str
    tags: list
    clock: float | None
    eval_before_cp: int
    eval_after_cp: int
    # PV du meilleur coup, longue (≤ _CLEAR_HARD_MAX demi-coups, UCI), pour la
    # règle d'avantage clair ; pv_mate : le moteur annonce un mat pour le trait.
    pv_uci: list = field(default_factory=list)
    pv_mate: bool = False
    # Difficulté du coup en Elo (Maia-2, sprint 28) : coups de Nico après le coup 10.
    difficulty: float | None = None
    # Probabilité Maia-2 (Elo de Nico) du coup joué (sprint 29, tronçon 12) : mêmes coups.
    played_p: float | None = None
    # Motifs tactiques du meilleur coup (sprint 29, clés de chess_coach.motifs).
    motifs: list = field(default_factory=list)


@dataclass
class CriticalPosition:
    """Position critique : la position AVANT un coup de Nico."""
    kind: str
    ply: PlyAnalysis
    score: float
    # Sorte d uniquement : coup explosif manqué (chess_coach.explosive.ExplosiveMove).
    explosive: object | None = None
    # Sortes c / e : critère d'avantage clair et ligne coupée au point d'arrêt (SAN).
    evidence: str | None = None
    line_san: list = field(default_factory=list)
    # Sortes a / b : suites forcées du meilleur coup et du coup joué (SAN, ce coup en tête).
    best_line_san: list = field(default_factory=list)
    played_line_san: list = field(default_factory=list)


@dataclass
class GameAnalysis:
    headers: dict
    nico_color: str
    color_source: str
    plies: list = field(default_factory=list)
    critical: list = field(default_factory=list)
    # Toutes les occasions explosives trouvées, retenues ou non (couleur des points de la courbe).
    explosive: list = field(default_factory=list)


def parse_pgn(text: str) -> chess.pgn.Game | None:
    """Lit la partie à partir de la première ligne commençant par « [ ».

    Le message peut contenir du texte libre avant le PGN. Les lignes sont
    dépouillées de leurs blancs : un collage Telegram indente souvent les
    lignes 2+, et read_game ignore un en-tête indenté. Retourne None si
    aucune partie, aucun coup, ou un coup illégal (game.errors non vide).
    """
    lines = [line.strip() for line in text.splitlines()]
    start = next((i for i, line in enumerate(lines) if line.startswith("[")), None)
    if start is None:
        return None
    game = chess.pgn.read_game(io.StringIO("\n".join(lines[start:])))
    if game is None or game.errors or game.next() is None:
        return None
    return game


def split_pgn(text: str) -> list[str]:
    """Découpe un PGN de plusieurs parties : une chaîne par partie (sprint 42).

    Même nettoyage que parse_pgn (lignes dépouillées). Une partie commence à
    une ligne « [ » qui suit une ligne non vide hors en-tête (fin des coups de
    la précédente) ou au tout premier en-tête. Le texte libre avant le premier
    en-tête (légende) est recopié en tête de chaque partie : detect_color y lit
    la couleur de Nico. Sans en-tête, retourne [text].
    """
    lines = [line.strip() for line in text.splitlines()]
    starts, previous = [], None
    for i, line in enumerate(lines):
        if line.startswith("[") and (previous is None or not previous.startswith("[")):
            starts.append(i)
        if line:
            previous = line
    if not starts:
        return [text]
    preface = "\n".join(lines[:starts[0]]).strip()
    games = []
    for start, end in zip(starts, starts[1:] + [len(lines)]):
        game = "\n".join(lines[start:end]).strip()
        games.append(f"{preface}\n\n{game}" if preface else game)
    return games


def detect_color(headers, message: str) -> tuple[str, str]:
    """Couleur de Nico : en-tête PGN (« Nico » ou un pseudo), puis message (« je joue les noirs »), puis blancs."""
    names = {name.lower() for name in (NICO_NAME, *config.chess_usernames)}
    if headers.get("White", "").lower() in names:
        return "white", "header"
    if headers.get("Black", "").lower() in names:
        return "black", "header"
    match = _COLOR_RE.search(message)
    if match:
        return ("black" if match.group(1).lower() == "noirs" else "white"), "message"
    return "white", "default"


def _win(cp: int) -> float:
    """Centipions (point de vue du joueur) → % de gain, formule Lichess."""
    cp = max(-_CP_CLAMP, min(_CP_CLAMP, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def _terminal_cp(board: chess.Board) -> int:
    """Évaluation d'une position terminale, point de vue du trait (mat = perdu)."""
    return -_MATE_SCORE if board.is_checkmate() else 0


def _phase(board: chess.Board, move_number: int) -> str:
    if move_number <= 10:
        return "opening"
    no_queens = not board.pieces(chess.QUEEN, chess.WHITE) and not board.pieces(chess.QUEEN, chess.BLACK)
    material = sum(
        value * (len(board.pieces(piece, chess.WHITE)) + len(board.pieces(piece, chess.BLACK)))
        for piece, value in _PIECE_VALUES.items()
    )
    return "endgame" if no_queens or material <= 13 else "middlegame"


def _tags(board: chess.Board, move: chess.Move) -> list:
    """Étiquettes descriptives du coup joué (board = position AVANT le coup)."""
    tags = []
    mover = board.turn
    piece = board.piece_type_at(move.from_square)
    if board.is_capture(move):
        tags.append("capture")
    if board.gives_check(move):
        tags.append("check")
    if piece == chess.PAWN:
        tags.append("pawn")
    if piece == chess.KING:
        tags.append("king")
    if board.is_castling(move):
        tags.append("castle")
    if piece != chess.PAWN and not board.is_castling(move):
        from_rank, to_rank = chess.square_rank(move.from_square), chess.square_rank(move.to_square)
        if (mover == chess.WHITE and to_rank < from_rank) or (mover == chess.BLACK and to_rank > from_rank):
            tags.append("retreat")
    after = board.copy(stack=False)
    after.push(move)
    for square, own in after.piece_map().items():
        if own.color == mover and own.piece_type != chess.KING \
                and after.is_attacked_by(not mover, square) and not after.is_attacked_by(mover, square):
            tags.append("hanging")
            break
    return tags


def _quality(played_uci: str, best_uci: str, loss: float) -> str:
    if played_uci == best_uci:
        return "best"
    if loss >= 30:
        return "blunder"
    if loss >= 20:
        return "mistake"
    if loss >= 10:
        return "inaccuracy"
    return "correct"


class FixedNodesEngine:
    """Enveloppe d'un SimpleEngine : le temps demandé devient un nombre fixe de nœuds.

    Les appelants n'utilisent que engine.analyse(board, Limit(time=…), **kwargs).
    game=object() change de « partie » à chaque appel, ce qui vide le hash : le
    résultat d'une position ne dépend pas de celles analysées avant elle.
    """

    def __init__(self, engine):
        self._engine = engine

    def analyse(self, board, limit, **kwargs):
        fixed = chess.engine.Limit(nodes=int(limit.time * _NODES_PER_SECOND), time=_STABLE_TIME_CAP)
        return self._engine.analyse(board, fixed, game=object(), **kwargs)


def run_on_engines(engine_path: str, work, items: list) -> list:
    """Applique work(engine, item) sur 8 Stockfish en parallèle, résultats dans l'ordre d'items.

    Chaque moteur ne sert qu'un appel à la fois ; tous sont fermés, y compris sur exception.
    """
    if not items:
        return []
    engines, idle = [], queue.SimpleQueue()

    def open_engine(_):
        engine = chess.engine.SimpleEngine.popen_uci(engine_path, timeout=ENGINE_TIMEOUT)
        engines.append(engine)
        engine.configure(STABLE_ENGINE_OPTIONS)
        idle.put(FixedNodesEngine(engine))

    def run(item):
        engine = idle.get()
        try:
            return work(engine, item)
        finally:
            idle.put(engine)

    try:
        with ThreadPoolExecutor(max_workers=_STABLE_ENGINES) as pool:
            # Ouverture parallèle : à la suite, les 8 démarrages coûtent 31 à 41 s [2 mesures, machine chargée].
            list(pool.map(open_engine, range(_STABLE_ENGINES)))
            return list(pool.map(run, items))
    finally:
        for engine in engines:
            engine.close()


def analyze_game(game, nico_color: str, engine_path: str, time_per_position: float = 0.15) -> list:
    """Analyse chaque position de la partie (N+1 positions) et qualifie chaque demi-coup.

    nico_color n'influe pas sur les mesures (calculées pour les deux camps) ;
    il est gardé dans la signature pour les callers.
    """
    nodes = list(game.mainline())
    boards = [game.board()] + [node.board() for node in nodes]

    def evaluate(engine, board):
        """Une analyse par position : (cp point de vue du trait, infos multipv)."""
        if board.is_game_over():
            return _terminal_cp(board), []
        infos = engine.analyse(board, chess.engine.Limit(time=time_per_position), multipv=2)
        return infos[0]["score"].relative.score(mate_score=_MATE_SCORE), infos

    evaluations = run_on_engines(engine_path, evaluate, boards)

    plies = []
    for i, node in enumerate(nodes):
        board = boards[i]
        move = node.move
        cp_before, infos = evaluations[i]
        # La position suivante est évaluée du point de vue de l'adversaire.
        cp_after = -evaluations[i + 1][0]
        win_before, win_after = _win(cp_before), _win(cp_after)

        best_pv = infos[0]["pv"]
        best_move = best_pv[0]
        pv_san = []
        pv_board = board.copy(stack=False)
        for pv_move in best_pv[:_PV_DISPLAY]:
            pv_san.append(pv_board.san(pv_move))
            pv_board.push(pv_move)
        best_score = infos[0]["score"].relative
        second_gap = None
        if len(infos) >= 2:
            second_cp = infos[1]["score"].relative.score(mate_score=_MATE_SCORE)
            second_gap = win_before - _win(second_cp)

        loss = max(0.0, win_before - win_after)
        sign = 1 if board.turn == chess.WHITE else -1
        plies.append(PlyAnalysis(
            ply=i,
            move_number=board.fullmove_number,
            color="white" if board.turn == chess.WHITE else "black",
            san=board.san(move),
            uci=move.uci(),
            fen_before=board.fen(),
            win_before=win_before,
            win_after=win_after,
            loss=loss,
            best_san=board.san(best_move),
            best_uci=best_move.uci(),
            pv_san=pv_san,
            second_gap=second_gap,
            quality=_quality(move.uci(), best_move.uci(), loss),
            phase=_phase(board, board.fullmove_number),
            tags=_tags(board, move),
            clock=node.clock(),
            eval_before_cp=sign * cp_before,
            eval_after_cp=sign * cp_after,
            pv_uci=[m.uci() for m in best_pv[:_CLEAR_HARD_MAX]],
            pv_mate=best_score.is_mate() and best_score.mate() > 0,
        ))
    return plies


def _material(board: chess.Board, color: chess.Color) -> int:
    """Bilan matériel (color − adversaire), en pions (1/3/3/5/9)."""
    values = {chess.PAWN: 1, **_PIECE_VALUES}
    return sum(
        value * (len(board.pieces(piece, color)) - len(board.pieces(piece, not color)))
        for piece, value in values.items()
    )


def _development(board: chess.Board, color: chess.Color) -> int:
    """Pièces mineures hors de la rangée de départ, + 1 si le roi est roqué (g/c)."""
    home = 0 if color == chess.WHITE else 7
    minors = board.pieces(chess.KNIGHT, color) | board.pieces(chess.BISHOP, color)
    developed = sum(1 for square in minors if chess.square_rank(square) != home)
    castled = board.king(color) in (chess.square(6, home), chess.square(2, home))
    return developed + int(castled)


def _legal_count(board: chess.Board, color: chess.Color) -> int:
    """Coups légaux de color (trait inversé sur une copie si besoin)."""
    if board.turn == color:
        return board.legal_moves.count()
    flipped = board.copy(stack=False)
    flipped.turn = color
    flipped.ep_square = None
    return flipped.legal_moves.count()


def _clear_criterion(start: chess.Board, board: chess.Board, mover: chess.Color) -> str | None:
    """Critère statique (matériel, développement, activité) vrai dans board, ou None."""
    if _material(board, mover) - _material(start, mover) >= 1:
        return "material"
    if _development(board, mover) - _development(board, not mover) >= _DEVELOPMENT_GAP:
        return "development"
    flipped = board.copy(stack=False)
    flipped.turn = not board.turn
    if not board.is_check() and not flipped.is_check():
        if _legal_count(board, mover) - _legal_count(board, not mover) >= _ACTIVITY_GAP:
            return "activity"
    return None


def clear_advantage(board: chess.Board, line: list, win: float, mate: bool) -> tuple | None:
    """Point d'arrêt d'une ligne où l'avantage du trait devient clair pour un humain.

    board = position avant le coup évalué (le trait = Nico) ; line = coups
    (chess.Move, le coup de Nico en tête) ; win = % de gain de Nico pour la
    ligne ; mate = le moteur annonce un mat pour Nico. Rend (n, critère),
    n = nombre de demi-coups montrés, ou None si aucun avantage clair.
    On s'arrête au premier n ≥ 2 où un critère est vrai ; au-delà de 10
    demi-coups, seulement tant que les coups sont forcés (échec, prise, mat
    annoncé), borne 16. Aucune analyse moteur : mesures sur l'échiquier.
    """
    mover = board.turn
    line = line[:_CLEAR_HARD_MAX]
    pos = board.copy(stack=False)
    for n, move in enumerate(line, start=1):
        if n > _CLEAR_MAX and not (mate or pos.gives_check(move) or pos.is_capture(move)):
            return None
        pos.push(move)
        if n < 2 and n < len(line):
            continue
        last = n == len(line)
        # Mat annoncé : la ligne va jusqu'au mat (fin de PV) dans la borne.
        if mate:
            if last or pos.is_checkmate():
                return n, "mate"
            continue
        criterion = _clear_criterion(board, pos, mover)
        if criterion is not None:
            return n, criterion
        # Position écrasante : on s'arrête dès que le coup suivant est calme.
        if win >= _CRUSHING_WIN and (last or not (
                pos.gives_check(line[n]) or pos.is_capture(line[n]))):
            return n, "crushing"
    return None


def _evidence(p: PlyAnalysis) -> tuple | None:
    """Avantage clair de la PV du meilleur coup (sortes c / e) : (n, critère, ligne SAN) ou None."""
    board = chess.Board(p.fen_before)
    line = [chess.Move.from_uci(uci) for uci in p.pv_uci]
    result = clear_advantage(board, line, p.win_before, p.pv_mate)
    if result is None:
        return None
    n, criterion = result
    san = []
    for move in line[:n]:
        san.append(board.san(move))
        board.push(move)
    return n, criterion, san


def assign_motifs(plies: list, nico_color: str) -> None:
    """Pose sur chaque coup de Nico (ply > 0) les motifs de la PV de son meilleur coup.

    La PV est coupée au point d'avantage clair (comme _evidence) ; pas
    d'avantage clair → aucun motif. Le coup adverse précédent ouvre la ligne
    (format des puzzles Lichess). Fonction pure : aucune analyse moteur.
    """
    for p in plies:
        if p.color != nico_color or p.ply == 0:
            continue
        line = [chess.Move.from_uci(uci) for uci in p.pv_uci]
        result = clear_advantage(chess.Board(p.fen_before), line, p.win_before, p.pv_mate)
        if result is not None:
            prev = plies[p.ply - 1]
            p.motifs = tag_motifs(prev.fen_before, prev.uci, p.pv_uci[:result[0]])


def first_shown_move(plies: list, nico_color: str, past_games=(), standard_start: bool = True) -> int:
    """Premier coup de Nico qui peut recevoir une miniature : le début de la nouveauté.

    past_games : (couleur de Nico, coups UCI) des autres parties. Un coup est connu
    si Nico l'a déjà joué dans ≥ 2 parties après exactement les mêmes coups. La
    nouveauté est le premier coup de Nico non connu, qu'il dévie lui-même ou que
    l'adversaire l'ait sorti du répertoire. Le renvoi d'une même partie ne compte pas.
    Tout est connu → coup au-delà de la fin : aucune miniature.
    """
    ucis = [p.uci for p in plies]
    known_lines = [line for color, line in past_games if color == nico_color and line != ucis]
    first_move = next(
        (p.move_number for p in plies if p.color == nico_color
         and sum(line[:p.ply + 1] == ucis[:p.ply + 1] for line in known_lines) < _KNOWN_MOVE_GAMES),
        plies[-1].move_number + 1,
    )
    floor = _CRITICAL_FIRST_MOVE
    if standard_start and nico_color == "white":
        detected = detect_opening(ucis)
        if detected is not None and opening_group(detected[1]) == "Göring Gambit":
            floor = _GORING_FIRST_MOVE
    return max(floor, first_move)


def _critical_errors(plies: list, nico_color: str, first_move: int) -> list:
    """Erreurs de Nico (sortes a et b) à partir de first_move, voir select_critical."""
    errors = []
    for p in plies:
        if p.color != nico_color or p.move_number < first_move:
            continue
        # Ouverture assumée : avant le coup 10, seule une perte ≥ 20 est une erreur.
        if p.loss >= (20 if p.move_number <= 10 else 10):
            prev = plies[p.ply - 1] if p.ply > 0 else None
            kind = "b" if prev is not None and prev.loss >= 20 else "a"
            errors.append(CriticalPosition(kind=kind, ply=p, score=p.loss))
    return errors


def select_critical(plies: list, nico_color: str, explosive=(), first_move: int = _CRITICAL_FIRST_MOVE) -> list:
    """Sélectionne ≤ 4 positions (coups manqués d'abord), à partir de first_move, ordre chronologique.

    (a) erreur de Nico (perte ≥ 10, ≥ 20 en ouverture : coups 1 à 10, ouverture
    assumée) ; (b) idem juste après une erreur adverse (perte adverse ≥ 20) ;
    (e) tournant : erreur adverse ≥ 15 suivie d'un coup de Nico à perte < 10,
    partie non décidée avant l'erreur ; (c) coup unique trouvé (meilleur coup,
    écart au 2e ≥ 15). Les c et e ne sont retenues que si la PV du meilleur coup
    rend l'avantage clair (clear_advantage) ; un ply à la fois e et c reste e.
    (d) occasion explosive, fournie par chess_coach.explosive (perte du coup joué
    < 10, donc jamais a/b). Budget unique de 4 : a/b, puis d, puis e, puis c, chaque
    sorte par score décroissant ; une position déjà prise est sautée. Une position
    d'avant first_move n'est jamais retenue, quelle que soit sa sorte.
    Aucune position retenue → liste vide.
    """
    errors = _critical_errors(plies, nico_color, first_move)
    error_plies = {c.ply.ply for c in errors}
    turns, uniques = [], []
    for p in plies:
        if p.color != nico_color or p.move_number < first_move or p.ply in error_plies:
            continue
        prev = plies[p.ply - 1] if p.ply > 0 else None
        if prev is not None and prev.loss >= 15 and p.loss < 10 and 100 - prev.win_before <= 90:
            evidence = _evidence(p)
            if evidence is not None:
                turns.append(CriticalPosition(kind="e", ply=p, score=prev.loss,
                                              evidence=evidence[1], line_san=evidence[2]))
        elif p.quality == "best" and p.second_gap is not None and p.second_gap >= 15:
            board = chess.Board(p.fen_before)
            decided = p.win_before > 90 or p.win_before < 10
            forced = board.legal_moves.count() <= 2
            recapture = (
                prev is not None and "capture" in prev.tags
                and chess.Move.from_uci(prev.uci).to_square == chess.Move.from_uci(p.uci).to_square
            )
            evidence = None if (decided or forced or recapture) else _evidence(p)
            if evidence is not None:
                uniques.append(CriticalPosition(kind="c", ply=p, score=p.second_gap,
                                                evidence=evidence[1], line_san=evidence[2]))

    # Les occasions fournies peuvent précéder first_move : le filtre vaut pour toutes.
    explosives = [d for d in explosive if d.ply.move_number >= first_move]
    selected, taken = [], set()
    for group in (errors, explosives, turns, uniques):
        for candidate in sorted(group, key=lambda c: c.score, reverse=True):
            if candidate.ply.ply not in taken and len(selected) < _CRITICAL_BUDGET:
                selected.append(candidate)
                taken.add(candidate.ply.ply)
    return sorted(selected, key=lambda c: c.ply.ply)


def new_targets(board: chess.Board, move: chess.Move) -> list:
    """Cases des pièces adverses que move attaque nouvellement : non défendues ou de valeur
    supérieure à la pièce jouée. C'est la définition d'une menace pour tout le coach."""
    if board.is_castling(move):
        return []
    values = {chess.PAWN: 1, **_PIECE_VALUES, chess.KING: 0}
    mover = board.turn
    before = board.attacks(move.from_square)
    # Le roi n'attaque utilement qu'une pièce non défendue.
    attacker_value = values[move.promotion or board.piece_type_at(move.from_square)] or 100
    after = board.copy(stack=False)
    after.push(move)
    return [
        sq for sq in after.attacks(move.to_square) & after.occupied_co[not mover]
        if sq not in before and after.piece_type_at(sq) != chess.KING
        and (not after.attackers(not mover, sq) or values[after.piece_type_at(sq)] > attacker_value)
    ]


def _is_forcing(board: chess.Board, move: chess.Move) -> bool:
    """Coup forcé au sens de Nico : échec, prise ou menace ; la promotion crée une menace."""
    return (board.gives_check(move) or board.is_capture(move) or bool(move.promotion)
            or bool(new_targets(board, move)))


def forcing_line(engine, fen: str, pv_uci: list) -> list:
    """Suite d'un coup (SAN, ce coup en tête), à partir de la ligne moteur pv_uci.

    Le coup et sa réponse sont toujours montrés ; ensuite la suite continue tant qu'un coup
    est forcé ou répond à un coup forcé. Stockfish tronque souvent sa ligne : au bout, la
    position atteinte est analysée de nouveau, tant que la suite n'est pas finie.
    """
    board = chess.Board(fen)
    moves = [chess.Move.from_uci(uci) for uci in pv_uci]
    line, previous_forcing = [], True
    while len(line) < _FORCING_MAX and not board.is_game_over():
        if not moves:
            moves = list(engine.analyse(board, chess.engine.Limit(time=_FORCING_TIME))["pv"])
        move = moves.pop(0)
        forcing = _is_forcing(board, move)
        if len(line) >= 2 and not forcing and not previous_forcing:
            break
        line.append(board.san(move))
        board.push(move)
        previous_forcing = forcing
    return line


def assign_forcing_lines(critical: list, plies: list, engine_path: str) -> None:
    """Remplit les deux suites comparées des erreurs (sortes a et b)."""
    errors = [c for c in critical if c.kind in ("a", "b")]
    items = []
    for c in errors:
        p = c.ply
        after = plies[p.ply + 1].pv_uci if p.ply + 1 < len(plies) else []
        items += [(p.fen_before, p.pv_uci), (p.fen_before, [p.uci, *after])]
    lines = run_on_engines(engine_path, lambda engine, item: forcing_line(engine, *item), items)
    for i, c in enumerate(errors):
        c.best_line_san, c.played_line_san = lines[2 * i], lines[2 * i + 1]


def analyze(text: str, message: str, engine_path: str,
            maia_models_dir: str | None = None, past_games=()) -> GameAnalysis | None:
    """Point d'entrée : PGN brut → GameAnalysis (None si PGN illisible).

    maia_models_dir : dossier des poids Maia-2 ; None → pas de difficulté ni
    d'occasion explosive. past_games : voir first_shown_move.
    """
    started = time.monotonic()
    game = parse_pgn(text)
    if game is None:
        return None
    headers = dict(game.headers)
    nico_color, source = detect_color(headers, message)
    plies = analyze_game(game, nico_color, engine_path)
    if maia_models_dir is not None:
        # Maia est une dépendance lourde optionnelle : son échec laisse
        # difficulty / played_p = None partout et l'analyse continue.
        try:
            from chess_coach.difficulty import assign_difficulty
            elo = headers.get("WhiteElo" if nico_color == "white" else "BlackElo", "")
            assign_difficulty(plies, nico_color, int(elo) if elo.isdigit() else None, maia_models_dir)
        except Exception:
            log.exception("maia_difficulty FAILED")
    assign_motifs(plies, nico_color)
    # Import local : explosive.py importe ce module (CriticalPosition, _win).
    from chess_coach.explosive import find_explosive
    opponent_elo = headers.get("BlackElo" if nico_color == "white" else "WhiteElo", "")
    opponent_elo = int(opponent_elo) if opponent_elo.isdigit() else None
    first_move = first_shown_move(plies, nico_color, past_games, "FEN" not in headers)
    # Les erreurs passent d'abord : si elles remplissent le budget, aucune occasion ne serait retenue.
    errors = len(_critical_errors(plies, nico_color, first_move))
    if errors >= _CRITICAL_BUDGET:
        log.info("chess_explosive skipped: %d errors fill the budget", errors)
        explosive = []
    else:
        explosive = find_explosive(plies, nico_color, engine_path, opponent_elo, maia_models_dir, first_move)
    critical = select_critical(plies, nico_color, explosive, first_move)
    assign_forcing_lines(critical, plies, engine_path)
    log.info(
        "chess_analysis OK plies=%d nico=%s source=%s first_move=%d critical=%s duration=%.1fs",
        len(plies), nico_color, source, first_move,
        [f"{c.kind}:{c.ply.move_number}{'.' if c.ply.color == 'white' else '...'}{c.ply.san}" for c in critical],
        time.monotonic() - started,
    )
    return GameAnalysis(headers=headers, nico_color=nico_color, color_source=source,
                        plies=plies, critical=critical, explosive=explosive)
