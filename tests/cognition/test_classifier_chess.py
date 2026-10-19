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
