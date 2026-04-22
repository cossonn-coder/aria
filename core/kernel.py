# aria/core/kernel.py

from config import config

from intent.intent_engine import IntentEngine
from memory.mempalace_bridge import retrieve_by_intent, retrieve_memories
from memory.mempalace_writer import store_interaction
from embedding.embedder import Embedder
from llm.llm_router import LLMRouter
from llm.intent_namer import extract_intent_name
from llm.image_router import ImageRouter
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
            session_memories={},  # pas encore calculé
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
        # 5 — CONTEXT BUILD (CRITICAL STEP MISSING IN CURRENT CODE)
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
        # 8 — INTENT PERSISTENCE (IN MEMORY ENGINE)
        # =====================================================
        if intent:
            intent.activate()
            self.intent_engine.save(intent)

        # =================================================
        # 9 — DECAY
        # =================================================

        self.intent_engine.decay_if_needed()

        # =====================================================
        # 10 — MEMPALACE WRITE (CRITICAL FIX)
        # =====================================================
        # Triggered ONLY after full reasoning completion
        # → avoids storing intermediate/noisy states

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

        self.last_ctx = ctx  # pour debug / inspection post-run

        return result
    

    def handle_ingestion(self, message, metadata):
        store_interaction(
            text=message,
            intent_id="knowledge_ingest",
            metadata={"source": "ingest"}
        )
        return "[INGESTION] contexte enregistré."


    def handle_image_input(self, message, metadata):
        img_path = metadata.get("image")

        store_interaction(
            text=f"[IMAGE_INPUT] {img_path}",
            intent_id="image_input",
            metadata={
                "type": "image_input",
                "wing": "aria",
                "room": "image_input",
                "path": img_path,
            },
        )

        return self.image_router.handle_input(img_path)


    def handle_image_generation(self, message, metadata):
        result = self.image_router.generate(message)

        store_interaction(
            text=f"[IMAGE_GENERATION] {message}",
            intent_id="image_generation",
            metadata={
                "type": "image_generated",
                "wing": "aria",
                "room": metadata.get("intent_id", "image_generation"),
                "path": result.path,
                "prompt": message,
            },
        )

        return result.path


    def handle_unknown(self, message, metadata):
        return "Je veux bien t'aider — c'est une demande de planning, " "une question sur ta mémoire, ou autre chose ?"