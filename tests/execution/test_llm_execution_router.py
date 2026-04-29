# tests/execution/test_llm_execution_router.py
#
# Tests unitaires du LLMExecutionRouter.
#
# Stratégie :
#   Toutes les dépendances IO (MemPalace, LLM, IntentEngine) sont mockées.
#   On teste la logique de pipeline, pas les providers.
#
# Migration bridge :
#   retrieve_memories et retrieve_by_intent ne sont plus des fonctions
#   module-level — elles sont des méthodes de MempalaceBridge injecté
#   dans le constructeur. Le mock est donc injecté via make_router(),
#   pas via @patch("execution.routers.llm_router.retrieve_memories").
#
# Ce qu'on vérifie ici :
#   - retrieve_memories est appelé exactement UNE fois par cycle (pas de doublon)
#   - global_memories est transmis intact à AgentContext
#   - session_memories (retrieve_by_intent) est appelé après résolution d'intent
#   - store_interaction est appelé en fin de pipeline (write unique)
#   - le résultat de ctx.result est retourné tel quel
#   - un op_type inconnu ne crash pas (fallback UNKNOWN)

from unittest.mock import MagicMock, patch
import pytest

from cognition.cognitive_context import CognitiveOperation
from execution.routers.llm_router import LLMExecutionRouter
from memory.mempalace_bridge import MempalaceBridge


# ── Fixtures ─────────────────────────────────────────────────────────────────

FAKE_GLOBAL_MEMORIES  = {"hits": [{"text": "souvenir global A"}],  "count": 1}
FAKE_SESSION_MEMORIES = {"hits": [{"text": "souvenir session B"}], "count": 1}


def make_router():
    """
    Construit un LLMExecutionRouter avec toutes les dépendances mockées.

    Le bridge est injecté directement — ses méthodes sont des MagicMock
    configurables test par test via .return_value / .side_effect.

    Retourne (router, llm_router_mock, intent_engine_mock, fake_intent, bridge_mock).
    """
    llm_router    = MagicMock(name="LLMRouter")
    intent_engine = MagicMock(name="IntentEngine")

    # Bridge mock — remplace l'injection MempalaceBridge(store=...)
    bridge = MagicMock(spec=MempalaceBridge)
    bridge.retrieve_memories.return_value   = FAKE_GLOBAL_MEMORIES
    bridge.retrieve_by_intent.return_value  = FAKE_SESSION_MEMORIES

    # Intent factice retourné par intent_engine.apply()
    fake_intent = MagicMock()
    fake_intent.id   = "intent-test-001"
    fake_intent.name = "test_intent"
    fake_intent.last_state = None

    intent_engine.list_attention_active.return_value = []
    intent_engine.list_active.return_value           = []
    intent_engine.resolve.return_value = (
        MagicMock(action="attach"),   # recall_decision
        None,
    )
    intent_engine.apply.return_value = fake_intent

    router = LLMExecutionRouter(
        llm_router=llm_router,
        intent_engine=intent_engine,
        mempalace_bridge=bridge,
    )

    return router, llm_router, intent_engine, fake_intent, bridge


def _fake_ctx(fake_intent, result="réponse aria"):
    """Retourne un AgentContext mock avec result et trace configurés."""
    ctx = MagicMock()
    ctx.result = result
    ctx.intent = fake_intent
    ctx.trace.as_dict.return_value = []
    return ctx


# ── Tests : appels mémoire ────────────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
def test_retrieve_memories_called_exactly_once(mock_store):
    """
    retrieve_memories NE DOIT être appelé qu'une seule fois par cycle.

    Régression directe du bug corrigé :
    l'ancien code appelait retrieve_memories deux fois (étapes 1 et 4).
    """
    router, _, _, fake_intent, bridge = make_router()
    router.controller.run = MagicMock(return_value=_fake_ctx(fake_intent))

    router._run_pipeline("test message", CognitiveOperation.FACT_RECALL, {})

    assert bridge.retrieve_memories.call_count == 1, (
        f"retrieve_memories appelé {bridge.retrieve_memories.call_count} fois "
        "— attendu 1. Doublon détecté dans le pipeline."
    )


