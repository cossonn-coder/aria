# aria/agents/executor_agent.py

from agents.base_agent import BaseAgent, AgentContext
from llm.llm_router import LLMRouter
from llm.llm_role import LLMRole
from intent.intent import IntentStatus


EXECUTOR_PROMPT = """
Tu es un agent d'exécution.

OBJECTIF :
Produire une action unique et un statut d'intention.

INTENT :
{intent}

PHASE :
{phase}

HISTORIQUE :
{history}

FORMAT STRICT :

ACTION: ...
STATUS: active|completed|paused
"""


class ExecutorAgent(BaseAgent):

    name = "executor"

    def run(self, ctx: AgentContext, llm: LLMRouter) -> AgentContext:

        if ctx.intent is None:
            return ctx

        intent = ctx.intent
        history = intent.actions_history or []

        prompt = EXECUTOR_PROMPT.format(
            intent=intent.subject,
            phase=intent.infer_phase(),
            history="\n".join(history),
        )

        response = llm.complete(
            prompt=prompt,
            role=LLMRole.CHAT,
            temperature=0.3,
            max_tokens=200,
        )

        text = response.content.strip()
        action, status = self._parse_output(text)

        if action:
            intent.next_action = action
            if intent.actions_history is None:
                intent.actions_history = []
            intent.actions_history.append(action)

        if status:
            try:
                intent.status = IntentStatus(status.lower())
            except ValueError:
                pass

        ctx.result = f"Prochaine action : {intent.next_action}"
        return ctx

    def _parse_output(self, text: str):
        action = None
        status = None

        for line in text.splitlines():
            line = line.strip()
            if line.startswith("ACTION:"):
                action = line.replace("ACTION:", "").strip()
            elif line.startswith("STATUS:"):
                status = line.replace("STATUS:", "").strip()

        return action, status