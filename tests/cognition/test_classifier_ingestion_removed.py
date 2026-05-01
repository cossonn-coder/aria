# tests/cognition/test_classifier_ingestion_removed.py
#
# Tests de régression — suppression du court-circuit INGESTION (sprint 3.0).
#
# Vérifie que :
#   1. Un message long contenant une question n'est plus classifié INGESTION.
#   2. "ingestion" est absent de CLASSIFIER_PROMPT (le LLM ne peut plus l'émettre).
#   3. INGESTION est absent du _ROUTING_TABLE du kernel.

from unittest.mock import MagicMock

from cognition.cognitive_classifier import CLASSIFIER_PROMPT, classify_operation
from cognition.cognitive_context import CognitiveOperation
from core.kernel import _ROUTING_TABLE


def _make_llm_mock(operation: str = "reasoning") -> MagicMock:
    mock = MagicMock()
    response = MagicMock()
    response.content = f'{{"operation": "{operation}", "confidence": 0.85}}'
    mock.complete.return_value = response
    return mock


class TestIngestionRemovedFromClassifier:

    def test_long_message_with_question_not_classified_as_ingestion(self):
        """
        Régression bug sprint 3.0 : message >150 chars contenant une question
        ne doit plus être court-circuité vers INGESTION.

        Avant le fix, len(message) > 150 retournait INGESTION immédiatement,
        silençant Aria sans appel LLM ni réponse cognitive.
        """
        long_question = (
            "J'ai du mal à comprendre quelque chose dans notre relation. "
            "Je veux qu'on se fasse des câlins mais des fois tu sembles distant. "
            "Est-ce que tu peux m'expliquer comment tu fonctionnes et ce que "
            "je peux faire pour qu'on soit plus proches ?"
        )
        assert len(long_question) > 150

        result = classify_operation(long_question, llm_router=_make_llm_mock())

        assert result != CognitiveOperation.INGESTION, (
            f"Message long avec question classifié INGESTION — "
            f"le court-circuit len>150 est toujours actif. Got: {result}"
        )

    def test_long_message_without_llm_not_classified_as_ingestion(self):
        """
        Sans LLM disponible (fallback UNKNOWN), un message long ne doit
        toujours pas passer par INGESTION.
        """
        long_message = "x" * 300
        result = classify_operation(long_message, llm_router=None)
        assert result != CognitiveOperation.INGESTION

    def test_ingestion_absent_from_classifier_prompt(self):
        """
        Le LLM classifier ne doit plus pouvoir retourner 'ingestion'.

        Si 'ingestion' est absent de CLASSIFIER_PROMPT, le LLM ne peut pas
        émettre cette opération, rendant le bug inatteignable même en cas
        de réintroduction de la branche len().
        """
        assert "ingestion" not in CLASSIFIER_PROMPT.lower(), (
            "La catégorie 'ingestion' est encore dans CLASSIFIER_PROMPT. "
            "Le LLM pourrait classifier un message long comme INGESTION et "
            "court-circuiter la pipeline cognitive."
        )

    def test_ingestion_absent_from_routing_table(self):
        """
        INGESTION ne doit plus avoir d'entrée dans le _ROUTING_TABLE du kernel.

        Si l'enum était malgré tout émis (classifier cache ou réintroduction),
        l'absence de routing produirait une erreur explicite plutôt qu'un
        silence silencieux.
        """
        assert CognitiveOperation.INGESTION.value not in _ROUTING_TABLE.mapping, (
            "CognitiveOperation.INGESTION est encore dans le _ROUTING_TABLE. "
            "Un message classifié INGESTION serait routé vers ingestion_router "
            "et court-circuiterait la pipeline LLM."
        )
