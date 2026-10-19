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
import re
import time
from dataclasses import dataclass, field

import chess
import chess.engine
import chess.pgn

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

# Options Stockfish de toute l'analyse (sprint 27) : la machine a 16 cœurs.
ENGINE_OPTIONS = {"Threads": 8, "Hash": 256}

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


@dataclass
class GameAnalysis:
    headers: dict
    nico_color: str
    color_source: str
    plies: list = field(default_factory=list)
    critical: list = field(default_factory=list)


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


def detect_color(headers, message: str, username: str) -> tuple[str, str]:
    """Couleur de Nico : en-tête PGN, puis message (« je joue les noirs »), puis blancs."""
    name = username.lower()
    if headers.get("White", "").lower() == name:
        return "white", "header"
    if headers.get("Black", "").lower() == name:
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


def analyze_game(game, nico_color: str, engine_path: str, time_per_position: float = 0.15) -> list:
    """Analyse chaque position de la partie (N+1 positions) et qualifie chaque demi-coup.

    nico_color n'influe pas sur les mesures (calculées pour les deux camps) ;
    il est gardé dans la signature pour les callers.
    """
    nodes = list(game.mainline())
    boards = [game.board()] + [node.board() for node in nodes]

    # Une analyse par position : (cp point de vue du trait, infos multipv).
    evaluations = []
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        engine.configure(ENGINE_OPTIONS)
        for board in boards:
            if board.is_game_over():
                evaluations.append((_terminal_cp(board), []))
                continue
            infos = engine.analyse(board, chess.engine.Limit(time=time_per_position), multipv=2)
            cp = infos[0]["score"].relative.score(mate_score=_MATE_SCORE)
            evaluations.append((cp, infos))

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
        if mate and (last or pos.is_checkmate()):
            return n, "mate"
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


def select_critical(plies: list, nico_color: str, explosive=()) -> list:
    """Sélectionne ≤ 3 positions critiques + 1 occasion explosive en bonus, ordre chronologique.

    (a) erreur de Nico (perte ≥ 10, ≥ 20 en ouverture : coups 1 à 10, ouverture
    assumée) ; (b) idem juste après une erreur adverse (perte adverse ≥ 20) ;
    (e) tournant : erreur adverse ≥ 15 suivie d'un coup de Nico à perte < 10,
    partie non décidée avant l'erreur ; (c) coup unique trouvé (meilleur coup,
    écart au 2e ≥ 15). Les c et e ne sont retenues que si la PV du meilleur coup
    rend l'avantage clair (clear_advantage). Les a/b par score décroissant, puis
    les e, puis les c remplissent le budget de 3 ; un ply à la fois e et c reste e.
    (d) occasion explosive, fournie par chess_coach.explosive (perte du coup joué
    < 10, donc jamais a/b) : la meilleure s'ajoute en 4e sans rien évincer, sauf
    si sa position est déjà retenue. Aucune position retenue → liste vide.
    """
    errors, turns, uniques = [], [], []
    for p in plies:
        if p.color != nico_color:
            continue
        prev = plies[p.ply - 1] if p.ply > 0 else None
        # Ouverture assumée : avant le coup 10, seule une perte ≥ 20 est une erreur.
        threshold = 20 if p.move_number <= 10 else 10
        if p.loss >= threshold:
            kind = "b" if prev is not None and prev.loss >= 20 else "a"
            errors.append(CriticalPosition(kind=kind, ply=p, score=p.loss))
        elif prev is not None and prev.loss >= 15 and p.loss < 10 and 100 - prev.win_before <= 90:
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

    errors.sort(key=lambda c: c.score, reverse=True)
    turns.sort(key=lambda c: c.score, reverse=True)
    uniques.sort(key=lambda c: c.score, reverse=True)
    selected = (errors + turns + uniques)[:3]
    if explosive:
        best_d = max(explosive, key=lambda c: c.score)
        if all(c.ply.ply != best_d.ply.ply for c in selected):
            selected.append(best_d)
    return sorted(selected, key=lambda c: c.ply.ply)


def analyze(text: str, message: str, username: str, engine_path: str) -> GameAnalysis | None:
    """Point d'entrée : PGN brut → GameAnalysis (None si PGN illisible)."""
    started = time.monotonic()
    game = parse_pgn(text)
    if game is None:
        return None
    headers = dict(game.headers)
    nico_color, source = detect_color(headers, message, username)
    plies = analyze_game(game, nico_color, engine_path)
    # Import local : explosive.py importe ce module (CriticalPosition, _win).
    from chess_coach.explosive import find_explosive
    explosive = find_explosive(plies, nico_color, engine_path)
    critical = select_critical(plies, nico_color, explosive)
    log.info(
        "chess_analysis OK plies=%d nico=%s source=%s critical=%s duration=%.1fs",
        len(plies), nico_color, source,
        [f"{c.kind}:{c.ply.move_number}{'.' if c.ply.color == 'white' else '...'}{c.ply.san}" for c in critical],
        time.monotonic() - started,
    )
    return GameAnalysis(headers=headers, nico_color=nico_color, color_source=source,
                        plies=plies, critical=critical)
