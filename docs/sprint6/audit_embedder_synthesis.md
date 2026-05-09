# Audit Embedder — Synthèse + Recommandation T-Embedder2

**Sprint 6 / sous-sprint embedder, tour 1.** Branche
`feat/sprint6-embedder-audit`. Cette synthèse référence
`audit_embedder_inventory.md` (Tâches 1+2) et
`audit_embedder_benchmark.md` (Tâches 3+4) pour les chiffres bruts.

---

## 1. Constat sur la racine du bug #18

Le bug intent matching documenté en sprint 5 §5/§9 a une cause unique
mesurée empiriquement : l'embedder `all-MiniLM-L6-v2` produit en
français un espace de représentation **plat** — max pairwise sur 1953
paires d'intents = 0.668, médiane = 0.160. Conséquence directe : les
intents distincts ne se séparent pas suffisamment pour que le seuil
ATTACH=0.45 puisse trancher entre vrai positif et faux positif. C'est
un défaut d'**espace**, pas de seuil. Le passage à un modèle
multilingue dont l'espace en français est correctement structuré (max
pairwise > 0.85, doublons sémantiques regroupés) déplace le problème
vers les leviers complémentaires (re-rank LLM, signal de continuité,
nettoyage des intents fantômes) — qui sont l'objet de T-Match.

---

## 2. Tableau récap décisionnel

Trié par Recall@3 décroissant. Chiffres de
`audit_embedder_benchmark.md` §1.

| Tag | Modèle | Dim | R@1 | R@3 | Gap moyen | Cold (ms) | Warm (ms) | Thr (p/s) | Disk (MB) | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **M2** | paraphrase-multilingual-mpnet-base-v2 | 768 | 0.62 | **0.88** | +0.238 | 120 | 108 | 27 | 2253 | **Principal** |
| M0 | all-MiniLM-L6-v2 (baseline) | 384 | 0.25 | 0.62 | −0.077 | 61 | 35 | 107 | 183 | À remplacer |
| M3 | multilingual-e5-base | 768 | 0.12 | 0.62 | +0.032 | 77 | 107 | 24 | 2269 | Disqualifié qualité |
| M4 | bge-m3 | 1024 | 0.25 | 0.62 | +0.127 | **362** | 328 | 5.6 | 9129 | **VETO UX** (cold > 200 ms) |
| M1 | paraphrase-multilingual-MiniLM-L12-v2 | 384 | 0.12 | 0.50 | +0.219 | 51 | 56 | 78 | 959 | **Secours** (compromis) |
| M5 | all-mpnet-base-v2-onnx (choix externe) | 768 | 0.12 | 0.38 | +0.037 | 80 | 94 | 14 | 878 | **Disqualifié** (cf. §3) |
| M2-ONNX | M2 exporté localement | 768 | 0.62 | 0.88 | +0.238 | 51 | 46 | 31 | 1110 | **Variante perf de M2** |

---

## 3. Le choix `all-mpnet-base-v2-onnx` de la session externe tient-il ?

**Non.** Trois raisons documentées :

1. **Qualité métier** : sur le bench multilingue, M5 obtient les pires
   scores qualité de la liste — Recall@3 = 0.38 (vs 0.62 pour le
   baseline et 0.88 pour M2). Sur 8 cas terrain bug #18, M5 ne réussit
   qu'**1 ATTACH-correct sur 8**. Le faire passer en prod aggraverait
   le bug que la session voulait corriger.

2. **Espace de représentation** : `max pairwise = 0.667`,
   quasi-identique au baseline `all-MiniLM-L6-v2` (0.668). C'est un
   modèle ANGLOCENTRÉ — l'export ONNX ne change pas la langue
   d'entraînement. La racine du bug #18 (espace plat en français)
   n'est donc pas adressée.

3. **Justification interne de la session externe absente** : le commit
   `archive/embedder-parallel-work` ne contient aucune mesure qualité,
   uniquement des chiffres perf (phrases/s). Il semble que le choix
   `all-mpnet-base-v2-onnx` ait été motivé par un benchmark perf
   isolé, sans valider que le modèle traitait le problème d'origine.

**Décision T-Embedder1** : ne pas merger `archive/embedder-parallel-work`.
Le refactor `embedding/embedder.py` (ajout d'un mode ONNX
conditionnel) reste pertinent comme base pour T-Embedder2 si on
choisit d'aller en ONNX, mais **le modèle proposé est rejeté**.

---

## 4. Recommandation pour T-Embedder2

