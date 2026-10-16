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
