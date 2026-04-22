# aria/intent/intent_recall_engine.py

import numpy as np
from dataclasses import dataclass

from memory.mempalace_bridge import retrieve_memories


@dataclass
class RecallDecision:
    action: str  # "attach" | "create" | "split"
    primary_intent_id: str | None = None
    score: float = 0.0


class IntentRecallEngine:

    def __init__(self, embedder, threshold: float = 0.45):
        self.embedder = embedder
        self.threshold = threshold

    def resolve(self, message: str, intents: list, memory_context=None):

        # =========================
        # 1. EMBEDDING MESSAGE (FIX CLEAN)
        # =========================
        msg_emb = self.embedder.encode([message])[0]

        # =========================
        # 2. MEMORY CONTEXT BOOST (OPTIONAL GLOBAL SIGNAL)
        # =========================
        mem_score_map = {}

        if memory_context and memory_context.get("hits"):
            for h in memory_context["hits"]:
                intent_id = h.get("metadata", {}).get("intent")
                if intent_id:
                    mem_score_map[intent_id] = mem_score_map.get(intent_id, 0.0) + 1.0

        # normalize memory scores
        if mem_score_map:
            max_mem = max(mem_score_map.values())
            for k in mem_score_map:
                mem_score_map[k] /= max_mem

        # =========================
        # 3. FILTER ACTIVE INTENTS
        # =========================
        intents = [i for i in intents if i.status == "active"]

        if not intents:
            return RecallDecision(action="create"), []

        scored = []

        # =========================
        # 4. SCORING CORE LOOP
        # =========================
        for intent in intents:
            emb = getattr(intent, "embedding", None)
            if emb is None:
                continue

            cosine = self._cosine(msg_emb, intent.embedding)

            # -----------------------------------
            # 🔥 MEMPALACE CO-OCCURRENCE SIGNAL
            # -----------------------------------
            mem_score = mem_score_map.get(intent.id, 0.0)

            final_score = (0.8 * cosine) + (0.2 * mem_score)

            scored.append((intent, final_score))

        if not scored:
            return RecallDecision(action="create"), []

        # =========================
        # 5. BEST MATCH
        # =========================
        scored.sort(key=lambda x: x[1], reverse=True)
        best_intent, best_score = scored[0]

        print("\n[RECALL]")
        print(f"message={message}")
        print(f"best_intent={best_intent.id}")
        print(f"best_score={best_score:.3f}")

        # =========================
        # 6. DECISION LOGIC
        # =========================
        CREATE_FLOOR = 0.30  # en dessous → on attache au meilleur quand même

        if best_score > self.threshold:
            return RecallDecision(
                action="attach",
                primary_intent_id=best_intent.id,
                score=best_score,
            ), scored

        close = [s for s in scored if s[1] > self.threshold - 0.05]
        if len(close) >= 2:
            return RecallDecision(action="split"), scored

        # score trop faible pour créer → attache au meilleur intent existant
        if best_score > CREATE_FLOOR and len(scored) > 0:
            return RecallDecision(
                action="attach",
                primary_intent_id=best_intent.id,
                score=best_score,
            ), scored

        return RecallDecision(action="create"), scored

    # =========================
    # SIMILARITY
    # =========================
    def _cosine(self, a, b):
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))