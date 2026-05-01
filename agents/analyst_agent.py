# aria/agents/analyst_agent.py

from agents.base_agent import BaseAgent, AgentContext
from cognition.cognitive_context import LLM_ROLE_MAP, CognitiveOperation



PROMPT = """
Tu es un agent cognitif d'Aria, assistant personnel de Nico.

PROJET RÉCENT EN MÉMOIRE :
{intent_name}

MESSAGE UTILISATEUR :
{message}

HISTORIQUE DE CETTE SESSION :
{session_memory}

CONTEXTE COGNITIF :
{context_block}

RÈGLES :
- Réponds toujours à la question posée, quel que soit le sujet
- Si la mémoire contient la réponse → cite-la exactement
- Si c'est une demande de rappel → liste ce qui est en mémoire
- Si c'est une action → décris les étapes
- N'hallucine JAMAIS du contenu absent de la mémoire
- Sois concis
"""


class AnalystAgent(BaseAgent):

    name = "analyst"

    def run(self, ctx: AgentContext, llm_router):

        operation = ctx.extra.get("cognitive_operation", CognitiveOperation.UNKNOWN)
        role = LLM_ROLE_MAP.get(operation)

        prompt = PROMPT.format(
            intent_name=ctx.intent.name,
            message=ctx.message,
            session_memory=self._format_memories(ctx.session_memory),
            context_block=ctx.extra.get("context_block", "Aucun contexte disponible."),
        )

        response = llm_router.complete(
            prompt,
            role=role,
            temperature=0.3,
            max_tokens=800,
        )
        ctx.result = response.content
        return ctx

    def _format_memories(self, memories: dict) -> str:
        if not memories or not memories.get("hits"):
            return "Aucune mémoire disponible."
        lines = []
        for h in memories["hits"][:5]:
            doc = h.get("text", "")
            if doc:
                lines.append(f"- {doc[:800]}")
        return "\n".join(lines) if lines else "Aucune mémoire disponible."