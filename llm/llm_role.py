# aria/llm/llm_role.py

from enum import Enum


class LLMRole(str, Enum):
    """
    Rôles standardisés pour le routing LLM.

    Utilisé uniquement pour orienter le type de traitement demandé
    par un agent vers le LLMRouter.
    """

    CHAT = "chat"
    REASONING = "reasoning"
    PLANNING = "planning"
    REFLECTION = "reflection"