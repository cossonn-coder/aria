# Tests sprint 22 tronçon 02 : émission de WEB_SEARCH par le classifier.

from cognition.cognitive_classifier import (
    CLASSIFIER_PROMPT,
    classify_operation,
    detect_web_search_intent,
)
from cognition.cognitive_context import CognitiveOperation


def test_source_short_message_is_web_search():
    assert classify_operation("source ?") == CognitiveOperation.WEB_SEARCH


def test_explicit_phrase_is_web_search():
    msg = "cherche sur le web le score du match de Caen"
    assert classify_operation(msg) == CognitiveOperation.WEB_SEARCH


def test_source_inside_sentence_does_not_match():
    assert not detect_web_search_intent("il faut trouver une source d'eau pour le potager")


def test_prompt_has_web_search_category():
    assert "web_search" in CLASSIFIER_PROMPT