### 4.1 Modèle principal — **M2** (`paraphrase-multilingual-mpnet-base-v2`)

**Justification** :
- Seul modèle au-dessus de R@3=0.62 (R@3=0.88) ; seul à dépasser 4/8
  ATTACH-correct sur les cas terrain.
- `max pairwise = 0.928` avec médiane 0.251 → espace correctement
  discriminant en français.
- Latence cold 120 ms / warm 108 ms : sous le veto UX 200 ms cold,
  P95 = 174 ms confortable pour Telegram.
- RSS Δ ≈ 385 MB en pic, acceptable sur la VM 125 Go.
- Disk 2.2 GB — le plus gros impact infra (à comparer avec les 183 MB
  du baseline), mais sans conséquence sur la VM (1.8 To dispo).

**Plan de bascule à T-Embedder2** :
1. Mettre à jour `config.py:35` : `EMBEDDING_MODEL =
   "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"`.
2. Re-encoder les 655 entrées de `mempalace_drawers` (cf. §5).
3. Vérifier que les seuils (`memory_relevance_threshold = 0.55`,
   F1 ATTACH = 0.45) restent pertinents — le tuning est l'objet de
   T-Match. Pour ce tour, garder les valeurs actuelles et mesurer
   la régression/amélioration sur les 8 cas terrain.
4. Lancer les tests : `pytest tests/ -q` doit toujours passer.

**Variante M2-ONNX** : option d'optimisation à arbitrer en
T-Embedder2. Mêmes vecteurs (à epsilon flottant près) que M2-ST mais
2.4× plus rapide en warm latency. Trade-off :
- ✅ 46 ms warm vs 108 ms (gain UX réel sur messages courts).
- ✅ Disk 1.1 GB vs 2.2 GB.
- ❌ L'export ONNX n'est pas redistribué sur HF — il faut soit
  versionner les ~1.1 GB en repo (incompatible avec git/Nextcloud),
  soit régénérer à l'install via `optimum-cli` (dépendance install
  +1 min de build), soit héberger le modèle sur un bucket privé.
- ❌ Code custom mean-pooling + normalize côté ARIA (cf. archive
  embedder.py) — surface d'attaque pour des bugs subtils.

**Recommandation** : démarrer avec M2-ST (chemin standard, dépendance
sentence-transformers déjà installée), valider le gain qualité,
arbitrer le passage à M2-ONNX comme optimisation séparée si la
latence pose problème UX en prod.

### 4.2 Modèle de secours — **M1** (`paraphrase-multilingual-MiniLM-L12-v2`)

**Justification** :
- Si la migration M2 pose un problème opérationnel imprévu (incompat
  ONNX d'un downstream, RAM, latence sur d'autres workloads), M1
  offre un compromis lisible : qualité au-dessus du baseline (Gap
  +0.219 vs −0.077) avec disk 4× plus petit que M2 (959 MB vs 2253).
- Latence excellente (warm 56 ms, cold 51 ms).
- Multilingue, max pairwise 0.884.
- Limite : R@3=0.50 reste en deçà de la barre minimale qualité (5
  ATTACH-corrects sur 8 cas attendus). À ne déployer que comme
  position de repli temporaire.

### 4.3 Modèle disqualifié — **M4** (`bge-m3`)

Bonne qualité (R@3=0.62, Gap +0.127, max pairwise 0.835), mais
**latence cold 362 ms** dépasse le veto UX. Le modèle reste
intéressant si l'usage évolue vers du batch (ingestion par lots,
indexation périodique) : 5.6 phrases/s soutenu. Hors-scope T-Embedder.

---

## 5. Conséquences sur la migration

D'après l'inventaire (audit_embedder_inventory.md §2.7) :

| Étape | Volume | Estimation (M2-ST) |
|---|---|---|
| Re-encoder `mempalace_drawers` | 655 docs | ~25 s (27 p/s × 24) |
| Re-encoder `intents.json` (boot) | 63 noms | ~2 s |
| Réécrire la collection ChromaDB (delete + upsert) | 655 ops | ~5 s |
| Validation post-migration | — | ~10 s |
| **Total** | — | **< 1 minute** |

Procédure canonique (à détailler en T-Embedder3 si fait dans un sprint
séparé) :
1. Snapshot du `~/.mempalace/palace/` (cp -r vers un dossier daté).
2. `client.delete_collection("mempalace_drawers")` puis recréer
   (la dim ChromaDB est figée au premier upsert).
