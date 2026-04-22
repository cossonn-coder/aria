#aria/agents/registry_agent.py
from agents.analyst_agent import AnalystAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.critic_agent import CriticAgent


class AgentRegistry:
    """
    Registre central des agents cognitifs.

    - instancie les agents une seule fois
    - fournit un accès par nom
    """

    def __init__(self):

        self._agents = {
            "analyst": AnalystAgent(),
            "planner": PlannerAgent(),
            "executor": ExecutorAgent(),
            "critic": CriticAgent(),
        }

    def get(self, name: str):
        return self._agents.get(name)

    def all(self):
        return self._agents