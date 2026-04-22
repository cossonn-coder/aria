from agents.base_agent import BaseAgent, AgentContext
from llm.llm_router import LLMRouter
from llm.llm_role import LLMRole

CRITIC_PROMPT = """
Tu es un agent critique.

MISSION :
Analyser la réponse produite et détecter :

- incohérences
- actions irréalistes
- manque d'information
- risques
- simplifications abusives

CONTEXTE :
Intent : {intent}
Phase : {phase}

RÉPONSE ACTUELLE :
{result}

RÈGLES :
- réponse courte
- uniquement critiques utiles
- pas de reformulation
- pas de politesse
"""


class CriticAgent(BaseAgent):

    name = "critic"

    def run(self, ctx: AgentContext, llm: LLMRouter) -> AgentContext:

        if not ctx.result:
            return ctx

        prompt = CRITIC_PROMPT.format(
            intent=ctx.intent.subject,
            phase=ctx.intent.infer_phase(),
            result=ctx.result,
        )

        response = llm.complete(
            prompt=prompt,
            role=LLMRole.CHAT,
            temperature=0.2,
            max_tokens=300,
        )

        critique = response.content.strip()

        # on stocke la critique sans écraser le résultat
        ctx.extra["critique"] = critique

        return ctx