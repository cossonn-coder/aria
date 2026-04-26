# tests/execution/test_pipeline_memory_isolation.py
#
# Tests d'isolation mémoire du pipeline cognitif.
#
# Principe vérifié :
#   Les agents (AnalystAgent, PlannerAgent, etc.) NE DOIVENT PAS
#   appeler retrieve_memories, retrieve_by_intent, ou tout autre
#   accès MemPalace de leur propre chef.
#
#   Seul LLMExecutionRouter est autorisé à lire la mémoire.
#   Les agents reçoivent un AgentContext pré-assemblé — point final.
#
# Ces tests patchent les fonctions mémoire au niveau du module agent
# et vérifient qu'elles restent silencieuses pendant l'exécution.

from unittest.mock import MagicMock, patch
import pytest

from agents.base_agent import AgentContext
from agents.analyst_agent import AnalystAgent
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_trace import CognitiveTrace
from intent.intent import Intent


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context(
    message: str = "test",
    operation: CognitiveOperation = CognitiveOperation.FACT_RECALL,
) -> AgentContext:
    """
    Construit un AgentContext minimal avec mémoires pré-chargées.

    Simule ce que LLMExecutionRouter aurait injecté avant d'appeler les agents.
    """
    fake_intent = MagicMock(spec=Intent)
    fake_intent.id = "intent-isolation-test"
    fake_intent.name = "isolation_test"

    return AgentContext(
        message=message,
        intent=fake_intent,
        memories={
            "hits": [{"text": "souvenir A injecté par le router"}],
            "count": 1,
        },
        session_memory={
            "hits": [{"text": "session B injectée par le router"}],
            "count": 1,
        },
        trace=CognitiveTrace(),
        extra={
            "cognitive_operation": operation,
            "active_intents": [],
        },
    )


def make_llm_router_mock() -> MagicMock:
    """LLMRouter minimal — retourne une réponse factice sans IO."""
    mock = MagicMock(name="LLMRouter")
    response = MagicMock()
    response.content = "réponse factice"
    mock.complete.return_value = response
    return mock


# ── Tests : AnalystAgent ──────────────────────────────────────────────────────

class TestAnalystAgentMemoryIsolation:
    """
    Vérifie qu'AnalystAgent n'accède jamais à MemPalace directement.
    """

    def test_analyst_does_not_call_retrieve_memories(self):
        """
        retrieve_memories ne doit pas être appelé depuis AnalystAgent.
        """
        ctx = make_context(operation=CognitiveOperation.FACT_RECALL)
        llm_router = make_llm_router_mock()
        agent = AnalystAgent()

        with patch("memory.mempalace_bridge.retrieve_memories") as mock_retrieve:
            agent.run(ctx, llm_router)
            mock_retrieve.assert_not_called()

    def test_analyst_does_not_call_retrieve_by_intent(self):
        """
        retrieve_by_intent ne doit pas être appelé depuis AnalystAgent.
        """
        ctx = make_context(operation=CognitiveOperation.MEMORY_QUERY)
        llm_router = make_llm_router_mock()
        agent = AnalystAgent()

        with patch("memory.mempalace_bridge.retrieve_by_intent") as mock_by_intent:
            agent.run(ctx, llm_router)
            mock_by_intent.assert_not_called()

    def test_analyst_uses_ctx_memories_not_fresh_query(self):
        """
        AnalystAgent doit utiliser ctx.memories tel quel,
        pas initier une nouvelle requête vectorielle.

        On vérifie que le prompt LLM contient bien le contenu
        des mémoires injectées dans le contexte.
        """
        ctx = make_context(operation=CognitiveOperation.FACT_RECALL)
        llm_router = make_llm_router_mock()
        agent = AnalystAgent()

        agent.run(ctx, llm_router)

        # Le prompt passé au LLM doit contenir les souvenirs du ctx
        call_args = llm_router.complete.call_args
        prompt_used = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")

        assert "souvenir A injecté par le router" in prompt_used, (
            "AnalystAgent n'utilise pas ctx.memories dans son prompt. "
            "Il ignore les mémoires pré-assemblées."
        )

    def test_analyst_result_set_on_context(self):
        """
        AnalystAgent doit écrire son résultat dans ctx.result.

        Vérifie le contrat de base de BaseAgent.
        """
        ctx = make_context()
        llm_router = make_llm_router_mock()
        agent = AnalystAgent()

        result_ctx = agent.run(ctx, llm_router)

        assert result_ctx.result is not None
        assert isinstance(result_ctx.result, str)
        assert len(result_ctx.result) > 0


# ── Tests : AgentContext — contrat d'immutabilité ─────────────────────────────

class TestAgentContextContract:
    """
    Vérifie le contrat d'AgentContext : result ne peut être écrit qu'une fois.
    """

    def test_set_result_raises_on_overwrite(self):
        """
        set_result() doit lever RuntimeError si result est déjà défini.

        Évite les overwrite silencieux entre agents dans un pipeline multi-agents.
        """
        ctx = make_context()
        ctx.set_result("premier résultat")

        with pytest.raises(RuntimeError, match="Result already set"):
            ctx.set_result("tentative d'overwrite")

    def test_stop_sets_halted(self):
        """
        stop() doit passer ctx.halted à True.

        Un agent peut interrompre la pipeline proprement.
        """
        ctx = make_context()
        assert ctx.halted is False

        ctx.stop()

        assert ctx.halted is True

    def test_set_result_also_halts(self):
        """
        set_result() doit implicitement halter la pipeline.
        """
        ctx = make_context()
        ctx.set_result("résultat terminal")

        assert ctx.halted is True


# ── Tests : isolation transversale ───────────────────────────────────────────

class TestMemoryIsolationTransversal:
    """
    Vérifie que le module memory.mempalace_bridge n'est jamais importé
    ni appelé depuis le package agents/.
    """

    def test_analyst_agent_has_no_direct_mempalace_import(self):
        """
        analyst_agent ne doit pas importer retrieve_memories
        ou retrieve_by_intent directement dans son module.

        Si ces imports apparaissent, l'agent peut court-circuiter le pipeline.
        """
        import agents.analyst_agent as module
        import inspect

        source = inspect.getsource(module)

        assert "retrieve_memories" not in source, (
            "analyst_agent importe ou appelle retrieve_memories — "
            "la mémoire doit être injectée via AgentContext."
        )
        assert "retrieve_by_intent" not in source, (
            "analyst_agent importe ou appelle retrieve_by_intent — "
            "la mémoire doit être injectée via AgentContext."
        )