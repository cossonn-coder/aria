import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CompressionCluster:
    intents: list
    centroid: np.ndarray


class IntentCompressionEngine:
    """
    MAIC: Memory-Aware Intent Compression Engine

    - fusion d'intents sémantiquement proches
    - stabilisation du graphe d'intents
    - memory-aware weighting possible (MemPalace hooks)
    """

    def __init__(self, embedder, similarity_threshold: float = 0.78):
        self.embedder = embedder
        self.threshold = similarity_threshold

    # =========================================================
    # PUBLIC API
    # =========================================================

    def compress(self, intents: List):
        """
        Retourne une liste d'intents compressés.
        Aucun effet de bord.
        """

        if len(intents) <= 1:
            return intents

        clusters: List[CompressionCluster] = []

        # =====================================================
        # 1. CLUSTERING
        # =====================================================
        for intent in intents:

            if not hasattr(intent, "embedding") or intent.embedding is None:
                continue

            placed = False

            for cluster in clusters:
                sim = self._cosine(intent.embedding, cluster.centroid)

                if sim >= self.threshold:
                    cluster.intents.append(intent)
                    cluster.centroid = self._update_centroid(cluster)
                    placed = True
                    break

            if not placed:
                clusters.append(
                    CompressionCluster(
                        intents=[intent],
                        centroid=np.array(intent.embedding, dtype=np.float32),
                    )
                )

        # =====================================================
        # 2. MERGE CLUSTERS
        # =====================================================
        compressed = []

        for cluster in clusters:

            if len(cluster.intents) == 1:
                compressed.append(cluster.intents[0])
                continue

            merged = self._merge_intents(cluster.intents)
            compressed.append(merged)

        return compressed

    # =========================================================
    # MERGE LOGIC
    # =========================================================

    def _merge_intents(self, intents: List):
        """
        Fusion déterministe + stable.
        """

        base = intents[0]

        merged = type(base)(name=self._merge_names(intents))

        # embedding centroid weighted
        embeddings = [np.array(i.embedding, dtype=np.float32) for i in intents]
        merged.embedding = self._centroid(embeddings)

        # fusion actions
        merged.actions = []
        for i in intents:
            if hasattr(i, "actions"):
                merged.actions.extend(i.actions)

        # provenance tracking (CRITIQUE pour debug futur)
        merged.merged_from = [i.id for i in intents]

        return merged

    # =========================================================
    # STABILITY FUNCTIONS
    # =========================================================

    def _merge_names(self, intents):
        names = [i.name for i in intents if hasattr(i, "name")]
        return " + ".join(names[:3])[:80]

    def _centroid(self, vectors):
        if not vectors:
            return None
        return np.mean(vectors, axis=0)

    def _update_centroid(self, cluster):
        vectors = [np.array(i.embedding) for i in cluster.intents]
        return np.mean(vectors, axis=0)

    def _cosine(self, a, b):
        a = np.array(a, dtype=np.float32)
        b = np.array(b, dtype=np.float32)

        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0

        return float(np.dot(a, b) / denom)