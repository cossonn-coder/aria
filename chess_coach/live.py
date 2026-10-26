# aria/chess_coach/live.py
#
# Analyse live d'une position de l'échiquier ARIA (sprint 35, tronçon 01, dette #94).
#
# Le camp au trait cherche un coup explosif avec le code existant de
# chess_coach.explosive (_search_position, inchangé). Un proxy moteur rend la
# recherche interruptible (un coup joué entre-temps lève Superseded au prochain
# appel moteur) et l'approfondit passe après passe (temps multiplié par FACTORS).
# Module pur : aucun import mémoire / LLM / HTTP.

import chess
import chess.engine

from chess_coach.difficulty import position_values, reply_distribution
from chess_coach.explosive import (_REPLY_LINE_PLIES, _WIN_MAX, _WIN_MIN, _by_shape, _human_replies, _priority,
                                   _san_line, _search_position, _win_of)
from logger import get_logger

log = get_logger(__name__)

# Facteurs de temps des passes successives sur une même position (≈ 75 s cumulées).
FACTORS = (1, 2, 4, 8)
# Analyse de tête (meilleur coup et 2e) : temps de base, avant facteur.
_HEAD_TIME = 0.5
# « Seul coup » : 2e coup à au moins cet écart (pts de % de gain) derrière le meilleur.
_FORCED_GAP = 20
# Piège (cyan) et stratégie (rose), sprint 37 : candidats MultiPV + coups de forme,
# à au plus _HUMAN_WINDOW pts de % de gain du meilleur coup.
_HUMAN_MULTIPV = 8
_HUMAN_WINDOW = 15
# Piège : au plus _TRAP_MAX_DEEP candidats approfondis ; une réponse humaine est
# piégeante si elle rapporte au trait ≥ meilleur coup + _TRAP_GAIN pts ; piège
# retenu si ces réponses pèsent au moins _TRAP_P_MIN (probabilités Maia brutes).
_TRAP_MAX_DEEP = 6
_TRAP_GAIN = 15
_TRAP_P_MIN = 0.20


class Superseded(Exception):
    """Une position plus récente est arrivée : la passe en cours est abandonnée."""


class EngineProxy:
    """Enveloppe d'un SimpleEngine : interruption et temps multiplié par factor.

    explosive.py n'appelle que engine.analyse(board, Limit(time=…), **kwargs) :
    c'est le seul point à intercepter.
    """

    def __init__(self, engine, factor: float, is_stale):
        self._engine = engine
        self._factor = factor
        self._is_stale = is_stale

    def analyse(self, board, limit, **kwargs):
        if self._is_stale():
            raise Superseded()
        return self._engine.analyse(board, chess.engine.Limit(time=limit.time * self._factor), **kwargs)


def _explosive_dict(move) -> dict:
    """Champs d'un ExplosiveMove utiles à la page."""
    return {"uci": move.uci, "san": move.san, "pv_san": move.pv_san,
            "replies": move.replies, "trap_line_san": move.trap_line_san}


