# tests/execution/test_llm_execution_router.py
#
# Tests unitaires du LLMExecutionRouter.
#
# Stratégie :
#   Toutes les dépendances IO (MemPalace, LLM, IntentEngine) sont mockées.
#   On teste la logique de pipeline, pas les providers.
#
# Ce qu'on vérifie ici :
#   - retrieve_memories est appelé exactement UNE fois par cycle (pas de doublon)
#   - global_memories est transmis intact à AgentContext
#   - session_memories (retrieve_by_intent) est appelé après la résolution d'intent
#   - store_interaction est appelé en fin de pipeline (write unique)
#   - le résultat de ctx.result est retourné tel quel
#   - un op_type inconnu ne crash pas (fallback UNKNOWN)

from unittest.mock import MagicMock, patch, call
import pytest

from cognition.cognitive_context import CognitiveOperation
from execution.routers.llm_router import LLMExecutionRouter


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_router():
    """
    Construit un LLMExecutionRouter avec toutes les dépendances mockées.

    Retourne (router, llm_router_mock, intent_engine_mock).
    """
    llm_router = MagicMock(name="LLMRouter")
    intent_engine = MagicMock(name="IntentEngine")

    # Intent factice retourné par intent_engine.apply()
    fake_intent = MagicMock()
    fake_intent.id = "intent-test-001"
    fake_intent.name = "test_intent"
    fake_intent.last_state = None

    intent_engine.list_attention_active.return_value = []
    intent_engine.list_active.return_value = []
    intent_engine.resolve.return_value = (
        MagicMock(action="attach"),   # recall_decision
        None,
    )
    intent_engine.apply.return_value = fake_intent

    router = LLMExecutionRouter(
        llm_router=llm_router,
        intent_engine=intent_engine,
    )

    return router, llm_router, intent_engine, fake_intent


FAKE_GLOBAL_MEMORIES = {"hits": [{"text": "souvenir global A"}], "count": 1}
FAKE_SESSION_MEMORIES = {"hits": [{"text": "souvenir session B"}], "count": 1}


# ── Tests : appels mémoire ────────────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_retrieve_memories_called_exactly_once(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    retrieve_memories NE DOIT être appelé qu'une seule fois par cycle.

    Régression directe du bug corrigé :
    l'ancien code appelait retrieve_memories deux fois (étapes 1 et 4).
    """
    mock_retrieve.return_value = FAKE_GLOBAL_MEMORIES
    mock_by_intent.return_value = FAKE_SESSION_MEMORIES

    router, llm_router, intent_engine, fake_intent = make_router()

    # AgentController.run() retourne ctx avec un result positionné
    fake_ctx = MagicMock()
    fake_ctx.result = "réponse aria"
    fake_ctx.intent = fake_intent
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    router._run_pipeline("test message", CognitiveOperation.FACT_RECALL, {})

    assert mock_retrieve.call_count == 1, (
        f"retrieve_memories appelé {mock_retrieve.call_count} fois — attendu 1. "
        "Doublon détecté dans le pipeline."
    )


@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_retrieve_memories_called_with_correct_top_k(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    retrieve_memories doit utiliser le top_k correspondant à l'opération.

    FACT_RECALL → top_k=3, REASONING → top_k=8.
    """
    mock_retrieve.return_value = FAKE_GLOBAL_MEMORIES
    mock_by_intent.return_value = FAKE_SESSION_MEMORIES

    router, llm_router, intent_engine, fake_intent = make_router()

    fake_ctx = MagicMock()
    fake_ctx.result = "ok"
    fake_ctx.intent = fake_intent
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    router._run_pipeline("requête", CognitiveOperation.FACT_RECALL, {})
    mock_retrieve.assert_called_once_with("requête", n=3)

    mock_retrieve.reset_mock()

    router._run_pipeline("analyse complexe", CognitiveOperation.REASONING, {})
    mock_retrieve.assert_called_once_with("analyse complexe", n=8)


