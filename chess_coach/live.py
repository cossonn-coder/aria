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

from chess_coach.explosive import _REPLY_LINE_PLIES, _WIN_MAX, _WIN_MIN, _san_line, _search_position, _win_of
from logger import get_logger

log = get_logger(__name__)

# Facteurs de temps des passes successives sur une même position (≈ 75 s cumulées).
FACTORS = (1, 2, 4, 8)
# Analyse de tête (meilleur coup et 2e) : temps de base, avant facteur.
_HEAD_TIME = 0.5
# « Seul coup » : 2e coup à au moins cet écart (pts de % de gain) derrière le meilleur.
_FORCED_GAP = 20


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


def analyse_pass(proxy, fen: str, elo: int, models_dir: str) -> dict:
    """Une passe sur fen pour le camp au trait : {"result", "explosive", "forced", "best"}.

    result parmi game_over | decided | explosive | none ; forced = {"uci", "san"}
    du seul coup (coup légal unique ou 2e coup ≥ _FORCED_GAP derrière), sinon None ;
    best = {"uci", "san", "pv_san"} du meilleur coup moteur (même longueur de suite
    que les réponses du coup explosif), None en fin de partie.
    elo = Elo de l'adversaire du trait (réponses humaines Maia).
    """
    board = chess.Board(fen)
    # _search_position lit la PV du meilleur coup : inutilisable sur une position terminale.
    if board.is_game_over():
        return {"result": "game_over", "explosive": None, "forced": None, "best": None}

    head = proxy.analyse(board, chess.engine.Limit(time=_HEAD_TIME), multipv=2)
    win_best = _win_of(head[0])
    best = head[0]["pv"][0]
    forced = None
    if len(head) == 1 or win_best - _win_of(head[1]) >= _FORCED_GAP:
        forced = {"uci": best.uci(), "san": board.san(best)}
    best_dict = {"uci": best.uci(), "san": board.san(best),
                 "pv_san": _san_line(board, head[0]["pv"][:_REPLY_LINE_PLIES + 1])}

    if not _WIN_MIN <= win_best <= _WIN_MAX:
        return {"result": "decided", "explosive": None, "forced": forced, "best": best_dict}

    move = _search_position(proxy, board, "", "", elo, models_dir)
    if move is None:
        return {"result": "none", "explosive": None, "forced": forced, "best": best_dict}
    return {"result": "explosive", "explosive": _explosive_dict(move), "forced": forced, "best": best_dict}
