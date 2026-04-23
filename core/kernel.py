# aria/core/kernel.py

from config import config

from intent.intent_engine import IntentEngine
from memory.mempalace_bridge import retrieve_by_intent, retrieve_memories
from memory.mempalace_writer import store_interaction
from embedding.embedder import Embedder
from llm.llm_router import LLMRouter
from llm.intent_namer import extract_intent_name
from llm.image_router import ImageRouter
from images.image_types import ImageInput
from agents.base_agent import AgentContext
from agents.registry_agent import AgentRegistry
from agents.controller.controller_agent import AgentController
from cognition.cognitive_classifier import classify_operation
from cognition.cognitive_context import MEMORY_TOP_K, LLM_ROLE_MAP, CognitiveOperation
from cognition.memory_context import MemoryContext
from cognition.cognitive_trace import CognitiveTrace
from cognition.cognitive_dispatcher import CognitiveDispatcher

FAST_PATH = {
    CognitiveOperation.IMAGE_GENERATION,
    CognitiveOperation.IMAGE_INPUT,
    CognitiveOperation.INGESTION,
    CognitiveOperation.UNKNOWN,
}


def _serialize_artifact(artifact) -> dict:
    """
    Aplatit un ImageArtifact en dict compatible ChromaDB.

    ChromaDB n'accepte que : str, int, float, bool, None.
    - datetime  → isoformat string
    - dict      → str (metadata imbriquée)
    - autre     → str fallback
    """
    result = {}
    for k, v in artifact.__dict__.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = str(v)
        elif v is None or isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return result


class AriaKernel:
    """
    Orchestrateur central.

    Pipeline :
        1. retrieve_memories (MemPalace READ)
        2. intent recall + mutation
        3. cognition (agents + LLM)
        4. persistence (MemPalace WRITE)
    """

    def __init__(self):

        # =====================================================
        # CORE
        # =====================================================
        self.embedder = Embedder(config.EMBEDDING_MODEL)
        self.intent_engine = IntentEngine(self.embedder)
        self.llm_router = LLMRouter()
        self.image_router = ImageRouter()
        self.dispatcher = CognitiveDispatcher()

        # =====================================================
        # AGENTS
        # =====================================================
        self.registry = AgentRegistry()
        self.controller = AgentController(self.registry)

        # =====================================================
        # DISPATCHER
        # =====================================================
        self.dispatcher.register(CognitiveOperation.INGESTION)(
            self.handle_ingestion
        )

        self.dispatcher.register(CognitiveOperation.IMAGE_INPUT)(
            self.handle_image_input
        )

        self.dispatcher.register(CognitiveOperation.IMAGE_GENERATION)(
            self.handle_image_generation
        )

        self.dispatcher.register(CognitiveOperation.UNKNOWN)(
            self.handle_unknown
        )

    # =========================================================
    # ENTRYPOINT
    # =========================================================

    async def handle_message(self, message: str, metadata: dict | None = None) -> str:

        metadata = metadata or {}

        # =====================================================
        # 0 — MESSAGE CLASSIFICATION
        # =====================================================
        message = message.strip()
        if not message:
            return ""

        operation = classify_operation(
            message,
            self.llm_router,
            metadata=metadata
        )

        print(f"[COGNITION] operation={operation.value}")

        dispatch_out = self.dispatcher.dispatch(operation, message, metadata)

        if dispatch_out["short_circuit"]:
            return dispatch_out["result"]

        # =====================================================
        # 1 — GLOBAL MEMORY (pre-intent context)
        # =====================================================
        top_k = MEMORY_TOP_K.get(operation, 4)
        memory_context = MemoryContext(
            global_memories=retrieve_memories(message, n=top_k),
            session_memories={},
        )

        # =====================================================
        # 2 — INTENT RECALL
        # =====================================================
        active_intents = self.intent_engine.list_attention_active()

        recall_decision, matches = self.intent_engine.resolve(
            message,
            active_intents,
            memory_context=memory_context.global_memories
        )

        # =====================================================
        # 3 — INTENT MUTATION
        # =====================================================
        intent_name = None
        if recall_decision.action == "create":
            intent_name = extract_intent_name(message, self.llm_router)

        intent = self.intent_engine.apply(
            decision=recall_decision,
            message=message,
            intent_name=intent_name,
        )

        # =====================================================
        # 4 — SESSION MEMORY (post-intent context)
        # =====================================================
        memory_context = MemoryContext(
            global_memories=retrieve_memories(message, n=top_k),
            session_memories=retrieve_by_intent(
                query=message,
                intent_id=intent.id,
            ) if intent else {"hits": [], "count": 0},
        )

        # =====================================================
        # 5 — CONTEXT BUILD
        # =====================================================
        trace = CognitiveTrace()

        ctx = AgentContext(
            message=message,
            intent=intent,
            memories=memory_context.global_memories,
            session_memory=memory_context.session_memories,
            trace=trace,
            extra={
                "memory_context": memory_context,
                "recall": recall_decision,
                "active_intents": self.intent_engine.list_active(),
                "cognitive_operation": operation,
                **metadata,
            },
        )

        # =====================================================
        # 6 — COGNITION PIPELINE
        # =====================================================
        ctx = self.controller.run(ctx, self.llm_router)

        # =====================================================
        # 7 — RESULT RESOLUTION
        # =====================================================
        if ctx.result:
            result = ctx.result
        elif ctx.intent and hasattr(ctx.intent, "last_state"):
            result = ctx.intent.last_state
        else:
            result = f"[NO RESULT] intent={ctx.intent.id if ctx.intent else None}"

        # =====================================================
        # 8 — INTENT PERSISTENCE
        # =====================================================
        if intent:
            intent.activate()
            self.intent_engine.save(intent)

        # =====================================================
        # 9 — DECAY
        # =====================================================
        self.intent_engine.decay_if_needed()

        # =====================================================
        # 10 — MEMPALACE WRITE
        # =====================================================
        try:
            if intent:
                store_interaction(
                    text=f"USER:\n{message}\n\nARIA:\n{result}",
                    intent_id=intent.id,
                    metadata={
                        "intent_name": intent.name,
                        "wing": "aria",
                        "room": intent.id,
                        "source": "kernel",
                    },
                )
        except Exception as e:
            print(f"[MEMORY WRITE ERROR] {e}")

        print("\n[COGNITIVE TRACE]")
        for step in ctx.trace.as_dict():
            print(step)

        self.last_ctx = ctx

        return result

    # =========================================================
    # TERMINAL HANDLERS
    # =========================================================

    def handle_ingestion(self, message, metadata):
        store_interaction(
            text=message,
            intent_id="knowledge_ingest",
            metadata={"source": "ingest"},
        )
        return "[INGESTION] contexte enregistré."

    def handle_image_input(self, message, metadata):
        img_path = metadata.get("image")
        artifact = self.image_router.handle_input(ImageInput(path=img_path))
        store_interaction(
            text=artifact.caption or artifact.path,
            intent_id=metadata.get("intent_id", "image_input"),
            metadata={"type": "image_input", **_serialize_artifact(artifact)},
        )
        return artifact

    def handle_image_generation(self, message, metadata):
        artifact = self.image_router.generate(
            message,
            intent_id=metadata.get("intent_id")
        )
        store_interaction(
            text=artifact.prompt,
            intent_id=artifact.intent_id or "image_generation",
            metadata={"type": "image_generated", **_serialize_artifact(artifact)},
        )
        return artifact.path

    def handle_unknown(self, message, metadata):
        return (
            "Je veux bien t'aider — c'est une demande de planning, "
            "une question sur ta mémoire, ou autre chose ?"
        )