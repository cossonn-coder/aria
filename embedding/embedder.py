# embedding/embedder.py

from embedding.embedding_contract import EmbeddingContract
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

# Imports conditionnels pour ONNX (pas obligatoires si le modèle n'est pas ONNX)
try:
    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from transformers import AutoTokenizer
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

class Embedder:

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.is_onnx = "-onnx" in model_name.lower() and ONNX_AVAILABLE

        if self.is_onnx:
            # Mode ONNX
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.ort_model = ORTModelForFeatureExtraction.from_pretrained(model_name)
            # Vérification dimension avec un petit échantillon
            sample = self._encode_onnx(["test"])[0]
        else:
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

    def _encode_onnx(self, texts: list[str]) -> np.ndarray:
        """Inférence ONNX avec mean pooling et normalisation."""
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512
        )
        with torch.no_grad():
            outputs = self.ort_model(**inputs)
        # Mean pooling
        attention_mask = inputs['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        # Normalisation L2
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy()

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.array([])

        if self.is_onnx:
            vecs = self._encode_onnx(texts)
        else:
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