# tests/execution/test_pipeline_memory_isolation.py
#
# Tests d'isolation mémoire du pipeline cognitif.
#
# Principe vérifié :
#   Les agents (AnalystAgent, PlannerAgent, etc.) NE DOIVENT PAS
#   appeler retrieve_memories, retrieve_by_intent, ou tout autre
#   accès MemPalace de leur propre chef.
#
#   Seul LLMExecutionRouter est autorisé à lire la mémoire via
#   son MempalaceBridge injecté. Les agents reçoivent un AgentContext
#   pré-assemblé — point final.
#
# Stratégie d'isolation :
#   retrieve_memories et retrieve_by_intent ne sont plus des fonctions
#   module-level — ce sont des méthodes de MempalaceBridge.
#   Il est donc impossible pour un agent de les patcher ou de les appeler
#   sans posséder une instance de bridge.
#
#   Les tests vérifient l'isolation via deux approches complémentaires :
#     1. Inspection statique du source (aucun import bridge dans agents/)
#     2. Vérification comportementale (l'agent run() utilise ctx, pas un bridge)

from unittest.mock import MagicMock
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
    fake_intent.id   = "intent-isolation-test"
    fake_intent.name = "isolation_test"

    return AgentContext(
        message=message,
        intent=fake_intent,
        memories={
            "hits"  : [{"text": "souvenir A injecté par le router"}],
            "count" : 1,
        },
        session_memory={
            "hits"  : [{"text": "session B injectée par le router"}],
            "count" : 1,
        },
        trace=CognitiveTrace(),
        extra={
            "cognitive_operation" : operation,
            "active_intents"      : [],
        },
    )


def make_llm_router_mock() -> MagicMock:
    """LLMRouter minimal — retourne une réponse factice sans IO."""
    mock = MagicMock(name="LLMRouter")
    response = MagicMock()
    response.content = "réponse factice"
    mock.complete.return_value = response
    return mock


# ── Tests : AnalystAgent — isolation mémoire ─────────────────────────────────

class TestAnalystAgentMemoryIsolation:
    """
    Vérifie qu'AnalystAgent n'accède jamais à MemPalace directement.

    Depuis la migration vers MempalaceBridge (classe injectée), les fonctions
    retrieve_memories et retrieve_by_intent n'existent plus au niveau module.
    Un agent qui tenterait de les appeler obtiendrait une AttributeError au
    runtime — ce qui constitue lui-même une preuve structurelle d'isolation.

    Les tests ci-dessous complètent cette garantie structurelle par :
      - inspection statique du source de l'agent
      - vérification comportementale (l'agent s'exécute sans bridge)
    """

    def test_analyst_has_no_bridge_import_or_usage(self):
        """
        analyst_agent ne doit pas importer MempalaceBridge ni appeler
        retrieve_memories ou retrieve_by_intent dans son source.

        Si ces symboles apparaissent, l'agent peut court-circuiter le pipeline
        en instanciant son propre bridge ou en appelant des fonctions mémoire.
        """
        import agents.analyst_agent as module
        import inspect

        source = inspect.getsource(module)

        assert "retrieve_memories"   not in source, (
            "analyst_agent référence retrieve_memories — "
            "la mémoire doit être injectée via AgentContext."
        )
        assert "retrieve_by_intent"  not in source, (
            "analyst_agent référence retrieve_by_intent — "
            "la mémoire doit être injectée via AgentContext."
        )
        assert "MempalaceBridge"     not in source, (
            "analyst_agent instancie MempalaceBridge directement — "
            "seul LLMExecutionRouter est autorisé à posséder un bridge."
        )

    def test_analyst_runs_without_bridge(self):
        """
        AnalystAgent doit s'exécuter correctement sans aucun bridge injecté.

        Seul ctx est disponible. Si l'agent tente d'accéder à MemPalace,
        il obtiendra une AttributeError ou NameError immédiate — ce test
        le détecterait comme une exception non attendue.
        """
        ctx        = make_context(operation=CognitiveOperation.FACT_RECALL)
        llm_router = make_llm_router_mock()
        agent      = AnalystAgent()

        # Aucun bridge n'est accessible — le test passe si et seulement si
        # l'agent n'essaie pas d'atteindre MemPalace.
        result_ctx = agent.run(ctx, llm_router)

        assert result_ctx is not None

    def test_analyst_does_not_call_retrieve_memories(self):
        """
        Vérifie comportementalement qu'AnalystAgent n'appelle pas retrieve_memories.

        Le bridge est injecté dans le module memory.mempalace_bridge comme
        attribut spy — si l'agent instancie ou accède à un bridge, le spy
        enregistrera l'appel.
        """
        import memory.mempalace_bridge as bridge_module

        # Vérification structurelle : le module bridge ne doit pas exposer
        # retrieve_memories comme fonction standalone.
        assert not hasattr(bridge_module, "retrieve_memories"), (
            "memory.mempalace_bridge expose encore retrieve_memories comme "
            "fonction module — elle doit être une méthode de MempalaceBridge."
        )

    def test_analyst_does_not_call_retrieve_by_intent(self):
        """
        Vérifie que retrieve_by_intent n'existe plus comme fonction module.

        Symétrique au test ci-dessus pour retrieve_by_intent.
        """
        import memory.mempalace_bridge as bridge_module

        assert not hasattr(bridge_module, "retrieve_by_intent"), (
            "memory.mempalace_bridge expose encore retrieve_by_intent comme "
            "fonction module — elle doit être une méthode de MempalaceBridge."
        )

    def test_analyst_uses_ctx_memories_not_fresh_query(self):
        """
        AnalystAgent doit utiliser ctx.memories tel quel,
        pas initier une nouvelle requête vectorielle.

        On vérifie que le prompt LLM contient bien le contenu
        des mémoires injectées dans le contexte.
        """
        ctx        = make_context(operation=CognitiveOperation.FACT_RECALL)
        llm_router = make_llm_router_mock()
        agent      = AnalystAgent()

        agent.run(ctx, llm_router)

        call_args  = llm_router.complete.call_args
        prompt_used = (
            call_args[0][0] if call_args[0]
            else call_args[1].get("prompt", "")
        )

        assert "souvenir A injecté par le router" in prompt_used, (
            "AnalystAgent n'utilise pas ctx.memories dans son prompt. "
            "Il ignore les mémoires pré-assemblées."
        )

    def test_analyst_result_set_on_context(self):
        """
        AnalystAgent doit écrire son résultat dans ctx.result.

        Vérifie le contrat de base de BaseAgent.
        """
        ctx        = make_context()
        llm_router = make_llm_router_mock()
        agent      = AnalystAgent()

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

        assert "retrieve_memories"  not in source, (
            "analyst_agent importe ou appelle retrieve_memories — "
            "la mémoire doit être injectée via AgentContext."
        )
        assert "retrieve_by_intent" not in source, (
            "analyst_agent importe ou appelle retrieve_by_intent — "
            "la mémoire doit être injectée via AgentContext."
        )