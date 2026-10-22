# aria/chess_coach/explosive.py
#
# Recherche des « occasions explosives » (sprint 27, tronçon 01, dette #87 ;
# coup piégeant face à un humain : sprint 29, tronçon 04 ; règle hybride :
# sprint 29, tronçon 07 ; coup qui pose problème : sprint 29, tronçon 08).
#
# Sorte d de position critique : avant un coup de Nico, un coup tenait la
# fenêtre de tolérance et, soit était une idée risquée au sens du sprint 28
# (sacrifice ou piège), soit rapportait plus que le meilleur coup face à un
# humain de l'Elo adverse. Espérance humaine E(coup) = Σ P_maia(réponse) ×
# % de gain de Nico après la réponse ; le gain d'espérance classe les candidats.
# Seconde passe moteur sur toute la partie, sans budget de temps.
# Module pur : aucun import mémoire / LLM / exécution.

import time
from dataclasses import dataclass, field

import chess
import chess.engine

from chess_coach.analysis import _CLEAR_MAX, ENGINE_OPTIONS, _MATE_SCORE, CriticalPosition, _win, clear_advantage
from chess_coach.difficulty import DEFAULT_ELO, _load, reply_distribution
from logger import get_logger

log = get_logger(__name__)

# Threads=8 + limites en temps : deux rejeux du même PGN peuvent différer (accepté).
# Durées d'analyse : référence MultiPV / candidats par forme, puis approfondissement.
_ROOT_TIME = 0.5
_DEEP_TIME = 0.3
# Réanalyse de la réponse humaine la plus probable quand sa PV est trop courte
# pour la règle d'avantage clair.
_EVIDENCE_TIME = 0.6
_MULTIPV = 5
# Positions éligibles : coups de Nico non décidés, joués sans erreur nette.
_WIN_MIN, _WIN_MAX = 35, 75
# Fenêtre de perte sur jeu parfait (pts de % de gain) : 5 en général, 15 pour
# un piège ou un gain d'espérance humaine. Piège minimal (pts) et gain minimal
# d'espérance humaine sur le meilleur coup.
_WINDOW = 5
_TRAP_WINDOW = 15
_TRAP_MIN = 10
_GAIN_MIN = 5
# Nombre maximal de candidats approfondis par position.
_MAX_DEEP = 3
# Ligne mesurée (candidat compris) : au moins 6 demi-coups, prolongée tant
# que l'échange continue, borne dure 10.
_LINE_PLIES = 6
_LINE_MAX = 10
# Longueur affichée des lignes des réponses (la suite de la réponse la plus
# probable est coupée par la règle d'avantage clair, chess_coach.analysis.clear_advantage).
_REPLY_LINE_PLIES = 6
_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


@dataclass
class ExplosiveMove:
    """Coup explosif retenu pour une position (tous les % de gain côté Nico)."""
    san: str
    uci: str
    loss: float
    win_after: float
    pv_san: list
    sacrifice: int
    forcing: list
    # Réponse humaine la plus probable (Maia, Elo adverse), en SAN.
    trap_reply_san: str | None
    # Gain = expected − best_expected (classement entre candidats et positions).
    score: float
    # Matériel offert par le candidat lui-même (pièce posée en prise), en pions.
    offered: int = 0
    # Suite de la réponse humaine la plus probable (SAN depuis la position après le candidat).
    trap_line_san: list = field(default_factory=list)
    # Réponses humaines : {"san", "p", "line_san", "win"} par probabilité Maia
    # décroissante (p brute, win = % de gain côté Nico après la réponse).
    replies: list = field(default_factory=list)
    # Règle d'avantage clair (tronçon 08) : position au point d'arrêt de la suite
    # logique, % de gain de Nico pour cette suite, critère (None = non admissible).
    trap_end_fen: str | None = None
    trap_end_win: float | None = None
    evidence: str | None = None
    # Espérance humaine du candidat et du meilleur coup (% de gain de Nico).
    expected: float = 0.0
    best_expected: float = 0.0
    # Piège (règle sprint 28) : % de gain adverse après sa meilleure réponse −
    # après la prise naturelle du matériel offert (0 sans prise naturelle).
    trap: float = 0.0


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


