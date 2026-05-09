# scripts/embedder_bench/_models.py
#
# Chargement uniforme des 6 modèles d'embedding du benchmark T-Embedder1.
# Gère :
#   - sentence-transformers natif (M0, M1, M2, M4)
#   - e5 avec préfixes obligatoires query/passage (M3)
#   - ONNX runtime via optimum (M5)
#
# Utilisé par benchmark_quality.py, pairwise_distribution.py et benchmark_perf.py.
#
# Dépendances pip :
#   sentence-transformers, transformers, torch, numpy
#   optimum, onnxruntime  (pour M5 uniquement)

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import torch


@dataclass
class ModelSpec:
    tag: str
    hf_id: str
    label: str
    expected_dim: int
    family: str  # "st" ou "onnx-mpnet"
    query_prefix: str = ""
    passage_prefix: str = ""
    notes: str = ""


REGISTRY: list[ModelSpec] = [
    ModelSpec(
        tag="M0",
        hf_id="sentence-transformers/all-MiniLM-L6-v2",
        label="all-MiniLM-L6-v2 (baseline ARIA, anglocentré)",
        expected_dim=384,
        family="st",
    ),
    ModelSpec(
        tag="M1",
        hf_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        label="paraphrase-multilingual-MiniLM-L12-v2 (multilingue léger)",
        expected_dim=384,
        family="st",
    ),
    ModelSpec(
        tag="M2",
        hf_id="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        label="paraphrase-multilingual-mpnet-base-v2 (multilingue robuste)",
        expected_dim=768,
        family="st",
    ),
    ModelSpec(
        tag="M3",
        hf_id="intfloat/multilingual-e5-base",
        label="multilingual-e5-base (préfixes query/passage)",
        expected_dim=768,
        family="st",
        query_prefix="query: ",
        passage_prefix="passage: ",
        notes=(
            "Modèle e5 — préfixes obligatoires sinon scores -0.10 à -0.15. "
            "query: sur le message utilisateur, passage: sur les noms d'intents."
        ),
    ),
    ModelSpec(
        tag="M4",
        hf_id="BAAI/bge-m3",
        label="bge-m3 (multilingue dense uniquement)",
        expected_dim=1024,
        family="st",
        notes="Dense uniquement (pas de sparse / colbert) pour comparabilité.",
    ),
    ModelSpec(
        tag="M5",
        hf_id="yilunzhang/all-mpnet-base-v2-onnx",
        label="all-mpnet-base-v2-onnx (choix session externe, anglocentré)",
        expected_dim=768,
        family="onnx-mpnet",
        notes="Export ONNX du all-mpnet-base-v2 anglais. Mean pooling + L2 manuel.",
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Encoder uniforme
# ──────────────────────────────────────────────────────────────────────────────

class UnifiedEncoder:
    """
    Wrapper qui expose `encode_queries(texts)` et `encode_passages(texts)` quelle
    que soit la famille du modèle. Vecteurs L2-normalisés.
    """

    def __init__(self, spec: ModelSpec, batch_size: int = 32):
        self.spec = spec
        self.batch_size = batch_size
        self._load()

    def _load(self):
        t0 = time.perf_counter()
        if self.spec.family == "st":
            from sentence_transformers import SentenceTransformer
            device = "cpu"  # 18 vCPU, pas de GPU sur la VM
            self._st = SentenceTransformer(self.spec.hf_id, device=device)
            self._st.eval()
        elif self.spec.family == "onnx-mpnet":
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(self.spec.hf_id)
            self._ort = ORTModelForFeatureExtraction.from_pretrained(self.spec.hf_id)
        else:
            raise ValueError(f"unknown family: {self.spec.family}")
        self.load_time_s = time.perf_counter() - t0

    # ─── encodage interne ──────────────────────────────────────────────────

    def _encode_st(self, texts: list[str]) -> np.ndarray:
        vecs = self._st.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(vecs, dtype=np.float32)

    def _encode_onnx(self, texts: list[str]) -> np.ndarray:
        out_chunks = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            inputs = self._tok(
                chunk,
                padding=True, truncation=True, return_tensors="pt", max_length=512,
            )
            with torch.no_grad():
                out = self._ort(**inputs)
            mask = inputs["attention_mask"].unsqueeze(-1).expand(out.last_hidden_state.size()).float()
            summed = torch.sum(out.last_hidden_state * mask, 1)
            counts = torch.clamp(mask.sum(1), min=1e-9)
            pooled = summed / counts
            normed = torch.nn.functional.normalize(pooled, p=2, dim=1)
            out_chunks.append(normed.cpu().numpy().astype(np.float32))
        return np.concatenate(out_chunks, axis=0)

    def _encode_raw(self, texts: list[str]) -> np.ndarray:
        if self.spec.family == "st":
            return self._encode_st(texts)
        return self._encode_onnx(texts)

    # ─── API ───────────────────────────────────────────────────────────────

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        if self.spec.query_prefix:
            texts = [self.spec.query_prefix + t for t in texts]
        return self._encode_raw(texts)

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        if self.spec.passage_prefix:
            texts = [self.spec.passage_prefix + t for t in texts]
        return self._encode_raw(texts)


# ──────────────────────────────────────────────────────────────────────────────
# Aides utilitaires
# ──────────────────────────────────────────────────────────────────────────────

def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine sim entre deux ensembles de vecteurs L2-normalisés (a×b)."""
    return a @ b.T


def topk(scores: np.ndarray, labels: list[str], k: int = 5) -> list[tuple[float, str]]:
    """Tri décroissant ; renvoie (score, label) pour les top-k."""
    order = np.argsort(-scores)[:k]
    return [(float(scores[i]), labels[i]) for i in order]


def rank_of(label: str, scores: np.ndarray, labels: list[str]) -> int | None:
    """Rang 1-based du label (None si absent)."""
    if label not in labels:
        return None
    target_idx = labels.index(label)
    target_score = scores[target_idx]
    # Nombre d'éléments STRICTEMENT supérieurs → rang 1-based
    return int(np.sum(scores > target_score)) + 1


def find_model(tag: str) -> ModelSpec:
    for s in REGISTRY:
        if s.tag == tag:
            return s
    raise KeyError(tag)
