# aria/execution/routers/llm_router.py
#
# Router d'exécution pour toutes les opérations textuelles cognitives.
#
# C'est le router le plus complexe du système : il porte le pipeline
# cognitif complet d'ARIA (mémoire + intents + agents + persistence).
#
# Pourquoi ici et pas dans le kernel ?
#   Le kernel orchestre — il ne connaît pas le pipeline cognitif texte.
#   Ce router est l'effecteur de toutes les CognitiveOperation textuelles :
#   FACT_RECALL, MEMORY_QUERY, PLANNING, REASONING, META_MEMORY,
#   PROFILE_QUERY, CONFIRMATION, UNKNOWN.
#
# Pipeline interne :
#   1. Mémoire globale (retrieve_memories)
#   2. Intent recall (resolve)
#   3. Intent mutation (create si nécessaire)
#   4. Mémoire de session (retrieve_by_intent)
#   5. Construction AgentContext
#   6. Pipeline agents (AgentController)
#   7. Résolution du résultat
#   8. Persistence intent
#   9. Decay
#   10. Écriture MemPalace

from execution.routers.execution_base import BaseRouter

from intent.intent_engine import IntentEngine
from llm.llm_router import LLMRouter
from memory.mempalace_writer import store_interaction
from memory.mempalace_bridge import MempalaceBridge
from llm.intent_namer import extract_intent_name
from agents.base_agent import AgentContext
from agents.registry_agent import AgentRegistry
from agents.controller.controller_agent import AgentController
from cognition.cognitive_context import MEMORY_TOP_K, LLM_ROLE_MAP, CognitiveOperation
from cognition.memory_context import MemoryContext
from cognition.cognitive_trace import CognitiveTrace


class LLMExecutionRouter(BaseRouter):
    """
    Effecteur du pipeline cognitif texte.

    Reçoit un payload normalisé depuis AriaKernel et exécute
    le pipeline complet : mémoire → intents → agents → persistence.

    Args:
        llm_router       : LLMRouter (multi-provider avec fallback)
        intent_engine    : IntentEngine (gestion cycle de vie des intents)
        mempalace_bridge : MempalaceBridge (lecture mémoire épisodique)
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        intent_engine: IntentEngine,
        mempalace_bridge: MempalaceBridge,
    ):
        self.llm_router = llm_router
        self.intent_engine = intent_engine
        self.mempalace_bridge = mempalace_bridge

        # Registre et contrôleur agents — construits une seule fois au démarrage.
        # Ils sont stateless entre les appels : pas de risque de contamination
        # d'état entre deux cycles cognitifs.
        self.registry = AgentRegistry()
        self.controller = AgentController(self.registry)

    def execute(self, payload: dict) -> dict:
        """
        Exécute le pipeline cognitif complet pour un message texte.

        Contrat de sortie :
            {"text": str}   — texte de réponse destiné à _normalize() du kernel

        payload attendu :
            op_type  : str (valeur de CognitiveOperation)
            content  : str (message utilisateur)
            metadata : dict
        """
        message = payload.get("content", "")
        metadata = payload.get("metadata", {})
        op_type = payload.get("op_type", CognitiveOperation.UNKNOWN.value)

        try:
            operation = CognitiveOperation(op_type)
        except ValueError:
            operation = CognitiveOperation.UNKNOWN

        result = self._run_pipeline(message, operation, metadata)
        return {"text": result}

    def _run_pipeline(self, message: str, operation: CognitiveOperation, metadata: dict) -> str:
        """
        Pipeline cognitif complet.

        Chaque étape est numérotée pour faciliter le debug
        et correspondre aux logs [COGNITIVE TRACE].
        """

        # ── 1. Mémoire globale (contexte pré-intent) ────────────────────────
        # Résolution unique — global_memories est réutilisé à l'étape 4.
        # top_k est fixé ici : toutes les étapes suivantes travaillent
        # avec le même budget mémoire pour ce cycle.
        top_k = MEMORY_TOP_K.get(operation, 4)
        global_memories = self.mempalace_bridge.retrieve_memories(message, n=top_k)

        memory_context = MemoryContext(
            global_memories=global_memories,
            session_memories={},
        )

        # ── 2. Intent recall ────────────────────────────────────────────────
        active_intents = self.intent_engine.list_attention_active()

        recall_decision, _ = self.intent_engine.resolve(
            message,
            active_intents,
            memory_context=memory_context.global_memories,
        )

        # ── 3. Intent mutation ──────────────────────────────────────────────
        # Extraction du nom canonique uniquement si création d'un nouvel intent.
        # Ce LLM call est coûteux — on ne l'effectue qu'en cas de nécessité.
        intent_name = None
        if recall_decision.action == "create":
            intent_name = extract_intent_name(message, self.llm_router)

        intent = self.intent_engine.apply(
            decision=recall_decision,
            message=message,
            intent_name=intent_name,
        )

        # ── 4. Mémoire de session (contexte post-intent) ────────────────────
        # retrieve_by_intent cible les souvenirs liés à l'intent résolu —
        # plus précis que la mémoire globale pour ancrer la réponse.
        # global_memories est réutilisé depuis l'étape 1 : inutile de
        # rappeler retrieve_memories avec les mêmes paramètres.
        session_memories = (
            self.mempalace_bridge.retrieve_by_intent(query=message, intent_id=intent.id)
            if intent
            else {"hits": [], "count": 0}
        )

        memory_context = MemoryContext(
            global_memories=global_memories,   # déjà résolu à l'étape 1
            session_memories=session_memories,
        )

        # ── 5. Construction du contexte agent ───────────────────────────────
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

        # ── 6. Pipeline agents ───────────────────────────────────────────────
        ctx = self.controller.run(ctx, self.llm_router)

        # ── 7. Résolution du résultat ────────────────────────────────────────
        # Priorité : résultat direct du pipeline agents, puis dernier état
        # de l'intent, puis fallback de debug explicite (jamais silencieux).
        if ctx.result:
            result = ctx.result
        elif ctx.intent and hasattr(ctx.intent, "last_state"):
            result = ctx.intent.last_state
        else:
            result = f"[NO RESULT] intent={ctx.intent.id if ctx.intent else None}"

        # ── 8. Persistence intent ────────────────────────────────────────────
        if intent:
            intent.activate()
            self.intent_engine.save(intent)

        # ── 9. Decay ────────────────────────────────────────────────────────
        self.intent_engine.decay_if_needed()

        # ── 10. Écriture MemPalace ───────────────────────────────────────────
        # Écriture après résolution complète — jamais sur un état intermédiaire.
        # Non bloquant : une erreur mémoire ne doit pas tuer la réponse.
        try:
            if intent:
                store_interaction(
                    text=f"USER:\n{message}\n\nARIA:\n{result}",
                    intent_id=intent.id,
                    metadata={
                        "intent_name": intent.name,
                        "wing": "aria",
                        "room": intent.id,
                        "source": "llm_execution_router",
                    },
                )
        except Exception as e:
            from logger import get_logger
            log = get_logger(__name__)
            log.error("[MEMORY WRITE ERROR] : %s", e)

        from logger import get_logger
        log = get_logger(__name__)
        log.info("pipeline done → %d chars", len(result))
        for step in ctx.trace.as_dict():
            log.debug("trace: %s", step)

        return result