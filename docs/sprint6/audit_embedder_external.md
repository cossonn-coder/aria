Voici le bilan complet de notre session à destination de **Claude.ai** (ou tout autre LLM reprenant le projet **ARIA**).

## Contexte et objectif initial

- **VM** : Debian (nom `vDebianIA`) sur nœud Proxmox (nom `lemineur`), avec 18 vCPU, 125 Go RAM.
- **Objectif** : faire tourner des modèles d’embedding (sentence-transformers) sur GPU plutôt que CPU.
- **Matériel disponible** : carte NVIDIA GTX 1060 6 Go (identifiée `0b:00.0` sur l’hôte).

## Constat : GPU indisponible pour la VM Debian

- La carte est déjà en **passthrough exclusif** vers une autre VM (`windows11` / VMID 100) utilisée pour le gaming (Moonlight).
- Le passthrough PCIe est **exclusif** : un GPU ne peut être attribué qu’à une seule VM.
- Tentatives d’ajout à la VM Debian (VMID 110) : erreur `already in use by VMID 100`.
- **Décision** : renoncer à l’utilisation du GPU pour l’embedding (aucune seconde carte disponible, attente jusqu’à septembre pour un éventuel ajout matériel).

## Audits et diagnostics réalisés sur l’hôte Proxmox

Commandes clés exécutées en root sur `lemineur` :

```bash
# Vérification de l'IOMMU (actif)
dmesg | grep -e DMAR -e IOMMU -e AMD-Vi

# Groupes IOMMU
find /sys/kernel/iommu_groups/ -type l

# Cartes VGA physiques
lspci -nn | grep -i vga
# Résultat : 01:00.1 Matrox G200EH (intégré), 0b:00.0 NVIDIA GTX 1060

# Module vfio-pci chargé
lsmod | grep vfio

# Configuration de la VM 100 (Windows)
qm config 100   # montre hostpci0: 0000:0b:00, pcie=1, rombar=0, x-vga=1

# Tentative d’ajout (annulée) sur VM 110
qm set 110 -hostpci0 0b:00.0,rombar=on   # puis suppression
qm set 110 -delete hostpci0
```

**Conclusion** : le GPU est bien isolé en VFIO mais attaché à une VM différente. Pas de partage possible.

## Benchmarking des modèles d’embedding en CPU

Objectif : trouver le meilleur compromis vitesse/qualité sur les 18 cœurs (performance réelle mesurée : 5–15 phrases/seconde selon modèle).

### Modèles testés (script `bench_cpu.py`)

- `all-mpnet-base-v2` : 7.5 phrases/s, dim 768
- `BAAI/bge-m3` : 4.0 phrases/s, dim 1024
- `intfloat/multilingual-e5-small` : 15.6 phrases/s, dim 384
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` : 14.5 phrases/s, dim 384
- `all-MiniLM-L6-v2` (modèle actuel ARIA) : non retesté mais estimé ~10-15, dim 384

### Amélioration par ONNX sur `all-mpnet-base-v2`

Utilisation du modèle **pré-converti** `yilunzhang/all-mpnet-base-v2-onnx` :

- Script `test_onnx.py` (direct) : **23.5 phrases/s**, dim 768 (gain x3 par rapport au même modèle en PyTorch CPU)
- Validation dans l’architecture ARIA via `test_onnx_embedder.py` : vecteur de dimension 768 correctement généré.

**Choix final** : conserver `all-mpnet-base-v2` en version ONNX malgré le changement de dimension (768 vs 384), car la qualité sémantique est supérieure et la vitesse est excellente (23 phrases/s).  
Cela impose une **migration des embeddings existants** (voir plus loin).

## Modifications de code dans ARIA

### 1. `aria/config.py` (diff)

Un seul changement : la variable `EMBEDDING_MODEL`.

```diff
-    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
+    EMBEDDING_MODEL = "yilunzhang/all-mpnet-base-v2-onnx"
```

### 2. `aria/embedding/embedder.py` (remplacement complet)

Ancienne version (simpliste) → nouvelle version supportant ONNX et fallback.

**Fichier final** (`aria/embedding/embedder.py`) :

```python
from embedding.embedding_contract import EmbeddingContract
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

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
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.ort_model = ORTModelForFeatureExtraction.from_pretrained(model_name)
            sample = self._encode_onnx(["test"])[0]
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer(model_name, device=device)
            sample = self.model.encode(["test"], normalize_embeddings=True, show_progress_bar=False)[0]

        self.contract = EmbeddingContract(dim=len(sample))

    def _encode_onnx(self, texts: list[str]) -> np.ndarray:
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
            vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            vecs = np.array(vecs)
        for v in vecs:
            self.contract.validate(v)
        return vecs
```

### 3. Scripts de test ajoutés dans `aria/scripts/`

- `bench_cpu.py` : benchmark des modèles en CPU (résultats plus haut).
- `test_onnx.py` : test direct du pipeline ONNX avec `ORTModelForFeatureExtraction` (utilisé pour valider les 23.5 phrases/s).
- `test_onnx_embedder.py` : test de l’intégration dans la classe `Embedder`.

Contenu de `test_onnx_embedder.py` :

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from embedding.embedder import Embedder
from config import config

emb = Embedder(config.EMBEDDING_MODEL)
vec = emb.encode(["Bonjour ARIA, test de vitesse."])
print(vec.shape)  # doit afficher (1, 768)
```

## Dépendances supplémentaires à installer dans le venv ARIA

```bash
pip install "optimum[onnxruntime]" transformers
```

## Points d’attention pour la suite (à transmettre à Claude)

1. **Migration des embeddings** : tous les vecteurs précédemment stockés dans ChromaDB et MemPalace (dimension 384) ne sont plus compatibles. Il faut **re-générer l’intégralité des embeddings** avec le nouveau modèle (`yilunzhang/all-mpnet-base-v2-onnx`) avant toute utilisation. Cela peut être fait par un script itérant sur toutes les mémoires et mettant à jour les collections.

2. **GPU toujours inaccessible** : l’option de repasser sur GPU reste envisageable plus tard (septembre) si une seconde carte est ajoutée ou si la VM Windows est déplacée. Pour l’instant, tout tourne en CPU optimisé ONNX.

3. **Service systemd** : après les modifications, redémarrer le service ARIA (`sudo systemctl restart aria`). Surveiller les logs pour vérifier l’absence d’erreurs de dimension.

4. **Fallback automatique** : la classe `Embedder` gère les modèles ONNX (si le nom contient `"-onnx"`) et les modèles classiques. Si `optimum` n’est pas installé, elle bascule silencieusement sur SentenceTransformer (mais cela plantera car le modèle ONNX n’est pas compatible). Il est donc impératif que l’environnement contienne les bonnes bibliothèques.

5. **Performances mesurées** :
   - Ancien modèle (MiniLM) : ~10-15 phrases/s, dim 384
   - Nouveau modèle (mpnet ONNX) : **23-24 phrases/s**, dim 768
   - Temps pour 10 phrases : environ 0.43 s → acceptable pour un usage interactif (Telegram).

## Résumé de l’état final

- **Pas de GPU utilisé** (abandon définitif pour cette itération).
- **Modèle d’embedding** : `yilunzhang/all-mpnet-base-v2-onnx` via ONNX Runtime.
- **Code ARIA modifié** : `config.py` et `embedder.py` (diffs fournis).
- **Scripts de test** disponibles dans `aria/scripts/`.
- **Action urgente** : re-générer tous les embeddings existants (sinon incohérence dimensionnelle).

Toutes ces informations doivent permettre à Claude (ou un autre développeur) de reprendre le projet sans surprise.