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


@dataclass
class CriticalPosition:
    """Position critique : la position AVANT un coup de Nico."""
    kind: str
    ply: PlyAnalysis
    score: float
    # Sorte d uniquement : coup explosif manqué (chess_coach.explosive.ExplosiveMove).
    explosive: object | None = None


@dataclass
class GameAnalysis:
    headers: dict
    nico_color: str
    color_source: str
    plies: list = field(default_factory=list)
    critical: list = field(default_factory=list)


def parse_pgn(text: str) -> chess.pgn.Game | None:
    """Lit la partie à partir de la première ligne commençant par « [ ».

    Le message peut contenir du texte libre avant le PGN. Retourne None si
    aucune partie, aucun coup, ou un coup illégal (game.errors non vide).
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip().startswith("[")), None)
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
        for pv_move in best_pv[:6]:
            pv_san.append(pv_board.san(pv_move))
            pv_board.push(pv_move)
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
        ))
    return plies


def select_critical(plies: list, nico_color: str, explosive=()) -> list:
    """Sélectionne ≤ 3 positions critiques (avant un coup de Nico), ordre chronologique.

    (a) erreur de Nico (perte ≥ 10) ; (b) idem juste après une erreur adverse
    (perte adverse ≥ 20) ; (c) coup unique trouvé (meilleur coup, écart au
    2e ≥ 20) ; (d) occasion explosive manquée, fournie par chess_coach.explosive
    (perte du coup joué < 10, donc jamais a/b). Ordre : a/b par score
    décroissant, puis d, puis c pour compléter.
    """
    errors, uniques = [], []
    for p in plies:
        if p.color != nico_color:
            continue
        prev = plies[p.ply - 1] if p.ply > 0 else None
        if p.loss >= 10:
            kind = "b" if prev is not None and prev.loss >= 20 else "a"
            errors.append(CriticalPosition(kind=kind, ply=p, score=p.loss))
        elif p.quality == "best" and p.second_gap is not None and p.second_gap >= 20:
            board = chess.Board(p.fen_before)
            decided = p.win_before > 90 or p.win_before < 10
            forced = board.legal_moves.count() <= 2
            recapture = (
                prev is not None and "capture" in prev.tags
                and chess.Move.from_uci(prev.uci).to_square == chess.Move.from_uci(p.uci).to_square
            )
            if not (decided or forced or recapture):
                uniques.append(CriticalPosition(kind="c", ply=p, score=p.second_gap))

    errors.sort(key=lambda c: c.score, reverse=True)
    uniques.sort(key=lambda c: c.score, reverse=True)
    explosives = sorted(explosive, key=lambda c: c.score, reverse=True)
    selected = (errors + explosives + uniques)[:3]
    if not selected:
        nico_plies = [p for p in plies if p.color == nico_color]
        if nico_plies:
            worst = max(nico_plies, key=lambda p: p.loss)
            selected = [CriticalPosition(kind="a", ply=worst, score=worst.loss)]
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
