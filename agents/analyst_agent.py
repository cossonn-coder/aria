# aria/agents/analyst_agent.py

from agents.base_agent import BaseAgent, AgentContext
from cognition.cognitive_context import LLM_ROLE_MAP, CognitiveOperation



PROMPT = """
Tu es un agent cognitif d'Aria.

DOMAINE ACTUEL (tu dois rester dans ce domaine) :
{intent_name}

MESSAGE UTILISATEUR :
{message}

INTENTIONS ACTIVES :
{active_intents}

HISTORIQUE DE CETTE SESSION :
{session_memory}

MÉMOIRE GLOBALE :
{global_memory}

RÈGLES STRICTES :
- Réponds UNIQUEMENT dans le domaine de l'intent actuel
- Si la mémoire contient la réponse → cite-la exactement
- Si c'est une demande de rappel → liste ce qui est en mémoire
- Si c'est une action → décris les étapes
- N'hallucine JAMAIS du contenu absent de la mémoire
- Sois concis
"""


class AnalystAgent(BaseAgent):

    name = "analyst"

    def run(self, ctx: AgentContext, llm_router):

        # intents actifs = sujets traités dans cette session
        active_intents = ctx.extra.get("active_intents", [])
        intents_text = self._format_intents(active_intents)
        operation = ctx.extra.get("cognitive_operation", CognitiveOperation.UNKNOWN)
        role = LLM_ROLE_MAP.get(operation)

        # mémoire session courante
        session_mem = ctx.session_memory

        # mémoire globale
        global_mem = ctx.memories

        prompt = PROMPT.format(
            intent_name=ctx.intent.name,
            message=ctx.message,
            active_intents=self._format_intents(active_intents),
            session_memory=self._format_memories(session_mem),
            global_memory=self._format_memories(global_mem),
        )

        response = llm_router.complete(
            prompt,
            role=role,
            temperature=0.3,
            max_tokens=800,
        )
        ctx.result = response.content
        return ctx

    def _format_intents(self, intents: list) -> str:
        if not intents:
            return "Aucune intention active."
        return "\n".join(
            f"- {i.name} (status: {i.status})"
            for i in intents
        )

    def _format_memories(self, memories: dict) -> str:
        if not memories or not memories.get("hits"):
            return "Aucune mémoire disponible."
        lines = []
        for h in memories["hits"][:5]:
            doc = h.get("text", "")
            if doc:
                lines.append(f"- {doc[:800]}")
        return "\n".join(lines) if lines else "Aucune mémoire disponible."