from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class MemoryContext:
    """
    Normalisation de toutes les mémoires disponibles pour un cycle cognitif.
    """

    global_memories: Dict[str, Any]
    session_memories: Dict[str, Any]

    # optionnel mais utile pour debug / audit
    meta: Dict[str, Any] = None