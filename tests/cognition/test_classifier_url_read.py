# Tests sprint 23 tronçon 01 : émission de URL_READ par le classifier.

from cognition.cognitive_classifier import classify_operation, detect_url
from cognition.cognitive_context import CognitiveOperation


def test_message_with_url_is_url_read():
    assert classify_operation("regarde https://ex.fr/a") == CognitiveOperation.URL_READ


def test_url_beats_web_search_phrase():
    msg = "cherche en ligne https://ex.fr/a"
    assert classify_operation(msg) == CognitiveOperation.URL_READ


def test_detect_url_strips_trailing_punctuation():
    assert detect_url("lis (https://ex.fr/page).") == "https://ex.fr/page"


# ── Tronçon 02 : « lis la suite » ────────────────────────────────────────────

from unittest.mock import MagicMock


def _bridge(user_turn):
    bridge = MagicMock()
    bridge.load_conversation_history.return_value = [
        {"role": "user", "content": user_turn},
        {"role": "assistant", "content": "Veux-tu que je lise la suite ?"},
    ]
    return bridge


def test_oui_after_partial_read_is_url_read():
    bridge = _bridge("[Lecture partielle : https://ex.fr/a caractères 0-99000 sur 250000]\n\nrésume")
    assert classify_operation("Oui !", metadata={"chat_id": 42}, bridge=bridge) == CognitiveOperation.URL_READ
    bridge.load_conversation_history.assert_called_once_with("42", n=2)


def test_oui_without_marker_stays_confirmation():
    bridge = _bridge("on mange quoi ce soir")
    assert classify_operation("oui", metadata={"chat_id": 42}, bridge=bridge) == CognitiveOperation.CONFIRMATION


# ── Sprint 42 : document reçu → FILE_READ sans LLM ──────────────────────────

def test_file_event_classified_file_read():
    from cognition.cognitive_engine import CognitiveEngine
    from core.event import Event, EventType
    event = Event.create(
        event_type=EventType.FILE, user_id="1",
        content={"file_path": "/tmp/x.txt", "file_name": "x.txt", "caption": None},
        metadata={},
    )
    result = CognitiveEngine().classify(event)
    assert result.operation == CognitiveOperation.FILE_READ