def _human_moves(proxy, board: chess.Board, elo: int, models_dir: str) -> dict:
    """Piège (cyan) et stratégie (rose) du camp au trait : {"trap", "strategy"}.

    strategy = {"uci", "san", "value", "best_value", "pv_san"} : candidat au plus
    fort pronostic Maia-2 du trait (value, en %), best_value = pronostic du meilleur
    coup Stockfish. trap = {"uci", "san", "p", "replies"} : candidat dont les réponses
    humaines piégeantes (≥ meilleur coup + _TRAP_GAIN) pèsent le plus, si ≥ _TRAP_P_MIN ;
    replies = ces seules réponses ({"san", "p", "line_san", "win"}), sinon None.
    """
    head = proxy.analyse(board, chess.engine.Limit(time=_HEAD_TIME), multipv=_HUMAN_MULTIPV)
    win_best = _win_of(head[0])
    best = head[0]["pv"][0]
    infos = {info["pv"][0]: info for info in head}
    # Coups de forme absents du MultiPV : analysés à part (PV comprise).
    shaped = [move for move in _by_shape(board) if move not in infos]
    if shaped:
        for info in proxy.analyse(board, chess.engine.Limit(time=_HEAD_TIME), root_moves=shaped,
                                  multipv=len(shaped)):
            infos.setdefault(info["pv"][0], info)

    def after(move):
        position = board.copy(stack=False)
        position.push(move)
        return position

    # Meilleur coup qui termine la partie : ni pronostic de référence, ni réponse à évaluer.
    if after(best).is_game_over():
        return {"trap": None, "strategy": None}
    candidates = [
        (move, max(0.0, win_best - _win_of(info))) for move, info in infos.items()
        if win_best - _win_of(info) <= _HUMAN_WINDOW and not after(move).is_game_over()
    ]

    # Stratégie : dans la position suivante l'adversaire est au trait, d'où 100 − valeur.
    values = position_values([after(move).fen() for move, _ in candidates], elo, models_dir)
    prognosis = {move: 100 - value for (move, _), value in zip(candidates, values)}
    chosen = max(prognosis, key=prognosis.get)
    strategy = {"uci": chosen.uci(), "san": board.san(chosen), "value": prognosis[chosen],
                "best_value": prognosis[best],
                "pv_san": _san_line(board, infos[chosen]["pv"][:_REPLY_LINE_PLIES + 1])}

    # Piège : coups prioritaires d'abord, puis perte croissante ; une passe Maia batchée.
    deep = sorted(candidates, key=lambda c: (not _priority(board, c[0]), c[1]))[:_TRAP_MAX_DEEP]
    distributions = reply_distribution([after(move).fen() for move, _ in deep], elo, models_dir)
    trap = None
    for (move, _), distribution in zip(deep, distributions):
        replies, _ = _human_replies(proxy, after(move), distribution)
        trapping = [r for r in replies if r["win"] >= win_best + _TRAP_GAIN]
        p = sum(r["p"] for r in trapping)
        if p >= _TRAP_P_MIN and (trap is None or p > trap["p"]):
            trap = {"uci": move.uci(), "san": board.san(move), "p": p, "replies": trapping}
    return {"trap": trap, "strategy": strategy}


def analyse_pass(proxy, fen: str, elo: int, models_dir: str) -> dict:
    """Une passe sur fen pour le camp au trait : {"result", "explosive", "forced", "best", "trap", "strategy"}.

    result parmi game_over | decided | explosive | none ; forced = {"uci", "san"}
    du seul coup (coup légal unique ou 2e coup ≥ _FORCED_GAP derrière), sinon None ;
    best = {"uci", "san", "pv_san"} du meilleur coup moteur (même longueur de suite
    que les réponses du coup explosif), None en fin de partie.
    trap / strategy = piège (cyan) et stratégie (rose) de _human_moves, calculés
    hors fenêtre de l'orange aussi (decided compris) ; None, None en fin de partie.
    elo = Elo de l'adversaire du trait (réponses humaines Maia).
    """
    board = chess.Board(fen)
    # _search_position lit la PV du meilleur coup : inutilisable sur une position terminale.
    if board.is_game_over():
        return {"result": "game_over", "explosive": None, "forced": None, "best": None,
                "trap": None, "strategy": None}

    head = proxy.analyse(board, chess.engine.Limit(time=_HEAD_TIME), multipv=2)
    win_best = _win_of(head[0])
    best = head[0]["pv"][0]
    forced = None
    if len(head) == 1 or win_best - _win_of(head[1]) >= _FORCED_GAP:
        forced = {"uci": best.uci(), "san": board.san(best)}
    best_dict = {"uci": best.uci(), "san": board.san(best),
                 "pv_san": _san_line(board, head[0]["pv"][:_REPLY_LINE_PLIES + 1])}
    human = _human_moves(proxy, board, elo, models_dir)

    if not _WIN_MIN <= win_best <= _WIN_MAX:
        return {"result": "decided", "explosive": None, "forced": forced, "best": best_dict, **human}

    move = _search_position(proxy, board, "", "", elo, models_dir)
    if move is None:
        return {"result": "none", "explosive": None, "forced": forced, "best": best_dict, **human}
    return {"result": "explosive", "explosive": _explosive_dict(move), "forced": forced, "best": best_dict, **human}
