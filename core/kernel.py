# aria/core/kernel.py

from config import config

from intent import intent_engine
from intent.intent_engine import IntentEngine
from memory.mempalace_bridge import retrieve_memories
from memory.mempalace_writer import store_interaction
from embedding.embedder import Embedder
from llm.llm_router import LLMRouter
from llm.intent_namer import extract_intent_name
from agents.base_agent import AgentContext
from agents.registry_agent import AgentRegistry
from agents.controller.controller_agent import AgentController
from cognition.cognitive_classifier import classify_operation
from cognition.cognitive_context import MEMORY_TOP_K, LLM_ROLE_MAP, CognitiveOperation


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
        # 1 — MEMORY (filtrée par opération)
        # =====================================================
        top_k = MEMORY_TOP_K.get(operation, 4)
        memories = retrieve_memories(message, n=top_k) if top_k > 0 else {"hits": [], "count": 0}

        # =====================================================
        # 2 — INTENT RECALL
        # =====================================================
        active_intents = self.intent_engine.list_attention_active()

        recall_decision, matches = self.intent_engine.resolve(
            message,
            active_intents,
            memory_context=memories
        )

        print("\n[KERNEL DEBUG]")
        print(f"message={message}")
        print(f"recall_action={recall_decision.action}")
        print(f"matches={len(matches)}")

        # =====================================================
        # 3 — INTENT MUTATION
        # =====================================================
        # extraction nom canonique uniquement sur CREATE
        intent_name = None
        if recall_decision.action == "create":
            intent_name = extract_intent_name(message, self.llm_router)
            print(f"intent_name={intent_name}")

        intent = self.intent_engine.apply(
            decision=recall_decision,
            message=message,
            intent_name=intent_name,
        )

        print(f"intent={intent.id if intent else None}")

        # =====================================================
        # 4 — CONTEXT BUILD
        # =====================================================
        ctx = AgentContext(
            message=message,
            intent=intent,
            memories=memories,
            extra={
                "recall": recall_decision,
                "active_intents": self.intent_engine.list_active(),
                "cognitive_operation": operation,   # ← ajout
                **metadata,
            },
        )

        # =====================================================
        # 5 — COGNITION PIPELINE
        # =====================================================
        ctx = self.controller.run(ctx, self.llm_router)

        # =====================================================
        # 6 — RESULT RESOLUTION
        # =====================================================
        if ctx.result:
            result = ctx.result

        elif ctx.intent and hasattr(ctx.intent, "last_state"):
            result = ctx.intent.last_state

        else:
            result = f"[NO RESULT] intent={ctx.intent.id if ctx.intent else None}"

        # =====================================================
        # 7 — INTENT PERSISTENCE (IN MEMORY ENGINE)
        # =====================================================
        if intent:
            self.intent_engine.save(intent)

        # ====
        # DECAY
        # ====
        intent.activate()
        self.intent_engine.decay_if_needed()

        # =====================================================
        # 8 — MEMPALACE WRITE (CRITICAL FIX)
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

        return result