3. Lire tous les `(documents, metadatas, ids)` du snapshot, re-encoder
   les documents avec M2, upsert.
4. Vérifier `count == 655` et `dim == 768` après migration.
5. Lancer les tests + un cas terrain (C2 « vacances Normandie ») pour
   valider l'amélioration.

`mempalace_closets` (32 entrées legacy) et `chroma_db/aria_memories`
(105 entrées orphelines) : **non migrés** — aucun caller prod, perte
fonctionnelle nulle. À nettoyer en sprint 7+.

---

## 6. Risques / dettes / surprises rencontrés

1. **Caveat e5 pairwise** : la métrique pairwise passage↔passage tasse
   artificiellement les scores (préfixe `passage:` partagé). Le verdict
   métier d'e5 reste à juger sur les R@K query→passage (médiocre
   ici), mais ne pas généraliser le « max pairwise élevé » à un défaut
   du modèle.

2. **Pollution `chroma_db/` à la racine** : ouvrir le store legacy
   avec `chromadb.PersistentClient` modifie les timestamps SQLite et
   fait apparaître les fichiers `.bin` / `.sqlite3` en `M` dans
   `git status`. Le store n'a aucun caller prod — proposition : le
   supprimer en sprint 7 (et virer `chroma_path` de `Config`).

3. **Lecture cas C5_T4 en prod** : l'intent fantôme `Dans ma cuisine
   j'ai : Une cocotte, une poêle...` (60 caractères tronqués) a été
   créé en prod par le bug SPLIT (dette #23). Il pollue les
   benchmarks parce qu'il devient le top-1 sur tous les modèles
   pour des messages contenant « cuisine » ou « cocotte ». **Le
   nettoyage de cet intent fantôme dans `intents.json` augmenterait
   mécaniquement les Recall des modèles M2/M4 sans aucun changement
   de modèle.** Levier T-Match.

4. **Cas durs lexicaux (C1, C5_T1)** : changer de modèle ne corrige
   pas le biais lexical sur « carottes » → `carottes dans jardin`.
   Un re-ranker LLM sur les top-3 ou un signal de continuité
   conversationnelle (favoriser les intents récents pour le même
   utilisateur) sont des leviers T-Match indispensables.

5. **Coût ONNX non documenté** : l'export `optimum-cli` produit un
   modèle `.onnx` non redistribué sur HF. La distribution interne du
   modèle exporté est une dette ops à arbitrer en T-Embedder2 —
   versioning git (1.1 GB inadapté), bucket privé, ou rebuild à
   l'install.

6. **Throughput M5 vs claim externe** : la session externe revendiquait
   un gain ONNX x3 sur `all-mpnet-base-v2`. Mesure ici : warm 94 ms
   sur l'inférence ONNX manuelle (mean pooling pytorch) vs 108 ms sur
   M2-ST — gain ~15 % seulement, **pas x3**. Le claim x3 n'a pas été
   reproduit dans l'environnement ARIA. La variante M2-ONNX
   (export local + onnxruntime direct + L2 numpy) atteint 46 ms warm
   sur M2 — c'est le vrai gain mesurable, mais sur M2 et pas sur M5.

7. **Dépendance ajoutée** : `psutil` installée dans le venv ARIA pour
   mesurer le RSS. Pip uniquement, déjà documentée dans
   `audit_embedder_benchmark.md` §6.

---

## 7. Verdict synthétique

**Migration recommandée** :
1. **M2** (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`)
   en remplacement de `all-MiniLM-L6-v2`, à arbitrer en T-Embedder2.
2. **Garder M1** comme position de repli si M2 pose un problème ops.
3. **Rejeter M5** (`all-mpnet-base-v2-onnx`) — empiriquement le pire
   sur le critère qualité.
4. **Ne pas merger** `archive/embedder-parallel-work`. Le refactor
   ONNX du fichier `embedder.py` peut être réintroduit séparément si
   et seulement si M2-ONNX est retenu après validation T-Embedder2.

**À ne PAS attendre de cette migration seule** :
- Correction des cas C1 / C5_T1 (biais lexical) — leviers T-Match.
- Disparition des intents fantômes — nettoyage T-Match.
- Continuité conversationnelle multi-tours — signal nouveau T-Match.

L'amélioration mesurable attendue : **R@3 de 0.62 à 0.88, ATTACH-correct
de 25 % à 50 % sans aucun autre changement**. Suffisant pour valider
T-Embedder comme premier maillon du redressement de l'intent matching.
