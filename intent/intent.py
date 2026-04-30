# aria/intent/intent.py
#
# Problème corrigé :
#   created_at et last_activated utilisaient datetime.utcnow() — datetime naïf
#   (sans timezone). La méthode decay() reçoit datetime.now(timezone.utc) —
#   datetime aware. La soustraction `now - self.last_activated` levait :
#     TypeError: can't subtract offset-naive and offset-aware datetimes
#   Ce crash se produisait dans decay_if_needed() et cassait tout le pipeline
#   cognitif après quelques messages, jusqu'au redémarrage du service.
#
#   Fix : toutes les dates sont créées avec datetime.now(timezone.utc).
#   datetime.utcnow() est déprécié depuis Python 3.12 — on ne l'utilise plus.

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
    ACTIVE    = "active"
    COMPLETED = "completed"
    PAUSED    = "paused"
    ABANDONED = "abandoned"


class IntentPhase(str, Enum):
    CREATION  = "creation"
    PLANNING  = "planning"
    EXECUTION = "execution"


# =====================================================
# COGNITIVE STATE
# =====================================================

class IntentAttentionState(str, Enum):
    ACTIVE     = "active"
    BACKGROUND = "background"
    PAUSED     = "paused"
    ARCHIVED   = "archived"


# =====================================================
# INTENT
# =====================================================

def _now_utc() -> datetime:
    """
    Retourne l'heure courante en UTC avec timezone.

    Utilisé comme default_factory pour les champs datetime.
    Remplace datetime.utcnow() qui produit des datetimes naïfs
    incompatibles avec les comparaisons timezone-aware.
    """
    return datetime.now(timezone.utc)


@dataclass
class Intent:

    # -----------------------------
    # Identity
    # -----------------------------
    id:          str = field(default_factory=lambda: str(uuid4()))
    name:        str = ""
    description: str = ""

    # -----------------------------
    # Business lifecycle
    # -----------------------------
    status: IntentStatus = IntentStatus.ACTIVE

    next_action:     Optional[str] = None
    actions_history: list[str]     = field(default_factory=list)

    # -----------------------------
    # Cognitive layer
    # -----------------------------
    salience:         float = 1.0
    activation_count: int   = 0

    # datetime.now(timezone.utc) — jamais datetime.utcnow() (naïf)
    created_at:     datetime = field(default_factory=_now_utc)
    last_activated: datetime = field(default_factory=_now_utc)

    attention_state: IntentAttentionState = IntentAttentionState.ACTIVE

    # =====================================================
    # READ-ONLY DERIVED STATE
    # =====================================================

    @property
    def actions(self):
        """Historique complet des actions, incluant la prochaine action planifiée."""
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
            "intent_name":        self.name,
            "intent_description": self.description,
            "intent_status":      self.status.value,
            "attention_state":    self.attention_state.value,
            "salience":           round(self.salience, 3),
            "next_action":        self.next_action,
            "actions_history":    self.actions_history,
            "phase":              phase,
            "memory_results":     memory_results,
        }

    # =====================================================
    # COGNITIVE OPERATIONS
    # =====================================================

    def activate(self):
        """
        Activation cognitive — équivalent d'un focus attentionnel.

        Incrémente la salience et met à jour last_activated avec un
        datetime timezone-aware pour rester compatible avec decay().
        """
        self.salience        += 1.0
        self.activation_count += 1
        self.last_activated   = datetime.now(timezone.utc)

        self._update_attention_state()

    def decay(self, now: datetime, decay_lambda: float = 0.15):
        """
        Oubli exponentiel basé sur le temps réel écoulé.

        Args:
            now          : datetime timezone-aware (datetime.now(timezone.utc))
            decay_lambda : constante de decay (défaut 0.15 par jour)

        Précondition :
            now et self.last_activated doivent être timezone-aware.
            Si last_activated était naïf (ancienne version), la soustraction
            lèverait TypeError — résolu par le fix _now_utc().
        """
        delta_days = (now - self.last_activated).total_seconds() / 86400
        self.salience *= math.exp(-decay_lambda * delta_days)
        self._update_attention_state()

    def _update_attention_state(self):
        """Met à jour l'état attentionnel en fonction de la salience courante."""
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
    # MUTATIONS CONTROLLED
    # =====================================================

    def set_next_action(self, action: str):
        self.next_action = action

    def add_action(self, action: str):
        self.actions_history.append(action)

    def complete(self):
        self.status = IntentStatus.COMPLETED

    def abandon(self):
        self.status = IntentStatus.ABANDONED