# ── Tests : transmission du contexte aux agents ───────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_agent_context_receives_preloaded_memories(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    AgentContext doit contenir global_memories et session_memories
    tels qu'ils ont été récupérés — pas recompilés ni recalculés.

    Les agents reçoivent le contexte pré-assemblé : ils ne font aucune requête.
    """
    mock_retrieve.return_value = FAKE_GLOBAL_MEMORIES
    mock_by_intent.return_value = FAKE_SESSION_MEMORIES

    router, llm_router, intent_engine, fake_intent = make_router()

    captured_ctx = {}

    def capture_ctx(ctx, lr):
        captured_ctx["memories"] = ctx.memories
        captured_ctx["session_memory"] = ctx.session_memory
        fake_ctx = MagicMock()
        fake_ctx.result = "réponse"
        fake_ctx.intent = fake_intent
        fake_ctx.trace.as_dict.return_value = []
        return fake_ctx

    router.controller.run = capture_ctx

    router._run_pipeline("test", CognitiveOperation.MEMORY_QUERY, {})

    assert captured_ctx["memories"] == FAKE_GLOBAL_MEMORIES, (
        "ctx.memories ne correspond pas à global_memories récupéré à l'étape 1."
    )
    assert captured_ctx["session_memory"] == FAKE_SESSION_MEMORIES, (
        "ctx.session_memory ne correspond pas à retrieve_by_intent."
    )


# ── Tests : persistence mémoire ───────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_store_interaction_called_once_after_resolution(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    store_interaction doit être appelé exactement une fois,
    après résolution complète du pipeline.

    Jamais sur un état intermédiaire.
    """
    mock_retrieve.return_value = FAKE_GLOBAL_MEMORIES
    mock_by_intent.return_value = FAKE_SESSION_MEMORIES

    router, llm_router, intent_engine, fake_intent = make_router()

    fake_ctx = MagicMock()
    fake_ctx.result = "résultat final"
    fake_ctx.intent = fake_intent
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    router._run_pipeline("message", CognitiveOperation.PLANNING, {})

    assert mock_store.call_count == 1
    call_kwargs = mock_store.call_args
    stored_text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "message" in stored_text
    assert "résultat final" in stored_text


@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_store_interaction_not_called_without_intent(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    Si intent_engine.apply() retourne None (aucun intent résolu),
    store_interaction NE doit PAS être appelé.

    Évite d'écrire des interactions orphelines en mémoire.
    """
    mock_retrieve.return_value = {"hits": [], "count": 0}
    mock_by_intent.return_value = {"hits": [], "count": 0}

    router, llm_router, intent_engine, _ = make_router()
    intent_engine.apply.return_value = None   # pas d'intent

    fake_ctx = MagicMock()
    fake_ctx.result = "réponse sans intent"
    fake_ctx.intent = None
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    router._run_pipeline("message", CognitiveOperation.UNKNOWN, {})

    mock_store.assert_not_called()


# ── Tests : robustesse ────────────────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_unknown_op_type_does_not_crash(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    execute() avec un op_type inconnu doit fallback sur UNKNOWN
    sans lever d'exception.
    """
    mock_retrieve.return_value = {"hits": [], "count": 0}
    mock_by_intent.return_value = {"hits": [], "count": 0}

    router, llm_router, intent_engine, fake_intent = make_router()

    fake_ctx = MagicMock()
    fake_ctx.result = "ok"
    fake_ctx.intent = fake_intent
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    result = router.execute({
        "op_type": "operation_inexistante",
        "content": "test",
        "metadata": {},
    })

    assert isinstance(result, dict)
    assert "text" in result


@patch("execution.routers.llm_router.store_interaction", side_effect=Exception("ChromaDB down"))
@patch("execution.routers.llm_router.retrieve_by_intent")
@patch("execution.routers.llm_router.retrieve_memories")
def test_store_interaction_failure_does_not_propagate(
    mock_retrieve, mock_by_intent, mock_store
):
    """
    Une erreur dans store_interaction (ex: ChromaDB indisponible)
    NE doit PAS faire crasher le pipeline.

    Le résultat doit quand même être retourné à l'utilisateur.
    """
    mock_retrieve.return_value = FAKE_GLOBAL_MEMORIES
    mock_by_intent.return_value = FAKE_SESSION_MEMORIES

    router, llm_router, intent_engine, fake_intent = make_router()

    fake_ctx = MagicMock()
    fake_ctx.result = "réponse malgré erreur mémoire"
    fake_ctx.intent = fake_intent
    fake_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=fake_ctx)

    result = router._run_pipeline("test", CognitiveOperation.FACT_RECALL, {})

    assert result == "réponse malgré erreur mémoire"