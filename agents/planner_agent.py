# aria/agents/planner_agent.py

from agents.base_agent import BaseAgent, AgentContext
from llm.llm_role import LLMRole
import json

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
- Si une action est nécessaire → donne les étapes numérotées
- Ne planifie pas ce qui est déjà fait ou déjà connu

Réponds UNIQUEMENT avec ce JSON, sans backticks, sans texte autour :
{{"response": "<réponse à afficher à l'utilisateur>", "next_action": "<prochaine action concrète ou null>"}}
"""


class PlannerAgent(BaseAgent):

    name = "planner"

    def run(self, ctx: AgentContext, llm_router):

        if ctx.intent is None:
            return ctx

        prompt = PROMPT.format(
            message=ctx.message,
            intent=ctx.intent.name,
            analysis=ctx.result or "Aucune analyse disponible.",
        )

        response = llm_router.complete(
            prompt,
            role=LLMRole.PLANNING,
            temperature=0.4,
            max_tokens=600,
        )

        parsed = self._parse_response(response.content)

        # seule la réponse va à l'utilisateur
        ctx.result = parsed["response"]

        # next_action sur l'intent, jamais dans le résultat
        if parsed["next_action"] and ctx.intent:
            ctx.intent.set_next_action(parsed["next_action"])

        return ctx

    # =========================================================
    # SAFE PARSER
    # =========================================================
    def _parse_response(self, content: str) -> dict:

        try:
            raw = content.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            return {
                "response": data.get("response", "").strip(),
                "next_action": data.get("next_action") or None,
            }
        except Exception:
            # fallback : tout va dans response, next_action perdu
            return {"response": content.strip(), "next_action": None}