def _expectation(replies: list) -> float:
    """Espérance humaine : Σ p × win, probabilités renormalisées sur les réponses gardées."""
    total = sum(r["p"] for r in replies)
    return sum(r["p"] * r["win"] for r in replies) / total


def _human_replies(engine, after: chess.Board, distribution: list) -> tuple:
    """Évalue les réponses humaines (Maia) dans after : (réponses affichables, infos moteur).

    Une analyse MultiPV restreinte à ces réponses (root_moves) ; infos moteur
    indexées par coup, dans l'ordre de probabilité.
    """
    moves = [chess.Move.from_uci(uci) for uci, _ in distribution]
    infos = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME), root_moves=moves, multipv=len(moves))
    by_move = {info["pv"][0]: info for info in infos}
    replies = [
        {"san": after.san(move), "p": p, "win": 100 - _win_of(by_move[move]),
         "line_san": _san_line(after, by_move[move]["pv"][:_REPLY_LINE_PLIES])}
        for move, (_, p) in zip(moves, distribution)
    ]
    return replies, [by_move[move] for move in moves]


def _deepen(engine, board: chess.Board, move: chess.Move, loss: float, win_after: float,
            distribution: list) -> ExplosiveMove:
    """Approfondit un candidat : ligne, sacrifice, piège, forçant, réponses humaines, avantage clair."""
    after = board.copy(stack=False)
    after.push(move)

    # Ligne : candidat + PV moteur adverse, mesurée une fois l'échange terminé.
    principal = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME))
    line = [move] + principal["pv"]
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
    trap = 0.0
    if capture is not None:
        taken_line = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME), root_moves=[capture])
        trap = max(0.0, _win_of(principal) - _win_of(taken_line))

    replies, infos = _human_replies(engine, after, distribution)

    # Suite de la réponse humaine la plus probable, coupée au point où l'avantage
    # devient clair pour un humain ; PV trop courte → réanalyse plus longue.
    logical = infos[0]
    if len(logical["pv"]) + 1 < _CLEAR_MAX:
        logical = engine.analyse(after, chess.engine.Limit(time=_EVIDENCE_TIME), root_moves=[logical["pv"][0]])
    score_logical = logical["score"].relative
    mate = score_logical.is_mate() and score_logical.mate() < 0
    trap_win = 100 - _win_of(logical)
    clear = clear_advantage(board, [move] + logical["pv"], trap_win, mate)
    trap_line_san, trap_end_fen, evidence = [], None, None
    if clear is not None:
        n, evidence = clear
        trap_line_san = _san_line(after, logical["pv"][:n - 1])
        end = after.copy(stack=False)
        for reply_move in logical["pv"][:n - 1]:
            end.push(reply_move)
        trap_end_fen = end.fen()

    return ExplosiveMove(
        san=board.san(move), uci=move.uci(), loss=loss, win_after=win_after, pv_san=pv_san,
        sacrifice=sacrifice, forcing=_forcing(board, move), trap_reply_san=replies[0]["san"],
        score=0.0, offered=offered, trap_line_san=trap_line_san, replies=replies,
        trap_end_fen=trap_end_fen, trap_end_win=trap_win, evidence=evidence,
        expected=_expectation(replies), trap=trap,
    )


def _admissible(candidate: ExplosiveMove, best_expected: float) -> bool:
    """Avantage clair, puis règle hybride : idée risquée du sprint 28 OU gain Maia.

    Sprint 28 : (perte ≤ 5, ou ≤ 15 avec piège ≥ 10) et (sacrifice ≥ 1 ou piège ≥ 10).
    Maia : perte ≤ 15 et espérance humaine ≥ meilleur coup + 5.
    """
    if candidate.evidence is None:
        return False
    in_window = candidate.loss <= _WINDOW or (candidate.loss <= _TRAP_WINDOW and candidate.trap >= _TRAP_MIN)
    risky = in_window and (candidate.sacrifice >= 1 or candidate.trap >= _TRAP_MIN)
    return risky or (candidate.loss <= _TRAP_WINDOW and candidate.expected >= best_expected + _GAIN_MIN)


