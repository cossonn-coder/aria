# aria/agents/planner_agent.py

from agents.base_agent import BaseAgent, AgentContext
from llm.llm_role import LLMRole

PROMPT = """
Tu es un agent cognitif d'Aria.

MESSAGE :
{message}

INTENT :
{intent}

CONTEXTE (résultat analyse) :
{analysis}

RÈGLES :
- Si l'analyse contient déjà une réponse directe → transmets-la sans reformuler
- Si une action est nécessaire → donne les étapes numérotées + NEXT_ACTION
- Ne planifie pas ce qui est déjà fait ou déjà connu
"""


class PlannerAgent(BaseAgent):

    name = "planner"

    def run(self, ctx: AgentContext, llm_router):

        # =====================================================
        # SAFETY CHECK
        # =====================================================
        if ctx.intent is None:
            return ctx

        # =====================================================
        # CONTEXT BUILD (stable source)
        # =====================================================
        context = {
            "message": ctx.message,
            "memories": ctx.memories,
            "extra": ctx.extra,
        }

        prompt = PROMPT.format(
            message=ctx.message,
            intent=ctx.intent.name,
            analysis=ctx.result or "Aucune analyse disponible.",  # ← fix + renommage
        )

        response = llm_router.complete(
            prompt,
            role=LLMRole.PLANNING,
            temperature=0.4,
            max_tokens=600,
        )

        # =====================================================
        # OUTPUT ISOLATION
        # =====================================================
        content = response.content.strip()

        ctx.result = content

        # =====================================================
        # INTENT UPDATE (SAFE PARSING)
        # =====================================================
        next_action = self._extract_next_action(content)

        if next_action and ctx.intent:
            ctx.intent.set_next_action(next_action)

        return ctx

    # =========================================================
    # SAFE PARSER
    # =========================================================

    def _extract_next_action(self, text: str) -> str | None:
        """
        Extraction robuste du NEXT_ACTION.
        Évite dépendance à split fragile.
        """

        lines = text.splitlines()

        for i, line in enumerate(lines):
            if "NEXT_ACTION" in line and i + 1 < len(lines):
                return lines[i + 1].strip()

        return None