# Tests sprint 26 tronçon 02 : émission de CHESS_ANALYSIS par le classifier.

from cognition.cognitive_classifier import classify_operation, detect_pgn
from cognition.cognitive_context import CognitiveOperation

_PGN = (
    '[Event "Live Chess"]\n[Site "Chess.com"]\n[White "Ami"]\n[Black "staroflexeur"]\n'
    '[Link "https://www.chess.com/game/live/123"]\n\n1. e4 e5 2. Nf3 Nc6 *'
)


def test_chesscom_pgn_with_link_is_chess_analysis():
    assert detect_pgn(_PGN)
    assert classify_operation(_PGN) == CognitiveOperation.CHESS_ANALYSIS


def test_moves_without_header_are_not_pgn():
    assert not detect_pgn("après 1.e4 e5 2.Cf3 quelles idées ?")


# ── Sprint 63 : question de suivi citant une position d'une partie analysée ──

from unittest.mock import MagicMock

from cognition.cognitive_context import CHESS_ANALYSIS_MARKER, CHESS_POSITION_MARKER


def _bridge(user_turn):
    bridge = MagicMock()
    bridge.load_conversation_history.return_value = [
        {"role": "user", "content": user_turn}, {"role": "assistant", "content": "réponse"},
    ]
    return bridge


def test_followup_citing_move_after_analysis():
    turn = f"{CHESS_ANALYSIS_MARKER} — Nico joue les blancs (pseudo dans l'en-tête) :\n…"
    message = "au coup 10 j'avais mat avec Bb5+ ?"
    assert classify_operation(message, bridge=_bridge(turn)) == CognitiveOperation.CHESS_FOLLOWUP
    assert classify_operation(message, bridge=_bridge("bonjour")) != CognitiveOperation.CHESS_FOLLOWUP


def test_board_move_stays_before_followup():
    turn = f"{CHESS_POSITION_MARKER} 8/8/8/8/8/8/8/8 w - - 0 1]\n{CHESS_ANALYSIS_MARKER}"
    assert classify_operation("et si 1...e6 ?", bridge=_bridge(turn)) == CognitiveOperation.CHESS_BOARD_MOVE
