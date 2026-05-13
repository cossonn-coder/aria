# Audit Embedder — Inventaire (T-Embedder1, Tâches 1+2)

**Sprint 6 / sous-sprint embedder, tour 1.** Branche
`feat/sprint6-embedder-audit`. Aucune modification de prod : ce
document est un snapshot lecture seule de l'état actuel.

---

## 1. Localisation du travail externe (Tâche 1)

### 1.1 Branches

`archive/embedder-parallel-work` existe en local **et** sur `origin`.
Hash : `182e1c3` (parent `b1d78ab` = clôture sprint 5, antérieure aux
commits de doc/T-Z sprint 6 sur `main`).

Commande :
```
git log archive/embedder-parallel-work --oneline -1
182e1c3 archive: travail embedder hors-workflow
```

### 1.2 Diff réel `b1d78ab..archive/embedder-parallel-work`

| Fichier | Type | Insertions | Notes |
|---|---|---|---|
| `config.py` | M | 6 | `EMBEDDING_MODEL` → `yilunzhang/all-mpnet-base-v2-onnx` ; ajout `deepseek_api_key` (orthogonal, lié bin/) |
| `embedding/embedder.py` | M | +73 / −18 | Refactor : détection `-onnx` dans le nom de modèle, chargement via `optimum.onnxruntime.ORTModelForFeatureExtraction`, mean pooling + L2 norm manuels. Fallback `SentenceTransformer` conservé. |
| `embedding/embedding_contract.py` | M | +1 | Ligne d'en-tête commentée |
| `scripts/bench_cpu.py` | A | 41 | Bench perf CPU sur 4 modèles ST (mpnet, bge-m3, e5-**small**, multilingual-MiniLM-L12-v2) — 100 phrases multi-FR/EN/DE, batch 32, 3 runs |
| `scripts/test_onnx.py` | A | 41 | Smoke test ONNX direct sur `all-mpnet-base-v2-onnx` |
| `scripts/test_onnx_embedder.py` | A | 10 | Smoke test de la classe Embedder refactorée |

### 1.3 Constat

Le travail externe **mesure exclusivement la perf CPU** (phrases/s,
dim). Aucune mesure de qualité sémantique, aucun benchmark contre
les cas terrain du bug #18, aucune analyse pairwise.

Le choix `yilunzhang/all-mpnet-base-v2-onnx` est un export ONNX du
modèle `all-mpnet-base-v2` (Microsoft) — **anglocentré**, comme
le baseline `all-MiniLM-L6-v2` qu'il prétend remplacer. La racine
fonctionnelle du bug #18 (espace de représentation plat en français)
n'est donc **pas adressée**.

À noter : le bench externe contient bien des candidats multilingues
(`bge-m3`, `multilingual-MiniLM-L12-v2`) mais utilise `e5-small` au
lieu de `e5-base`, et n'inclut pas `paraphrase-multilingual-mpnet-base-v2`.

**Décision T-Embedder1** : ne pas merger ni cherry-pick. Le refactor
ONNX de `embedder.py` peut servir de base si un modèle ONNX est
retenu après benchmark qualité (T-Embedder2). Conservé tel quel sur
la branche archive.

---

## 2. Inventaire des collections vectorielles (Tâche 2)

Données mesurées par
[`scripts/embedder_bench/inventory_vector_stores.py`](../../scripts/embedder_bench/inventory_vector_stores.py)
(lecture seule, lance avec `./venv/bin/python`).

### 2.1 Tableau synthétique

| Store | Path | Collection | Wing | Count | Dim | Vecteurs persistés ? | Disk | Re-encode si migration ? |
|---|---|---|---|---|---|---|---|---|
| chroma_db_root | `aria/chroma_db/` | `aria_memories` | `<no_wing>` | 105 | 384 | ✅ | 720 KB | **Non** — store mort, voir §2.5 |
| mempalace | `~/.mempalace/palace/` | `mempalace_drawers` | `aria_episodic` | 443 | 384 | ✅ | 8.6 MB total | **Oui** |
| mempalace | `~/.mempalace/palace/` | `mempalace_drawers` | `aria_classifier` | 212 | 384 | ✅ | (idem) | **Oui** |
| mempalace | `~/.mempalace/palace/` | `mempalace_closets` | `aria` (legacy) | 32 | 384 | ✅ | (idem) | **Non** — legacy à arbitrer (cf. CLAUDE.md couches mémoire) |
| intents.json | `~/.aria/intents.json` | n/a | n/a | 63 | n/a | ❌ embeddings reconstruits au boot | 40 KB | **Non** — gratuit |

**Total à re-encoder pour migration d'embedder : 655 entrées
(443 episodic + 212 classifier).** Closets legacy 32 entrées et chroma_db_root
105 entrées peuvent être ignorées (zéro caller prod).

### 2.2 ChromaDB legacy `aria/chroma_db/`

```
collection : aria_memories
count      : 105
dim        : 384
wing       : <no_wing> (105/105) — pas de schéma wing/room/type
```

Configuré dans `config.py:88` (`config.chroma_path = BASE_DIR /
"chroma_db"`) mais **aucun caller prod** ne l'importe. Recherche :

