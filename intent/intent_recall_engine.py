# aria/intent/intent_recall_engine.py

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


# =========================================================
# DECISION CONTRACT (UNIQUE SOURCE OF TRUTH)
# =========================================================

@dataclass
class RecallDecision:
    """
    Décision de routage d'intent.

    action:
        - "attach" → rattacher à un intent existant
        - "create" → créer un nouvel intent
        - "split"  → divergence de contexte
    """
    action: str  # "attach" | "create" | "split"
    primary_intent_id: Optional[str] = None
    score: float = 0.0


class IntentRecallEngine:
    """
    Moteur de rappel d'intents basé sur la similarité embedding (scoring cosine pur).
    """
    # Note F1 (sprint 3.1, 1er mai 2026) :
    # Le boost mem_score (+0.2 × hits_normalized) a été retiré.
    # Cause : il favorisait les rooms à fort volume mémoire,
    # indépendamment de la pertinence sémantique, créant des
    # mismatches en cascade (cf. log run live 1er mai : choux
    # rouges → construire une maison).
    # Si un signal mémoire devient utile, le réintroduire en F2
    # (pondéré par le score de similarité du hit, pas par le
    # nombre de hits).

    def __init__(self, embedder, threshold: float = 0.45):
        self.embedder = embedder
        self.threshold = threshold

    # =========================================================
    # MAIN ENTRY
    # =========================================================

    def resolve(
        self,
        message: str,
        intents: List,
        memory_context: Optional[dict] = None,  # conservé pour compat call-site, ignoré
        # depuis F1 (sprint 3.1). À retirer si on confirme que le
        # boost ne sera jamais réintroduit.
    ) -> Tuple[RecallDecision, List[Tuple]]:
        """
        Scoring purement sémantique (cosine). Pas de signal mémoire.

        Retourne :
            - RecallDecision
            - scored intents [(intent, score), ...]
        """

        # =====================================================
        # 1. EMBEDDING MESSAGE
        # =====================================================
        msg_emb = self.embedder.encode([message])[0]

        # =====================================================
        # 2. FILTER ACTIVE INTENTS
        # =====================================================
        active_intents = [i for i in intents if i.status == "active"]

        if not active_intents:
            return RecallDecision(action="create"), []

        # =====================================================
        # 3. SCORING
        # =====================================================
        scored: List[Tuple] = []

        for intent in active_intents:
            if not hasattr(intent, "embedding") or intent.embedding is None:
                continue

            cosine = self._cosine(msg_emb, intent.embedding)
            final_score = cosine

            scored.append((intent, final_score))

        if not scored:
            return RecallDecision(action="create"), []

        # =====================================================
        # 4. BEST MATCH
        # =====================================================
        scored.sort(key=lambda x: x[1], reverse=True)
        best_intent, best_score = scored[0]

        # =====================================================
        # 5. DECISION LOGIC (STABLE TRIANGLE)
        # =====================================================

        # CASE 1 — strong match → attach
        if best_score >= self.threshold:
            return RecallDecision(
                action="attach",
                primary_intent_id=best_intent.id,
                score=best_score,
            ), scored

        # CASE 2 — ambiguity → split
        close = [s for s in scored if s[1] > self.threshold - 0.05]
        if len(close) >= 2:
            return RecallDecision(
                action="split",
                score=best_score,
            ), scored

        # CASE 3 — weak signal → create
        return RecallDecision(
            action="create",
            score=best_score,
        ), scored

    # =========================================================
    # SIMILARITY
    # =========================================================

    def _cosine(self, a, b) -> float:
        a = np.array(a, dtype=np.float32)
        b = np.array(b, dtype=np.float32)

        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0

        return float(np.dot(a, b) / denom)