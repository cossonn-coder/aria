from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EmbeddingContract:
    """
    Contrat mathématique unique pour tous les embeddings ARIA.
    Garantit que Intent, MAIC, MemPalace comparent des vecteurs compatibles.
    """
    dim: int
    normalized: bool = True
    metric: str = "cosine"

    def validate(self, vec: np.ndarray):
        if len(vec) != self.dim:
            raise ValueError(
                f"Embedding dimension mismatch: got {len(vec)}, expected {self.dim}"
            )