def _search_position(engine, board: chess.Board, played_uci: str, first_best_uci: str,
                     elo: int, models_dir: str) -> ExplosiveMove | None:
    """Coup admissible au plus fort gain d'espérance humaine d'une position, ou None.

    Exclus : le coup joué, le meilleur coup de cette analyse et celui de la
    1re passe (first_best_uci, celui que la légende affiche comme meilleur),
    et les coups qui terminent la partie (Maia n'a aucune réponse à évaluer).
    """
    reference = engine.analyse(board, chess.engine.Limit(time=_ROOT_TIME), multipv=_MULTIPV)
    win_best = _win_of(reference[0])
    best = reference[0]["pv"][0]
    wins = {info["pv"][0]: _win_of(info) for info in reference}

    shaped = _by_shape(board)
    if shaped:
        infos = engine.analyse(board, chess.engine.Limit(time=_ROOT_TIME), root_moves=shaped, multipv=len(shaped))
        for info in infos:
            wins.setdefault(info["pv"][0], _win_of(info))

    def after(move):
        position = board.copy(stack=False)
        position.push(move)
        return position

    if after(best).is_game_over():
        return None
    candidates = [
        (move, max(0.0, win_best - win)) for move, win in wins.items()
        if move != best and move.uci() not in (played_uci, first_best_uci)
        and win_best - win <= _TRAP_WINDOW and not after(move).is_game_over()
    ]
    if not candidates:
        return None
    # Sacrifices, échecs et prises passent d'abord, puis la perte croissante.
    candidates.sort(key=lambda c: (not _priority(board, c[0]), c[1]))
    candidates = candidates[:_MAX_DEEP]

    # Une passe Maia batchée : meilleur coup + candidats approfondis.
    distributions = reply_distribution(
        [after(best).fen()] + [after(move).fen() for move, _ in candidates], elo, models_dir)
    best_expected = _expectation(_human_replies(engine, after(best), distributions[0])[0])

    kept = None
    for (move, loss), distribution in zip(candidates, distributions[1:]):
        candidate = _deepen(engine, board, move, loss, win_best - loss, distribution)
        candidate.best_expected = best_expected
        candidate.score = candidate.expected - best_expected
        if _admissible(candidate, best_expected) and (kept is None or candidate.score > kept.score):
            kept = candidate
    return kept


def find_explosive(plies: list, nico_color: str, engine_path: str,
                   opponent_elo: int | None, models_dir: str | None) -> list:
    """Positions critiques de sorte d (une par coup de Nico au plus), toute la partie.

    Maia indisponible (models_dir None ou échec de chargement) → aucune
    occasion, l'analyse continue.
    """
    started = time.monotonic()
    if models_dir is None:
        log.warning("chess_explosive skipped: Maia models_dir absent")
        return []
    try:
        _load(models_dir)
    except Exception as e:
        log.warning("chess_explosive skipped: Maia unavailable (%s: %s)", type(e).__name__, e)
        return []
    elo = opponent_elo or DEFAULT_ELO
    eligible = [
        p for p in plies
        if p.color == nico_color and _WIN_MIN <= p.win_before <= _WIN_MAX and p.loss < 10
    ]
    found = []
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        engine.configure(ENGINE_OPTIONS)
        for p in eligible:
            explosive = _search_position(engine, chess.Board(p.fen_before), p.uci, p.best_uci, elo, models_dir)
            if explosive is not None:
                found.append(CriticalPosition(kind="d", ply=p, score=explosive.score, explosive=explosive))
    log.info(
        "chess_explosive positions=%d/%d found=%d duration=%.1fs",
        len(eligible), len(eligible), len(found), time.monotonic() - started,
    )
    return found


