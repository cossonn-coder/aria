#aria/intent/intent_engine.py

import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from intent.intent import Intent
from intent.intent_decision import (
    IntentActionType,
    ScoredIntent,
)
from intent.intent_recall_engine import IntentRecallEngine
from intent.intent_compression_engine import IntentCompressionEngine
from intent.intent_store import save_intents, load_intents

class IntentEngine:
    """
    Responsable unique :
    - cycle de vie des intents
    - application stricte des décisions
    """

    def __init__(self, embedder):
        self.embedder = embedder
        self.intents: dict[str, Intent] = load_intents(embedder)  # ← charge depuis disque
        self.compressor = IntentCompressionEngine(embedder)
        self._compression_counter = 0
        self.recall_engine = IntentRecallEngine(embedder)
        self._last_decay = datetime.now(timezone.utc)
        self._decay_interval = timedelta(minutes=5)

    # =========================================================
    # STATE
    # =========================================================

    def get(self, intent_id: str) -> Optional[Intent]:
        return self.intents.get(intent_id)

    def list_active(self) -> List[Intent]:
        return [
            i for i in self.intents.values()
            if i.status == "active"
        ]
    
    def list_attention_active(self) -> List[Intent]:
        """
        Intents présents dans le champ attentionnel.
        Utilisé uniquement par le recall cognitif.
        """

        return [
            i for i in self.intents.values()
            if i.status == "active"
            and getattr(i, "attention_state", "active") in ("active", "background")
        ]

    # =========================================================
    # CREATION
    # =========================================================

    def _create(self, name: str) -> Intent:
        intent = Intent(name=name)
        intent.embedding = self.embedder.encode([intent.name])[0]
        self.intents[intent.id] = intent
        return intent

    # =========================================================
    # RECALL
    # =========================================================

    def resolve(self, message: str, intents: list, memory_context=None):
        return self.recall_engine.resolve(
            message,
            intents,
            memory_context=memory_context,
        )
    
    # =========================================================
    # FIND BY NAME (STRICT MATCH, ACTIVE ONLY)
    # =========================================================
    def _find_by_name(self, name: str):
        for intent in self.intents.values():
            if intent.name.lower() == name.lower() and intent.status == "active":
                return intent
        return None

    # =========================================================
    # FIND BY NAME (SEMANTIC MATCH, ACTIVE ONLY)
    # =========================================================
    def _find_by_name_semantic(self, name: str, threshold: float = 0.55) -> Optional[Intent]:
        """
        Autorité finale pour les décisions CREATE : si un intent existant est
        sémantiquement proche du nom canonique extrait, on attache plutôt que
        de créer un doublon — même si le recall message-based n'a pas franchi
        le seuil (signal différent, moins stable pour les noms courts).
        """
        if not name:
            return None
        name_emb = np.array(self.embedder.encode([name])[0], dtype=np.float32)
        best_intent = None
        best_score = threshold
        for intent in self.intents.values():
            if intent.status != "active":
                continue
            if not hasattr(intent, "embedding") or intent.embedding is None:
                continue
            b = np.array(intent.embedding, dtype=np.float32)
            denom = np.linalg.norm(name_emb) * np.linalg.norm(b)
            if denom == 0:
                continue
            score = float(np.dot(name_emb, b) / denom)
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent
    
    # =========================================================
    # APPLY (STRICT MUTATION ZONE)
    # =========================================================

    def apply(
            self,
            decision,
            message: str,
            intent_name: str | None = None,
            ) -> Intent:

        name = intent_name or message[:60]  # ← utilise le nom canonique si fourni

        # -------------------------
        # CREATE
        # -------------------------
        if decision.action == IntentActionType.CREATE:
            # Déduplication par nom canonique — autorité finale pour CREATE.
            # Le recall message-based peut manquer un intent proche (seuil +
            # bruit embedding) ; la similarité nom-à-nom offre un signal plus
            # stable. Exact match d'abord, sémantique ensuite.
            if intent_name:
                existing = self._find_by_name(intent_name)
                if existing:
                    existing.add_action(message)
                    self.compression_cycle_if_needed()
                    return existing
                existing = self._find_by_name_semantic(intent_name)
                if existing:
                    existing.add_action(message)
                    self.compression_cycle_if_needed()
                    return existing

            intent = self._create(name=name)
            intent.add_action(f"created_from_message:{message[:100]}")
            self.compression_cycle_if_needed()
            return intent

        # -------------------------
        # ATTACH
        # -------------------------
        if decision.action == IntentActionType.ATTACH:

            intent = self.get(decision.primary_intent_id)

            if intent is None:
                # fallback explicite (pas implicite)
                intent = self._create(
                    name=name
                )

            intent.add_action(message)
            self.compression_cycle_if_needed() 
            return intent

        # -------------------------
        # SPLIT
        # -------------------------
        if decision.action == IntentActionType.SPLIT:

            intent = self._create(
                name=name
            )

            intent.add_action(f"split_from_context:{message[:100]}")
            self.compression_cycle_if_needed() 
            return intent

        # -------------------------
        # FAIL-FAST (IMPORTANT CHANGE)
        # -------------------------
        raise ValueError(f"Unknown intent action: {decision.action}")

    # =========================================================
    # COMPRESSION
    # =========================================================
    def compression_cycle_if_needed(self):
        """
        Compression légère périodique.
        Non bloquante.
        """

        self._compression_counter += 1

        # fréquence simple (ajustable)
        if self._compression_counter < 20:
            return

        self._compression_counter = 0

        intents = self.list_active()

        if len(intents) < 10:
            return

        compressed = self.compressor.compress(intents)

        # overwrite pool
        for i in compressed:
            self.intents[i.id] = i

    # =========================================================
    # PERSISTENCE
    # =========================================================

    def save(self, intent: Intent):
        self.intents[intent.id] = intent
        save_intents(self.intents)  # ← persiste sur disque

    # =========================================================
    # DECAY
    # =========================================================
    def decay_if_needed(self):
        """
        Applique le decay uniquement si assez de temps réel s'est écoulé.
        """

        now = datetime.now(timezone.utc)

        if now - self._last_decay < self._decay_interval:
            return

        self._last_decay = now

        for intent in self.intents.values():
            intent.decay(now)