@patch("execution.routers.llm_router.store_interaction")
def test_retrieve_memories_called_with_correct_top_k(mock_store):
    """
    retrieve_memories doit utiliser le top_k correspondant à l'opération.

    FACT_RECALL → top_k=3, REASONING → top_k=8.
    """
    router, _, _, fake_intent, bridge = make_router()
    router.controller.run = MagicMock(return_value=_fake_ctx(fake_intent))

    router._run_pipeline("requête", CognitiveOperation.FACT_RECALL, {})
    bridge.retrieve_memories.assert_called_once_with("requête", n=3)

    bridge.retrieve_memories.reset_mock()

    router._run_pipeline("analyse complexe", CognitiveOperation.REASONING, {})
    bridge.retrieve_memories.assert_called_once_with("analyse complexe", n=8)


# ── Tests : transmission du contexte aux agents ───────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
def test_agent_context_receives_preloaded_memories(mock_store):
    """
    AgentContext doit contenir global_memories et session_memories
    tels qu'ils ont été récupérés — pas recompilés ni recalculés.

    Les agents reçoivent le contexte pré-assemblé : ils ne font aucune requête.
    """
    router, _, _, fake_intent, bridge = make_router()
    captured = {}

    def capture_ctx(ctx, lr):
        captured["memories"]       = ctx.memories
        captured["session_memory"] = ctx.session_memory
        return _fake_ctx(fake_intent, result="réponse")

    router.controller.run = capture_ctx

    router._run_pipeline("test", CognitiveOperation.MEMORY_QUERY, {})

    assert captured["memories"] == FAKE_GLOBAL_MEMORIES, (
        "ctx.memories ne correspond pas à global_memories récupéré à l'étape 1."
    )
    assert captured["session_memory"] == FAKE_SESSION_MEMORIES, (
        "ctx.session_memory ne correspond pas à retrieve_by_intent."
    )


# ── Tests : persistence mémoire ───────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
def test_store_interaction_called_once_after_resolution(mock_store):
    """
    store_interaction doit être appelé exactement une fois,
    après résolution complète du pipeline — jamais sur un état intermédiaire.
    """
    router, _, _, fake_intent, _ = make_router()
    router.controller.run = MagicMock(
        return_value=_fake_ctx(fake_intent, result="résultat final")
    )

    router._run_pipeline("message", CognitiveOperation.PLANNING, {})

    assert mock_store.call_count == 1
    call_kwargs  = mock_store.call_args
    stored_text  = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "message"        in stored_text
    assert "résultat final" in stored_text


@patch("execution.routers.llm_router.store_interaction")
def test_store_interaction_not_called_without_intent(mock_store):
    """
    Si intent_engine.apply() retourne None (aucun intent résolu),
    store_interaction NE doit PAS être appelé.

    Évite d'écrire des interactions orphelines en mémoire.
    """
    router, _, intent_engine, _, bridge = make_router()
    intent_engine.apply.return_value = None   # pas d'intent

    no_intent_ctx = MagicMock()
    no_intent_ctx.result = "réponse sans intent"
    no_intent_ctx.intent = None
    no_intent_ctx.trace.as_dict.return_value = []
    router.controller.run = MagicMock(return_value=no_intent_ctx)

    router._run_pipeline("message", CognitiveOperation.UNKNOWN, {})

    mock_store.assert_not_called()


# ── Tests : robustesse ────────────────────────────────────────────────────────

@patch("execution.routers.llm_router.store_interaction")
def test_unknown_op_type_does_not_crash(mock_store):
    """
    execute() avec un op_type inconnu doit fallback sur UNKNOWN
    sans lever d'exception.
    """
    router, _, _, fake_intent, _ = make_router()
    router.controller.run = MagicMock(return_value=_fake_ctx(fake_intent, result="ok"))

    result = router.execute({
        "op_type"  : "operation_inexistante",
        "content"  : "test",
        "metadata" : {},
    })

    assert isinstance(result, dict)
    assert "text" in result


@patch("execution.routers.llm_router.store_interaction", side_effect=Exception("ChromaDB down"))
def test_store_interaction_failure_does_not_propagate(mock_store):
    """
    Une erreur dans store_interaction (ex: ChromaDB indisponible)
    NE doit PAS faire crasher le pipeline.

    Le résultat doit quand même être retourné à l'utilisateur.
    """
    router, _, _, fake_intent, _ = make_router()
    router.controller.run = MagicMock(
        return_value=_fake_ctx(fake_intent, result="réponse malgré erreur mémoire")
    )

    result = router._run_pipeline("test", CognitiveOperation.FACT_RECALL, {})

    assert result == "réponse malgré erreur mémoire"