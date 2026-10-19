# aria/chess_coach/explosive.py
#
# Recherche des « occasions explosives » (sprint 27, tronçon 01, dette #87).
#
# Sorte d de position critique : avant un coup de Nico, un coup explosif
# (sacrifice, coup forçant, piège) tenait la fenêtre de tolérance alors que
# Nico a joué autre chose. Seconde passe moteur, plus profonde que la
# première, limitée aux positions non décidées des 20 premiers coups et
# bornée par un budget de temps global.
# Module pur : aucun import mémoire / LLM / exécution.

import time
from dataclasses import dataclass, field

import chess
import chess.engine

from chess_coach.analysis import ENGINE_OPTIONS, _MATE_SCORE, CriticalPosition, _win
from logger import get_logger

log = get_logger(__name__)

# Budget global de la recherche (secondes), vérifié avant chaque position.
# Threads=8 + limites en temps : deux rejeux du même PGN peuvent différer (accepté).
_BUDGET = 30.0
# Durées d'analyse : référence MultiPV / candidats par forme, puis approfondissement.
_ROOT_TIME = 0.5
_DEEP_TIME = 0.3
_MULTIPV = 5
# Positions éligibles : coups de Nico non décidés des 20 premiers coups.
_MAX_MOVE_NUMBER = 20
_WIN_MIN, _WIN_MAX = 35, 75
# Fenêtre de tolérance (Q5) : 5 pts, ou 15 si le coup tend un piège ≥ 10.
_WINDOW = 5
_TRAP_WINDOW = 15
_TRAP_MIN = 10
# Nombre maximal de candidats approfondis par position.
_MAX_DEEP = 3
# Ligne mesurée (candidat compris) : au moins 6 demi-coups, prolongée tant
# que l'échange continue, borne dure 10.
_LINE_PLIES = 6
_LINE_MAX = 10
# Longueurs affichées : suite du piège (prise comprise), lignes des réponses.
_TRAP_LINE_PLIES = 8
_REPLY_LINE_PLIES = 6
_SACRIFICE_CAP = 5
_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


@dataclass
class ExplosiveMove:
    """Coup explosif retenu pour une position (tous les % de gain côté Nico, sauf trap)."""
    san: str
    uci: str
    loss: float
    win_after: float
    pv_san: list
    sacrifice: int
    forcing: list
    trap: float
    trap_reply_san: str | None
    volatility: float
    score: float
    # Matériel offert par le candidat lui-même (pièce posée en prise), en pions.
    offered: int = 0
    # Suite si l'adversaire prend le matériel offert (SAN depuis la position après le candidat).
    trap_line_san: list = field(default_factory=list)
    # Réponses MultiPV adverses : {"san", "line_san", "win"} (win = % de gain côté Nico).
    replies: list = field(default_factory=list)


def _material(board: chess.Board, color: chess.Color) -> int:
    """Bilan matériel (color − adversaire), en pions."""
    return sum(
        value * (len(board.pieces(piece, color)) - len(board.pieces(piece, not color)))
        for piece, value in _VALUES.items()
    )


def _san_line(board: chess.Board, moves: list) -> list:
    """Ligne de coups en SAN depuis board (non modifié)."""
    board = board.copy(stack=False)
    san = []
    for move in moves:
        san.append(board.san(move))
        board.push(move)
    return san


def _line_sacrifice(board: chess.Board, line: list) -> tuple:
    """Matériel perdu par le trait de board sur une ligne stabilisée, et sa longueur.

    Point de mesure : le premier demi-coup à partir du 6e après lequel le coup
    suivant n'est pas une prise (on laisse finir l'échange), borne _LINE_MAX ;
    fin de la ligne si elle s'épuise avant.
    """
    mover = board.turn
    pv_board = board.copy(stack=False)
    plies = 0
    for move in line[:_LINE_MAX]:
        if plies >= _LINE_PLIES and not pv_board.is_capture(move):
            break
        pv_board.push(move)
        plies += 1
    return max(0, _material(board, mover) - _material(pv_board, mover)), plies


def _win_of(info: dict) -> float:
    """% de gain du trait de la position analysée."""
    return _win(info["score"].relative.score(mate_score=_MATE_SCORE))


def _by_shape(board: chess.Board) -> list:
    """Coups qui donnent échec, prennent, ou posent la pièce sur une case attaquée."""
    return [
        move for move in board.legal_moves
        if board.gives_check(move) or board.is_capture(move)
        or board.is_attacked_by(not board.turn, move.to_square)
    ]


def _forcing(board: chess.Board, move: chess.Move) -> list:
    """Étiquettes forçantes du coup (board = position AVANT le coup)."""
    labels = []
    if board.gives_check(move):
        labels.append("check")
    if board.is_capture(move):
        labels.append("capture")
    after = board.copy(stack=False)
    after.push(move)
    mover, piece = board.turn, after.piece_type_at(move.to_square)
    for square in after.attacks(move.to_square):
        target = after.piece_at(square)
        if target is None or target.color == mover or target.piece_type == chess.KING:
            continue
        if _VALUES[target.piece_type] > _VALUES[piece] or not after.is_attacked_by(not mover, square):
            labels.append("threat")
            break
    return labels


def _natural_capture(board: chess.Board, square: int) -> chess.Move | None:
    """Réponse naturelle (Q6) : prise du matériel offert sur la case d'arrivée.

    board = position APRÈS le candidat (trait à l'adversaire). Prise par
    l'attaquant le plus faible, retenue seulement si elle gagne du matériel
    à vue (pièce prise plus forte que la preneuse, ou case non défendue) :
    Fxa3 sur un pion défendu par b2 n'est pas une réponse naturelle.
    """
    captures = [m for m in board.legal_moves if m.to_square == square and board.is_capture(m)]
    if not captures:
        return None
    capture = min(captures, key=lambda m: _VALUES[board.piece_type_at(m.from_square)])
    offered = _VALUES[board.piece_type_at(square)] > _VALUES[board.piece_type_at(capture.from_square)]
    if offered or not board.is_attacked_by(not board.turn, square):
        return capture
    return None


