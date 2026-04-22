from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


# ==========================
# ACTIONS POSSIBLES DU RECALL
# ==========================

class IntentActionType(str, Enum):
    CREATE = "create"
    ATTACH = "attach"
    SPLIT = "split"
    IGNORE = "ignore"


# ==========================
# INTENT SCORED MATCH
# ==========================

@dataclass
class ScoredIntent:
    intent_id: str
    score: float


# ==========================
# DECISION PRODUITE PAR LE RECALL ENGINE
# ==========================

@dataclass
class IntentRecallDecision:
    action: IntentActionType
    primary_intent_id: Optional[str] = None
    confidence: float = 0.0


# ==========================
# SORTIE COMPLET DU RECALL
# ==========================

@dataclass
class RecallResult:
    decision: IntentRecallDecision
    matches: List[ScoredIntent]