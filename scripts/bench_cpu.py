import time
import numpy as np
import torch
torch.set_num_threads(18)
from sentence_transformers import SentenceTransformer

# Modèles à tester
models = {
    "mpnet": "sentence-transformers/all-mpnet-base-v2",
    "bge-m3": "BAAI/bge-m3",
    "intfloat/multilingual-e5-small" : "intfloat/multilingual-e5-small",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
}

# Phrases multilingues (français, anglais, allemand)
sentences = [
    "Bonjour, comment allez-vous ?",
    "Artificial intelligence is transforming the world.",
    "Die Sonne scheint heute sehr hell.",
    "Le machine learning permet de créer des embeddings.",
    "This is a test sentence for performance benchmarking."
] * 20  # 100 phrases au total

for name, model_id in models.items():
    print(f"\n=== {name} ===")
    model = SentenceTransformer(model_id, device="cpu")
    
    # Warm-up
    _ = model.encode(sentences[:10])
    
    # Mesure sur 3 runs
    times = []
    for _ in range(3):
        start = time.time()
        embeddings = model.encode(sentences, batch_size=32, show_progress_bar=False)
        times.append(time.time() - start)
    
    avg_time = np.mean(times)
    print(f"Temps moyen pour {len(sentences)} phrases : {avg_time:.2f} s")
    print(f"Phrases par seconde : {len(sentences)/avg_time:.1f}")
    print(f"Dimension des embeddings : {embeddings.shape[1]}")
