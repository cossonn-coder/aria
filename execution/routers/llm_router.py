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
from config import config
from logger import get_logger

from intent.intent_engine import IntentEngine
from intent.intent_recall_engine import RecallDecision
from llm.llm_router import LLMRouter
from memory.writer import write_interaction, write_conversation_turn
from memory.mempalace_bridge import MempalaceBridge
from llm.intent_namer import extract_intent_name
from agents.base_agent import AgentContext
from agents.registry_agent import AgentRegistry
from agents.controller.controller_agent import AgentController
from cognition.cognitive_context import MEMORY_TOP_K, LLM_ROLE_MAP, CognitiveOperation
from cognition.memory_context import MemoryContext
from cognition.cognitive_trace import CognitiveTrace
from cognition.context_builder import build_context_block

log = get_logger(__name__)

# Plafonds de l'historique conversationnel passé à l'analyst (sprint 33).
# Raison : les messages user enrichis (blocs de faits d'échecs, pages web)
# sont relus tels quels en historique et faisaient sauter Groq sur un simple
# « salut » (36 813 car. de payload). Même idiome que GROQ_MAX_PAYLOAD_CHARS.
HISTORY_MESSAGE_MAX_CHARS = 1_500
HISTORY_BUDGET_CHARS = 6_000


def _trim_history(history: list[dict]) -> list[dict]:
    """
    Plafonne l'historique : chaque message coupé à HISTORY_MESSAGE_MAX_CHARS
    (suffixe « […] »), total borné à HISTORY_BUDGET_CHARS.

    Rempli du plus récent au plus ancien ; arrêt au premier message qui
    ferait dépasser le budget (fenêtre contiguë, pas de trou).
    Rendu en ordre chronologique, comme le bridge.
    """
    kept: list[dict] = []
    total = 0
    for turn in reversed(history):
        content = turn.get("content", "")
        if len(content) > HISTORY_MESSAGE_MAX_CHARS:
            content = content[:HISTORY_MESSAGE_MAX_CHARS] + " […]"
        if total + len(content) > HISTORY_BUDGET_CHARS:
            break
        kept.append({**turn, "content": content})
        total += len(content)
    kept.reverse()
    return kept


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

        # ── 1b. Historique conversationnel (wing aria_conversation) ─────────
        # Chargé avant l'intent : le namer (étape 3) lit le tour précédent.
        # Clé = chat_id Telegram (passé en metadata), "default" sinon.
        # Convention : max_history_turns compte des tours (user + assistant),
        # load_conversation_history compte des messages → n = tours × 2.
        # C'est le router qui lit, jamais l'agent (règle inviolable 3).
        conversation_key = str(metadata.get("chat_id", "default"))
        # Drapeau skip_history (analyse de partie, sprint 29) : les réponses
        # passées servaient de moule au LLM. L'échange reste écrit en fin de
        # pipeline pour les questions de suivi.
        if metadata.get("skip_history"):
            conversation_history = []
            log.info("conversation_history SKIPPED reason=skip_history")
        else:
            conversation_history = _trim_history(
                self.mempalace_bridge.load_conversation_history(
                    conversation_key, n=config.max_history_turns * 2,
                )
            )
            log.info(
                "conversation_history loaded key=%s messages=%d chars=%d",
                conversation_key, len(conversation_history),
                sum(len(t.get("content", "")) for t in conversation_history),
            )

        # ── 2-3. Drapeau skip_intent (photo interrogative, #51) ─────────────
        # Le message enrichi d'une photo ne doit ni résoudre, ni créer, ni
        # modifier un intent : sinon la description vision devient un
        # « projet » présenté à l'agent. Le reste du pipeline est inchangé.
        if metadata.get("skip_intent"):
            log.info("intent SKIPPED reason=skip_intent")
            recall_decision = None
            intent = None
        elif metadata.get("forced_intent_name"):
            # ── 2-3 bis. Nom d'intent imposé (analyse de partie, audit 05) ──
            # Le namer répondait « aucun » sur un PGN enrichi → échange non
            # écrit en épisodique (bug 1). Le router appelant impose le nom :
            # ni resolve (pour ne pas rattacher la partie à un autre projet),
            # ni namer. apply en CREATE retrouve l'intent du même nom, sinon le crée.
            forced_name = metadata["forced_intent_name"]
            log.info("intent FORCED name=%s", forced_name)
            recall_decision = RecallDecision(action="create")
            intent = self.intent_engine.apply(
                decision=recall_decision,
                message=message,
                intent_name=forced_name,
            )
        else:
            # ── 2. Intent recall ────────────────────────────────────────────
            active_intents = self.intent_engine.list_attention_active()

            recall_decision, _ = self.intent_engine.resolve(
                message,
                active_intents,
                memory_context=memory_context.global_memories,
            )

            # ── 3. Intent mutation ──────────────────────────────────────────
            # Le namer (appel LLM coûteux) n'est sollicité qu'en create/split.
            # Il reçoit le contexte (tour user précédent + intents actifs) et
            # peut répondre un nom existant (→ rattachement dans apply), un
            # nouveau nom, ou « aucun » → pas d'intent pour ce message (#59).
            intent_name = None
            skip_apply = False
            if recall_decision.action in ("create", "split"):
                user_turns = [t["content"] for t in conversation_history if t.get("role") == "user"]
                previous_message = user_turns[-1] if user_turns else None
                intent_name = extract_intent_name(
                    message,
                    self.llm_router,
                    previous_message=previous_message,
                    active_intent_names=[i.name for i in active_intents],
                )
                skip_apply = intent_name is None

            if skip_apply:
                log.info("intent SKIPPED reason=namer_aucun")
                intent = None
            else:
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

        # ── 4b. Context builder (sémantique + intents + budget tokens) ─────────
        context_block = build_context_block(
            query=message,
            bridge=self.mempalace_bridge,
            active_intents=self.intent_engine.list_attention_active(),
            session_memories=session_memories,
            global_memories=global_memories,
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
                "context_block": context_block,
                "conversation_history": conversation_history,
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
        if intent is None:
            log.info("memory_write SKIPPED reason=no_intent_resolved")
        else:
            try:
                write_interaction(
                    text=f"USER:\n{message}\n\nARIA:\n{result}",
                    intent_id=intent.id,
                    intent_name=intent.name,
                    source="llm_execution_router",
                )
                log.info(
                    "memory_write OK wing=aria_episodic intent_id=%s intent_name=%s",
                    intent.id, intent.name,
                )
            except Exception:
                log.exception(
                    "memory_write ERROR intent_id=%s intent_name=%s",
                    intent.id, intent.name,
                )

        # Historique conversationnel : écrit même sans intent résolu
        # (amendement Nico 2026-10-15). Même politique non bloquante.
        try:
            write_conversation_turn(conversation_key, "user", message)
            write_conversation_turn(conversation_key, "assistant", result)
            log.info("conversation_write OK key=%s", conversation_key)
        except Exception:
            log.exception("conversation_write ERROR key=%s", conversation_key)

        log.info("pipeline done → %d chars", len(result))
        for step in ctx.trace.as_dict():
            log.debug("trace: %s", step)

        return result