def _priority(board: chess.Board, move: chess.Move) -> bool:
    """Candidat prioritaire : échec, prise, ou matériel offert sur la case d'arrivée."""
    if board.gives_check(move) or board.is_capture(move):
        return True
    after = board.copy(stack=False)
    after.push(move)
    return _natural_capture(after, move.to_square) is not None


def _deepen(engine, board: chess.Board, move: chess.Move, loss: float, win_after: float) -> ExplosiveMove:
    """Approfondit un candidat : ligne, sacrifice, forçant, piège, volatilité."""
    after = board.copy(stack=False)
    after.push(move)
    replies = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME), multipv=3)

    # Ligne : candidat + PV adverse, mesurée une fois l'échange terminé.
    line = [move] + replies[0]["pv"]
    sacrifice_line, plies = _line_sacrifice(board, line)
    pv_san = _san_line(board, line[:plies])

    # Matériel offert : pièce posée en prise (même si l'adversaire refuse dans la PV),
    # moins la pièce éventuellement prise par le candidat.
    capture = _natural_capture(after, move.to_square)
    offered = 0
    if capture is not None:
        taken = chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
        offered = max(0, _VALUES[after.piece_type_at(move.to_square)] - (_VALUES[taken] if taken else 0))
    sacrifice = max(sacrifice_line, offered)

    # Piège : % de gain adverse après sa meilleure réponse − après la prise naturelle.
    trap, trap_reply_san, trap_line_san = 0.0, None, []
    if capture is not None:
        captured = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME), root_moves=[capture])
        trap = max(0.0, _win_of(replies[0]) - _win_of(captured))
        trap_reply_san = after.san(capture)
        trap_line_san = _san_line(after, captured["pv"][:_TRAP_LINE_PLIES])

    reply_lines = [
        {"san": after.san(info["pv"][0]), "line_san": _san_line(after, info["pv"][:_REPLY_LINE_PLIES]),
         "win": 100 - _win_of(info)}
        for info in replies
    ]

    opponent_wins = [_win_of(info) for info in replies]
    volatility = max(opponent_wins) - min(opponent_wins)
    forcing = _forcing(board, move)
    forcing_points = sum({"check": 1, "capture": 0.5, "threat": 0.5}[label] for label in forcing)
    score = min(sacrifice, _SACRIFICE_CAP) + forcing_points + trap / 5 + volatility / 10
    return ExplosiveMove(
        san=board.san(move), uci=move.uci(), loss=loss, win_after=win_after, pv_san=pv_san,
        sacrifice=sacrifice, forcing=forcing, trap=trap, trap_reply_san=trap_reply_san,
        volatility=volatility, score=score, offered=offered, trap_line_san=trap_line_san,
        replies=reply_lines,
    )


def _admissible(candidate: ExplosiveMove) -> bool:
    """Fenêtre (Q5) et explosivité réelle (sacrifice ou piège)."""
    in_window = candidate.loss <= _WINDOW or (candidate.loss <= _TRAP_WINDOW and candidate.trap >= _TRAP_MIN)
    return in_window and (candidate.sacrifice >= 1 or candidate.trap >= _TRAP_MIN)


def _search_position(engine, board: chess.Board, played_uci: str) -> ExplosiveMove | None:
    """Meilleur coup explosif admissible d'une position, ou None."""
    reference = engine.analyse(board, chess.engine.Limit(time=_ROOT_TIME), multipv=_MULTIPV)
    win_best = _win_of(reference[0])
    best = reference[0]["pv"][0]
    wins = {info["pv"][0]: _win_of(info) for info in reference}

    shaped = _by_shape(board)
    if shaped:
        infos = engine.analyse(board, chess.engine.Limit(time=_ROOT_TIME), root_moves=shaped, multipv=len(shaped))
        for info in infos:
            wins.setdefault(info["pv"][0], _win_of(info))

    candidates = [
        (move, max(0.0, win_best - win)) for move, win in wins.items()
        if move != best and move.uci() != played_uci and win_best - win <= _TRAP_WINDOW
    ]
    # Sacrifices, échecs et prises passent d'abord, puis la perte croissante.
    candidates.sort(key=lambda c: (not _priority(board, c[0]), c[1]))

    kept = None
    for move, loss in candidates[:_MAX_DEEP]:
        candidate = _deepen(engine, board, move, loss, win_best - loss)
        if _admissible(candidate) and (kept is None or candidate.score > kept.score):
            kept = candidate
    return kept


def find_explosive(plies: list, nico_color: str, engine_path: str) -> list:
    """Positions critiques de sorte d (une par coup de Nico au plus), budget _BUDGET."""
    started = time.monotonic()
    eligible = [
        p for p in plies
        if p.color == nico_color and p.move_number <= _MAX_MOVE_NUMBER
        and _WIN_MIN <= p.win_before <= _WIN_MAX and p.loss < 10
    ]
    found, examined = [], 0
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        engine.configure(ENGINE_OPTIONS)
        for p in eligible:
            if time.monotonic() - started >= _BUDGET:
                break
            examined += 1
            explosive = _search_position(engine, chess.Board(p.fen_before), p.uci)
            if explosive is not None:
                found.append(CriticalPosition(kind="d", ply=p, score=explosive.score, explosive=explosive))
    log.info(
        "chess_explosive positions=%d/%d found=%d duration=%.1fs",
        examined, len(eligible), len(found), time.monotonic() - started,
    )
    return found
