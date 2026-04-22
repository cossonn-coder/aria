#aria/intent/intent.py
from enum import Enum
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone
import math


# =====================================================
# BUSINESS LIFECYCLE
# =====================================================

class IntentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class IntentPhase(str, Enum):
    CREATION = "creation"
    PLANNING = "planning"
    EXECUTION = "execution"


# =====================================================
# COGNITIVE STATE (NEW)
# =====================================================

class IntentAttentionState(str, Enum):
    ACTIVE = "active"
    BACKGROUND = "background"
    PAUSED = "paused"
    ARCHIVED = "archived"


# =====================================================
# INTENT
# =====================================================

@dataclass
class Intent:

    # -----------------------------
    # Identity
    # -----------------------------
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""

    # -----------------------------
    # Business lifecycle
    # -----------------------------
    status: IntentStatus = IntentStatus.ACTIVE

    next_action: Optional[str] = None
    actions_history: list[str] = field(default_factory=list)

    # -----------------------------
    # Cognitive layer (NEW)
    # -----------------------------
    salience: float = 1.0
    activation_count: int = 0

    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activated: datetime = field(default_factory=datetime.utcnow)

    attention_state: IntentAttentionState = IntentAttentionState.ACTIVE

    # =====================================================
    # READ-ONLY DERIVED STATE
    # =====================================================

    @property

    def actions(self):
        '''
        Historique complet des actions, incluant la prochaine action planifiée.
        '''
        return self.actions_history

    def subject(self) -> str:
        return self.name

    # -----------------------------
    # Workflow phase inference
    # -----------------------------
    def infer_phase(self) -> str:

        if not self.actions_history:
            return IntentPhase.CREATION.value

        if self.next_action:
            return IntentPhase.EXECUTION.value

        return IntentPhase.PLANNING.value

    # -----------------------------
    # LLM context builder
    # -----------------------------
    def build_llm_context(
        self,
        memory_results: list[dict],
        phase: str,
    ) -> dict:

        return {
            "intent_name": self.name,
            "intent_description": self.description,
            "intent_status": self.status.value,
            "attention_state": self.attention_state.value,
            "salience": round(self.salience, 3),
            "next_action": self.next_action,
            "actions_history": self.actions_history,
            "phase": phase,
            "memory_results": memory_results,
        }

    # =====================================================
    # COGNITIVE OPERATIONS (NEW)
    # =====================================================

    def activate(self):
        """
        Activation cognitive.
        Equivalent d'un focus attentionnel.
        """

        self.salience += 1.0
        self.activation_count += 1
        self.last_activated = datetime.now(timezone.utc)

        self._update_attention_state()

    def decay(self, now: datetime, decay_lambda: float = 0.15):
        """
        Oubli exponentiel.
        """

        delta_days = (
            now - self.last_activated
        ).total_seconds() / 86400

        self.salience *= math.exp(-decay_lambda * delta_days)

        self._update_attention_state()

    def _update_attention_state(self):

        s = self.salience

        if s > 2.5:
            self.attention_state = IntentAttentionState.ACTIVE
        elif s > 0.5:
            self.attention_state = IntentAttentionState.BACKGROUND
        elif s > 0.1:
            self.attention_state = IntentAttentionState.PAUSED
        else:
            self.attention_state = IntentAttentionState.ARCHIVED

    # =====================================================
    # MUTATIONS CONTROLLED (EXISTING)
    # =====================================================

    def set_next_action(self, action: str):
        self.next_action = action

    def add_action(self, action: str):
        self.actions_history.append(action)

    def complete(self):
        self.status = IntentStatus.COMPLETED

    def abandon(self):
        self.status = IntentStatus.ABANDONED