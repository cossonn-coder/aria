# embedding/embedder.py

from embedding.embedding_contract import EmbeddingContract
from sentence_transformers import SentenceTransformer
import torch
import numpy as np



class Embedder:

    def __init__(self, model_name: str):
        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(
            model_name,
            device=device
        )

        # warmup + dimension detection
        sample = self.model.encode(
            ["test"],
            normalize_embeddings=True,
            show_progress_bar=False
        )[0]

        self.contract = EmbeddingContract(dim=len(sample))

    # =========================================================
    # CORE API
    # =========================================================

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.array([])

        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        vecs = np.array(vecs)

        # validation contract
        for v in vecs:
            self.contract.validate(v)

        return vecs