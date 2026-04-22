# aria/core/kernel.py

from config import config

from intent.intent_engine import IntentEngine
from memory.mempalace_bridge import retrieve_by_intent, retrieve_memories
from memory.mempalace_writer import store_interaction
from embedding.embedder import Embedder
from llm.llm_router import LLMRouter
from llm.intent_namer import extract_intent_name
from agents.base_agent import AgentContext
from agents.registry_agent import AgentRegistry
from agents.controller.controller_agent import AgentController
from cognition.cognitive_classifier import classify_operation
from cognition.cognitive_context import MEMORY_TOP_K, LLM_ROLE_MAP, CognitiveOperation
from cognition.memory_context import MemoryContext
from cognition.cognitive_trace import CognitiveTrace


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

        # =====================================================
        # AGENTS
        # =====================================================
        self.registry = AgentRegistry()
        self.controller = AgentController(self.registry)

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

        operation = classify_operation(message, self.llm_router)
        print(f"[COGNITION] operation={operation.value}")

        if operation == CognitiveOperation.INGESTION:
            try:
                store_interaction(text=message, intent_id="knowledge_ingest",
                                metadata={"source": "ingest"})
            except Exception as e:
                print(f"[INGEST ERROR] {e}")
            return "[INGESTION] contexte enregistré."
        
        if operation == CognitiveOperation.UNKNOWN:
            return (
                "Je veux bien t'aider — c'est une demande de planning, "
                "une question sur ta mémoire, ou autre chose ?"
            )

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
                intent_id=intent.id
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
        for agent in self.registry.all().values():
            ctx = agent.run(ctx, self.llm_router)
            if ctx.halted:
                break

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