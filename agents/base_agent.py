# aria/agents/base_agent.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from intent.intent import Intent


# =========================================================
# AGENT CONTEXT
# =========================================================

@dataclass
class AgentContext:
    """
    Runtime cognitive state partagé entre agents.

    Règles fondamentales :
    - Le Kernel crée le contexte
    - Les agents MUTENT uniquement ce contexte
    - Aucun agent ne remplace ctx
    - result est produit UNE seule fois
    """

    # ----- INPUT -----
    message: str
    intent: Optional[Intent]
    memories: dict
    session_memory: dict

    # ----- RUNTIME -----
    extra: Dict[str, Any] = field(default_factory=dict)

    # ----- OUTPUT -----
    result: Optional[str] = None

    # ----- INTERNAL STATE -----
    halted: bool = False

    # =====================================================
    # SAFE HELPERS
    # =====================================================

    def set_result(self, value: str):
        """
        Définit le résultat final.
        Empêche overwrite silencieux.
        """
        if self.result is not None:
            raise RuntimeError("Result already set by another agent")

        self.result = value
        self.halted = True

    def stop(self):
        """Permet à un agent d'arrêter la pipeline."""
        self.halted = True


# =========================================================
# BASE AGENT
# =========================================================

class BaseAgent(ABC):

    name: str = "base"

    @abstractmethod
    def run(self, ctx: AgentContext, llm_router) -> AgentContext:
        """
        Chaque agent :
        - lit ctx
        - modifie ctx
        - retourne ctx
        """
        ...