#scripts/test_onnx_embedder.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding.embedder import Embedder
from config import config

emb = Embedder(config.EMBEDDING_MODEL)
vec = emb.encode(["Bonjour ARIA, test de vitesse."])
print(vec.shape)