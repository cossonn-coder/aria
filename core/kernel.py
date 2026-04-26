# aria/core/kernel.py
#
# Orchestrateur central d'ARIA. Responsabilité unique : séquencer le pipeline.
#
# Le kernel ne décide rien, n'exécute rien, ne stocke rien.
# Il reçoit un Event, obtient une décision du CognitiveEngine,
# et délègue l'exécution à l'ExecutionDispatcher.
#
# Pattern constructeur :
#   AriaKernel()                              → auto-wire complet (production)
#   AriaKernel(cognitive_engine=FakeEngine()) → injection partielle (tests)
#
# Flux :
#   Event → CognitiveEngine.classify() → CognitiveResult
#         → ExecutionDispatcher.dispatch() → ExecutionResult
#         → normalisation → str (réponse Telegram)

from config import config

from core.event import Event
from cognition.cognitive_engine import CognitiveEngine, CognitiveResult
from cognition.cognitive_context import CognitiveOperation

from memory.mempalace_bridge import MempalaceBridge

from embedding.embedder import Embedder
from intent.intent_engine import IntentEngine
from llm.llm_router import LLMRouter
from llm.image_router import ImageRouter as InternalImageRouter

from execution.operation import ExecutionOperation
from execution.execution_dispatcher import ExecutionDispatcher
from execution.routing_table import RoutingTable
from execution.router_registry import RouterRegistry
from execution.routers.image_router import ImageExecutionRouter
from execution.routers.llm_router import LLMExecutionRouter
from execution.routers.ingestion_router import IngestionExecutionRouter


# ── Table de routing opération → nom de router ──────────────────────────────
#
# Toutes les CognitiveOperation doivent avoir une entrée ici.
# Ajouter une capacité = ajouter 1 ligne + 1 router. Le kernel ne change pas.

_ROUTING_TABLE = RoutingTable({
    CognitiveOperation.IMAGE_GENERATION.value : "image_router",
    CognitiveOperation.IMAGE_INPUT.value       : "image_router",
    CognitiveOperation.INGESTION.value         : "ingestion_router",
    CognitiveOperation.FACT_RECALL.value       : "llm_router",
    CognitiveOperation.MEMORY_QUERY.value      : "llm_router",
    CognitiveOperation.PLANNING.value          : "llm_router",
    CognitiveOperation.REASONING.value         : "llm_router",
    CognitiveOperation.META_MEMORY.value       : "llm_router",
    CognitiveOperation.PROFILE_QUERY.value     : "llm_router",
    CognitiveOperation.CONFIRMATION.value      : "llm_router",
    CognitiveOperation.UNKNOWN.value           : "llm_router",
})


def _build_dispatcher(llm_router: LLMRouter, intent_engine: IntentEngine) -> ExecutionDispatcher:
    """
    Construit et câble le registre de routers d'exécution.

    Séparé en fonction pour rester testable :
    un test peut appeler _build_dispatcher avec des fakes.
    """
    registry = RouterRegistry()

    # Router image : analyse (IMAGE_INPUT) et génération (IMAGE_GENERATION)
    # llm_router injecté pour la traduction FR→EN des prompts de génération
    registry.register("image_router", ImageExecutionRouter(
        internal_router=InternalImageRouter(),
        intent_engine=intent_engine,
        mempalace_bridge=self.mempalace_bridge,
    ))

    # Router LLM : pipeline cognitif complet (mémoire + intents + agents)
    registry.register("llm_router", LLMExecutionRouter(
        llm_router=llm_router,
        intent_engine=intent_engine,
    ))

    # Router ingestion : stockage direct sans pipeline cognitif
    registry.register("ingestion_router", IngestionExecutionRouter())

    return ExecutionDispatcher(
        registry=registry._routers,
        routing_table=_ROUTING_TABLE,
    )


class AriaKernel:
    """
    Orchestrateur pur.

    Ne contient aucune logique métier.
    Toute décision vit dans CognitiveEngine.
    Toute exécution vit dans les routers.
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine | None = None,
        execution_dispatcher: ExecutionDispatcher | None = None,
    ):
        llm_router = LLMRouter()
        embedder = Embedder(config.EMBEDDING_MODEL)
        intent_engine = IntentEngine(embedder)
        mempalace_bridge = MempalaceBridge()   # ← instanciation ici

        self.cognitive_engine = cognitive_engine or CognitiveEngine(
            llm_router=llm_router,
        )
        self.execution_dispatcher = execution_dispatcher or _build_dispatcher(
            llm_router=llm_router,
            intent_engine=intent_engine,
            mempalace_bridge=mempalace_bridge,

    async def handle_event(self, event: Event) -> str:
        """
        Point d'entrée unique pour tous les events entrants.

        1. classify  → décision cognitive
        2. short_circuit check → réponse directe si applicable
        3. build ExecutionOperation → contrat vers la couche exécution
        4. dispatch → router spécialisé
        5. normalize → str pour la couche interface (Telegram)
        """

        # ── 1. Classification cognitive ──────────────────────────────────────
        cognitive_result: CognitiveResult = self.cognitive_engine.classify(event)

        # ── 2. Short-circuit ────────────────────────────────────────────────
        # Utilisé quand le CognitiveEngine peut répondre sans exécution
        # (ex: réponse en cache, opération non supportée connue, etc.)
        if cognitive_result.short_circuit:
            return cognitive_result.result

        # ── 3. Construction de l'ExecutionOperation ──────────────────────────
        # On passe op_type dans le payload pour que le router puisse distinguer
        # les sous-cas (ex: IMAGE_INPUT vs IMAGE_GENERATION dans ImageExecutionRouter)
        exec_op = ExecutionOperation(
            type=cognitive_result.type,
            payload={
                "op_type": cognitive_result.type,
                "content": event.content,
                "metadata": event.metadata,
            },
            metadata=event.metadata,
        )

        # ── 4. Dispatch vers le router d'exécution ───────────────────────────
        exec_result = self.execution_dispatcher.dispatch(exec_op)

        # ── 5. Normalisation vers str ────────────────────────────────────────
        # ExecutionDispatcher retourne toujours un dict {"status", "data"/"error"}
        return self._normalize(exec_result)

    def _normalize(self, exec_result: dict):
        """
        Traduit un ExecutionResult dict en réponse pour la couche interface.

        Retourne :
        - str               → réponse texte standard
        - dict {"type": "image", "path": ..., "caption": ...}
                            → signal à TelegramInterface d'envoyer send_photo()

        On ne lève jamais d'exception ici.
        """
        if not isinstance(exec_result, dict):
            return str(exec_result)

        if exec_result.get("status") == "success":
            data = exec_result.get("data")

            if isinstance(data, dict):
                # Résultat image : le router retourne "path" + "caption"
                # On détecte par la présence de "path" avec extension image
                path = data.get("path", "")
                if isinstance(path, str) and path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return {
                        "type": "image",
                        "path": path,
                        "caption": data.get("caption", ""),
                    }
                return data.get("text") or str(data)

            if isinstance(data, str):
                return data

            return str(data)

        # Erreur d'exécution — message neutre, pas de crash Telegram
        error = exec_result.get("error", "Erreur interne")
        print(f"[KERNEL] execution error: {error}")
        return "Une erreur s'est produite, réessaie."