```
$ grep -rn "chroma_db\|aria_memories\|chroma_path" --include="*.py" .
config.py:49     chroma_path: str = ""
config.py:88     self.chroma_path = str(BASE_DIR / "chroma_db")
```

Aucune référence dans `memory/`, `cognition/`, `intent/`, `agents/`,
`execution/`. Le chemin est défini mais inutilisé depuis la migration
MemPalace. Dette latente : entrée à supprimer de `Config` au prochain
ménage (hors-scope T-Embedder).

### 2.3 MemPalace `~/.mempalace/palace/` — collection `mempalace_drawers`

Backend : ChromaDB persistant. **Toutes les écritures prod** passent
par `memory.writer.write_*` qui appelle
`mempalace.palace.get_collection(config.mempalace_path)` et finissent
ici.

```
total      : 655
dim        : 384

by_wing :
  aria_episodic    443  ← interactions, image_input, image_generated
  aria_classifier  212  ← cache classifier d'opérations

by_type :
  interaction       352
  classifier_cache  212
  memory             36   ← legacy, pré-réécriture writer.py
  image_input        25
  image              22   ← legacy
  ingestion           7   ← legacy, pré-suppression auto-INGESTION (commit 31c21a4)
  image_generated     1
```

Top 5 rooms par wing (échantillon) :

| Wing | Room dominant | Count |
|---|---|---|
| `aria_episodic` | `general` | (legacy room) |
| `aria_classifier` | `RESPOND` / `EXTRACT` / `CREATE` / `ATTACH` (= les `CognitiveOperation`) | mix |

### 2.4 MemPalace `~/.mempalace/palace/` — collection `mempalace_closets`

```
count : 32
dim   : 384
wing  : aria (legacy, 32/32)
```

État conforme à CLAUDE.md (couches mémoire) : « 32 entrées résiduelles
dans `mempalace_closets` non migrées (hors scope sprint 4, à arbitrer
si un usage justifie leur migration) ».

Aucune sortie en lecture pour ces entrées dans le code prod (le bridge
ne lit que `aria_episodic`/`aria_semantic`/par room). Donc même si on
change l'embedder, ces 32 vecteurs sont inertes — re-encoding inutile.

### 2.5 `intents.json`

```
path     : ~/.aria/intents.json  (40 KB)
schéma   : { intent_id: { id, name, description, status, ... } }
count    : 63
status   : active 62, completed 1
embedding persisté : NON
```

Confirme l'audit sprint 5 §4 : aucun champ `embedding` ni `vector`
dans les enregistrements. Les embeddings sont **reconstruits au boot**
par `IntentStore` via `embedder.encode([intent.name])` (voir
`core/kernel.py:109` qui instancie `Embedder(config.EMBEDDING_MODEL)`).

Conséquence migration : changer le modèle d'embedding ne nécessite
**aucune** opération sur ce fichier — le re-encoding est gratuit
(coût : un seul appel batch de 63 textes au démarrage, ~50 ms même
sur le baseline actuel).

### 2.6 Caches additionnels — recherche exhaustive

```
$ grep -rl "embedding" --include="*.py" .   # hors __pycache__
embedding/embedder.py
embedding/embedding_contract.py
core/kernel.py
intent/intent_recall_engine.py
intent/intent_store.py
... (uniquement des callers de Embedder.encode, pas de cache disjoint)
```

Aucun cache LRU décoré sur `Embedder.encode`. Aucun pickle, JSON,
parquet ou autre stockage vectoriel hors des collections déjà
inventoriées. Aucun index vectoriel parallèle (FAISS, Annoy, hnswlib).

### 2.7 Synthèse migration

Ordre de grandeur du coût d'un changement de modèle :

| Étape | Volume | Estimation temps (CPU 18 vCPU) |
|---|---|---|
| Re-encoder `mempalace_drawers` | 655 docs | ~5–30 s selon modèle |
| Re-encoder `intents.json` (boot) | 63 noms | <100 ms |
| Réécrire la collection (delete + upsert) | 655 ops | ~5 s |
| Validation post-migration (count, dim, peek) | — | trivial |

Un changement vers un modèle dim 768 ou 1024 implique aussi de
**vérifier** que ChromaDB ne renvoie pas d'erreur de cohérence dim
sur la collection : la collection ne stocke pas explicitement la dim
attendue, mais une fois un premier vecteur inséré la dim est figée.
Solution canonique : `client.delete_collection("mempalace_drawers")`
puis recréer + upsert. Une procédure de migration sera détaillée
dans T-Embedder3.

---

## Annexes

- **Inventaire JSON brut** : `/tmp/aria_vector_inventory.json` (produit
  par le script ; non versionné).
- **Script** :
  [`scripts/embedder_bench/inventory_vector_stores.py`](../../scripts/embedder_bench/inventory_vector_stores.py).
- **Cas C5 (référence pour T3)** : 4 messages extraits de
  `docs/sprint5/audit_intent_matching.md` §7 cas 5, oracle attendu
  `recettes santé culinaire`.