# ── Coup qui pose problème (sprint 29, tronçon 08) ──────────────────────────
# Le « meilleur coup » de Nico : celui qui provoque des fautes humaines et donne
# le plus de potentiel de conversion. Maia (réponses probables) ET Stockfish
# (meilleure défense, valeur de chaque réponse), jamais Maia seule.
# Coup de Nico éligible : perte ≤ 5, coup adverse précédent sans erreur (< 15).
_BEST_LOSS_MAX = 5
_PREV_ERROR = 15
# Faute : réponse qui donne à Nico au moins 5 pts de plus que la meilleure défense.
_FAULT_MIN = 5
# Maia hésitante : aucune réponse à 15 % ou plus → on mesure sur le top 5 Stockfish.
_HESITANT_P = 0.15
# Bonus si l'adversaire a réellement fauté (perte ≥ 10) au coup suivant.
_BONUS_LOSS = 10
_BONUS = 1.5


@dataclass
class BestMove:
    """Coup qui pose problème : coup de Nico, meilleure défense et réponse jouée."""
    ply: object
    defense_san: str
    # Probabilité Maia (brute) de la meilleure défense, 0 hors des réponses Maia gardées.
    defense_p: float
    reply_played: str | None
    score: float


def _problem_score(maia: list, stockfish: list, best_win: float) -> float:
    """Score d'un coup à partir des réponses évaluées (% de gain de Nico).

    maia = [(p brute, win)] réponses Maia ; stockfish = [win] top Stockfish ;
    best_win = win après la meilleure défense. Seules les fautes comptent.
    Maia hésitante : part des réponses Stockfish fautives × leur écart moyen.
    """
    if max(p for p, _ in maia) < _HESITANT_P:
        gaps = [win - best_win for win in stockfish if win - best_win >= _FAULT_MIN]
        return len(gaps) / len(stockfish) * sum(gaps) / len(gaps) if gaps else 0.0
    return sum(p * (win - best_win) for p, win in maia if win - best_win >= _FAULT_MIN)


def find_best_move(plies: list, nico_color: str, engine_path: str,
                   opponent_elo: int | None, models_dir: str | None) -> BestMove | None:
    """Coup de Nico au plus fort score de fautes provoquées, ou None.

    Maia indisponible → None (le WARNING est déjà émis par find_explosive).
    Une seule passe Maia batchée sur toutes les positions éligibles.
    """
    started = time.monotonic()
    if models_dir is None:
        return None
    try:
        _load(models_dir)
    except Exception:
        return None
    elo = opponent_elo or DEFAULT_ELO

    eligible = []
    for p in plies:
        if p.color != nico_color or p.loss > _BEST_LOSS_MAX:
            continue
        if p.ply > 0 and plies[p.ply - 1].loss >= _PREV_ERROR:
            continue
        after = chess.Board(p.fen_before)
        after.push(chess.Move.from_uci(p.uci))
        if not after.is_game_over():
            eligible.append((p, after))
    if not eligible:
        return None
    distributions = reply_distribution([after.fen() for _, after in eligible], elo, models_dir)

    kept = None
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        engine.configure(ENGINE_OPTIONS)
        for (p, after), distribution in zip(eligible, distributions):
            hesitant = max(prob for _, prob in distribution) < _HESITANT_P
            top = engine.analyse(after, chess.engine.Limit(time=_DEEP_TIME), multipv=5 if hesitant else 3)
            stockfish = [100 - _win_of(info) for info in top]
            best_win = stockfish[0]
            replies, _ = _human_replies(engine, after, distribution)
            score = _problem_score([(r["p"], r["win"]) for r in replies], stockfish, best_win)
            following = plies[p.ply + 1] if p.ply + 1 < len(plies) else None
            if following is not None and following.loss >= _BONUS_LOSS:
                score *= _BONUS
            if score > 0 and (kept is None or score > kept.score):
                defense = top[0]["pv"][0]
                kept = BestMove(
                    ply=p, defense_san=after.san(defense),
                    defense_p=dict(distribution).get(defense.uci(), 0.0),
                    reply_played=following.san if following else None, score=score,
                )
    if kept is not None:
        log.info("chess_best_move OK move=%d%s%s score=%.1f duration=%.1fs",
                 kept.ply.move_number, "." if kept.ply.color == "white" else "...", kept.ply.san,
                 kept.score, time.monotonic() - started)
    else:
        log.info("chess_best_move OK move=none duration=%.1fs", time.monotonic() - started)
    return kept
