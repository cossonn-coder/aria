from transformers import AutoTokenizer
# 1. Importer la classe ONNX
from optimum.onnxruntime import ORTModelForFeatureExtraction
import torch
import torch.nn.functional as F
import time

# --- Copie de la fonction de pooling (inchangée) ---
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
# --------------------------------------------------

# 2. Charger le tokenizer et le modèle ONNX depuis le Hub
model_id = "yilunzhang/all-mpnet-base-v2-onnx"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = ORTModelForFeatureExtraction.from_pretrained(model_id) # <-- Chargement ONNX

sentences = [
    "Bonjour, comment allez-vous ?",
    "Artificial intelligence is transforming the world.",
    "Die Sonne scheint heute sehr hell."
] * 34  # Environ 100 phrases

# --- Benchmarks (le code reste identique !) ---
# Warm-up
_ = model(**tokenizer(sentences[:10], padding=True, truncation=True, return_tensors='pt'))

# Mesure
start = time.time()
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
with torch.no_grad():
    model_output = model(**encoded_input)
sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
end = time.time()

print(f"Temps de calcul ONNX: {end-start:.2f} secondes pour {len(sentences)} phrases")
print(f"Phrases par seconde: {len(sentences)/(end-start):.1f}")
print(f"Dimension des embeddings: {sentence_embeddings.shape[1]}")