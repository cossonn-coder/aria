# Tests sprint 22 tronçon 02 : émission de WEB_SEARCH par le classifier.

from cognition.cognitive_classifier import (
    CLASSIFIER_PROMPT,
    classify_operation,
    detect_web_search_intent,
    extract_research_subject,
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


# ── Sprint 45 : recherche autonome WEB_RESEARCH ──────────────────────────────

def test_explicit_research_phrase_is_web_research():
    assert classify_operation("fais une recherche sur le paillage") == CognitiveOperation.WEB_RESEARCH


def test_research_online_phrase_is_web_research_not_web_search():
    msg = "fais une recherche en ligne sur la rotation des cultures"
    assert classify_operation(msg) == CognitiveOperation.WEB_RESEARCH


def test_quick_search_stays_web_search():
    assert classify_operation("cherche en ligne la météo") == CognitiveOperation.WEB_SEARCH


def test_extract_research_subject_drops_trigger_phrase():
    assert (extract_research_subject("fais une recherche sur la rotation des cultures au potager")
            == "la rotation des cultures au potager")
    assert extract_research_subject("fais une recherche approfondie sur le compost ?") == "le compost"
