# Audit Embedder — Benchmark qualité + perf (T-Embedder1, Tâches 3+4)

**Sprint 6 / sous-sprint embedder, tour 1.** Branche
`feat/sprint6-embedder-audit`. Aucune modification de prod : tous les
chiffres sont reproductibles via les scripts
`scripts/embedder_bench/`.

---

## 1. Tableau récap croisé qualité × perf

Tableau central pour la décision T-Embedder2. Trié par
`Recall@3` décroissant.

| Tag | Modèle | Dim | R@1 | R@3 | Gap moyen | Cold (ms) | Warm (ms) | P95 (ms) | Thr (p/s) | RSS Δ (MB) | Disk (MB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M2** | paraphrase-multilingual-mpnet-base-v2 | 768 | **0.62** | **0.88** | **+0.238** | 120 | 108 | 174 | 27 | 385 | 2253 |
| M0 | all-MiniLM-L6-v2 (baseline ARIA) | 384 | 0.25 | 0.62 | −0.077 | 61 | 35 | 76 | 107 | 372 | 183 |
| M3 | multilingual-e5-base | 768 | 0.12 | 0.62 | +0.032 | 77 | 107 | 175 | 24 | 366 | 2269 |
| M4 | bge-m3 | 1024 | 0.25 | 0.62 | +0.127 | **362** ⚠ | 328 | 438 | 5.6 | 1237 | 9129 |
| M1 | paraphrase-multilingual-MiniLM-L12-v2 | 384 | 0.12 | 0.50 | +0.219 | 51 | 56 | 117 | 78 | 406 | 959 |
| M5 | all-mpnet-base-v2-onnx (choix externe) | 768 | 0.12 | **0.38** | +0.037 | 80 | 94 | 208 | 14 | 354 | 878 |

**Bonus M2-ONNX** (export local via `optimum-cli` + inference
`onnxruntime` direct) : cold=51ms · warm=46ms · thr=31/s · disk=1110MB.
Gain x2.3 sur warm vs M2 ST natif. Détail §5.

**Lecture rapide** :
- **M2 domine en qualité** : seul modèle au-dessus de R@3=0.62.
- **M5 (le choix de la session externe) est le plus mauvais en qualité**
  (R@3=0.38) — empiriquement éliminé.
- **M4 (bge-m3) est trop lent** : cold=362ms > 200ms (veto UX).
- **M0 baseline** a un Gap moyen négatif → confirme le bug #18.

---

## 2. Résultats détaillés Tâche 3 — qualité (8 cas, 6 modèles)

Cas terrain extraits de `docs/sprint5/audit_intent_matching.md` §7.
Corpus : 63 intents (62 active + 1 completed) chargés depuis
`~/.aria/intents.json`. Seuil F1 simulé = 0.45 (valeur prod actuelle).

### 2.1 Décision F1 simulée (top-1 + seuil 0.45) par modèle × cas

`✓` = ATTACH **sur** l'oracle. `✗` = ATTACH sur intent fautif. `C` =
CREATE (top-1 < 0.45). `S` = SPLIT (top-1 < 0.45 et ≥ 3 scores
> 0.40). Tableau **généré depuis** `/tmp/aria_bench_quality.json`,
pas écrit à la main.

| Cas | Oracle (candidats) | M0 | M1 | M2 | M3 | M4 | M5 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|
| C1 carottes ragoût | recettes santé culinaire / recette rapide | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| C2 vacances Normandie | voyage organisation / réservation voyage | ✗ | C | ✓ | ✓ | ✓ | ✗ |
| C3 carotte citron 6p | recettes santé culinaire | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| C4 Tu vas bien ? | salutation | ✗ | C | C | ✗ | ✓ | C |
| C5_T1 recette fer | recettes santé culinaire | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| C5_T2 lentilles épinards | recettes santé culinaire | ✗ | C | ✓ | ✗ | ✗ | ✓ |
| C5_T3 carotte citron | recettes santé culinaire | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| C5_T4 inventaire cuisine | recettes santé culinaire | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **ATTACH ✓** | — | **2/8** | **0/8** | **4/8** | **2/8** | **2/8** | **1/8** |

**Lecture importante** : Recall@1 (§2.2) ≠ ATTACH-correct.

- *Recall@1 mesure la capacité du modèle à mettre l'oracle en rang 1*.
- *ATTACH-correct mesure le résultat pipeline = oracle au rang 1 ET
  score > seuil 0.45.*

M2 a R@1=0.62 mais ATTACH-correct=4/8=50% : sur C4 (« Tu vas bien ? »),
M2 trouve `salutation` au rang 1 mais à 0.362 < 0.45 → CREATE plutôt
qu'ATTACH. **C'est un bug de seuil, pas de modèle**, et T-Match devra
arbitrer.

**3 cas durs où aucun modèle ne réussit** (C1, C5_T1, C5_T4) :
- **C1** : « Les carottes en ragoût recette ». Tous les modèles (sauf
  M3/M5 qui font CREATE) ATTACHent sur `carottes dans jardin` parce que
  le mot lexical « carottes » domine la cosine. M2 met l'oracle en
  rang 3 — un re-ranker LLM ou un signal de domaine résoudrait ça en
  T-Match.
- **C5_T1** : top-1 = `recette houmous` (intent culinaire générique
  qui capte la sémantique « recette »). Oracle rang 2.
- **C5_T4** : « Dans ma cuisine j'ai... » → top-1 = l'intent fantôme
  homonymique créé en prod (cf. §2.3 et dette #23). Aucun modèle
  d'embedding ne peut résoudre un conflit où l'intent fantôme est
  littéralement le préfixe du message.

Ces 3 cas valident le diagnostic : **changer de modèle d'embedding
améliore très significativement le matching mais ne suffit pas — le
re-ranker, le signal de continuité, et la nettoyage des intents
fantômes (T-Match) sont des leviers complémentaires.**

### 2.2 Métriques par modèle

| Tag | n_cases | Recall@1 | Recall@3 | Gap moyen | Gap min | Gap max |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 8 | 0.25 | 0.62 | −0.077 | −0.342 (C2) | +0.111 (C3) |
| M1 | 8 | 0.12 | 0.50 | +0.219 | +0.024 | +0.541 |
| **M2** | 8 | **0.62** | **0.88** | **+0.238** | −0.024 | +0.621 |
| M3 | 8 | 0.12 | 0.62 | +0.032 | −0.039 | +0.083 |
| M4 | 8 | 0.25 | 0.62 | +0.127 | +0.011 | +0.299 |
| M5 | 8 | 0.12 | 0.38 | +0.037 | −0.023 | +0.094 |

**Gap moyen positif** = oracle scoré au-dessus du faux match (en
moyenne). M0 baseline est le seul à avoir un Gap moyen *négatif* — ce
qui signifie qu'en moyenne, le faux match d'aujourd'hui dépasse
l'oracle attendu. C'est la traduction métrique directe du bug #18.

### 2.3 Cas représentatifs — top 5 brut (M0 vs M2)

#### C1 « Les carottes en ragoût recette »

| Modèle | Top 5 (score, intent — ★ = oracle) | Décision |
|---|---|---|
| M0 | (0.642, *carottes dans jardin*) (★0.545, recettes santé culinaire) (0.479, *Pourquoi elle ne germent pas*) (★0.476, recette rapide) (0.472, *semis en intérieur*) | ATTACH `carottes dans jardin` ✗ |
| M2 | (0.814, *carottes dans jardin*) (0.698, recette houmous) (★0.637, recettes santé culinaire) (0.602, méthodes de cuisson saines) (0.596, jardinage plantes + jardinage légumes) | ATTACH `carottes dans jardin` ✗ |

M2 augmente le **gap absolu** entre top-1 et oracle (0.814 vs 0.637 =
0.18) mais **ne corrige pas l'ATTACH** : le mot « carottes » domine
toujours le matching. Mention dans la synthèse : **un re-ranker LLM
sur les top-3 corrigerait ce cas immédiatement** (le LLM voit
clairement « ragoût recette » → culinaire).

#### C2 « Planifier des vacances en Normandie »

| Modèle | Top 1 | Top 2 | Décision |
|---|---|---|---|
| M0 | (0.502, *Dans ma cuisine j'ai...*) | (0.466, *Pourquoi elle ne germent pas*) | ATTACH faux ✗ ; oracle `réservation voyage` au rang **53/63**. |
| M2 | (★0.578, réservation voyage) | (0.424, capitale france) | ATTACH `réservation voyage` ✓ |

**Cas emblématique du gain M2** : M0 ATTACH sur un intent fantôme
hors-sujet (`Dans ma cuisine j'ai...` issu du bug C5_T4) parce que
l'oracle est **rang 53** — l'espace M0 est trop plat pour positionner
correctement les intents voyage. M2 met `réservation voyage` au rang
1 (0.578) dès la première recherche.

#### C5 (4 tours cuisine) — Rang oracle par tour

| Tour | Top-1 actuel (M0) | Score top-1 M0 | Rang oracle M0 | Top-1 M2 | Score top-1 M2 | Rang oracle M2 |
|---|---|---:|---:|---|---:|---:|
| T1 | *Pourquoi elle ne germent pas* | 0.535 | 2 | *recette houmous* | 0.599 | 2 |
| T2 | *Pourquoi elle ne germent pas* | 0.507 | 6 | recettes santé culinaire ★ | 0.610 | 1 |
| T3 | recettes santé culinaire ★ | 0.575 | 1 | recettes santé culinaire ★ | 0.680 | 1 |
| T4 | *Dans ma cuisine j'ai...* | 0.824 | 3 | *Dans ma cuisine j'ai...* | 0.892 | 4 |

M2 corrige T2 (oracle rang 6 → 1) et améliore les autres tours, mais
**T4 reste pollué par l'intent fantôme** (corrigible uniquement par
nettoyage des intents en T-Match). T1 reste mal classé : M2 préfère
`recette houmous` au top-1 — un re-ranker LLM verrait immédiatement
que « carotte citron pour 6 personnes » n'est pas du houmous.

---

## 3. Résultats détaillés Tâche 3 — distribution pairwise

Pairwise calculé sur 63 intents → 1953 paires. Métrique de
discriminabilité : un modèle plat aura `max < 0.70` et `spread`
faible ; un modèle discriminant a un `max > 0.85` sur les vrais
doublons sémantiques et une médiane basse.

| Tag | Max | Médiane | Spread | #>0.85 | #>0.70 | #>0.50 |
|---|---:|---:|---:|---:|---:|---:|
| M0 | 0.668 | 0.160 | 0.508 | 0 | 0 | 15 |
| M1 | 0.884 | 0.208 | 0.676 | 8 | 32 | 102 |
| **M2** | **0.928** | 0.251 | 0.676 | 7 | 37 | 164 |
| M3 ⚠ | 0.960 | 0.871 | 0.089 | **1497** | 1953 | 1953 |
| M4 | 0.835 | 0.404 | 0.431 | 0 | 8 | 176 |
| **M5** | **0.667** | 0.208 | 0.459 | 0 | 0 | 32 |

### Interprétation

**M0 (baseline)** : `max=0.668` reproduit exactement l'audit sprint 5
§5 (« max pairwise 0.668 sur 1770 paires »). L'espace est totalement
plat — aucune paire ne dépasse 0.70. Les vrais doublons (`météo
locale saison` ↔ `météo des prochains jours` ; `jardinage plantes` ↔
`jardin potager`) sont scorés au même niveau que des paires
indépendantes.

**M5 (choix externe)** : `max=0.667` — quasi-identique à M0. **Confirme
empiriquement que `all-mpnet-base-v2-onnx` ne résout pas la racine du
bug #18.** Le passage à un modèle anglocentré plus gros ne change rien
à la planéité de l'espace en français.

**M2 (candidat principal)** : `max=0.928`, médiane=0.251, 7 paires
> 0.85. Les top 5 paires de M2 sont des vrais doublons sémantiques
identifiés à la main dans l'audit sprint 5 (voir
`/tmp/aria_bench_pairwise.json` → `models[2].stats.top10_pairs`).
Espace correctement structuré : doublons proches, étrangers distants.

**M4 (bge-m3)** : `max=0.835`, médiane=0.404. Pas de paire > 0.85,
mais médiane élevée → espace plus tassé que M2 sans la
discriminabilité supérieure. Combiné avec sa lenteur (cf. §4), pas
attractif.

**M3 (e5-base) — caveat** : `médiane=0.871` extrême et 1497/1953
paires > 0.85 ne reflète **pas** un défaut intrinsèque. e5 est conçu
asymétrique (préfixes `query:` ≠ `passage:`) : tous les vecteurs
passage partagent le même préfixe `passage: ` qui domine la sémantique
sur des chaînes courtes (noms d'intent ≈ 3-5 mots). La métrique
pairwise passage↔passage n'est pas le cas d'usage canonique d'e5.
Le verdict métier d'e5 reste donc à juger sur la qualité query→passage
(§2.2 : R@1=0.12, R@3=0.62 — médiocre).

---

## 4. Résultats Tâche 4 — perf CPU

VM Debian, 18 vCPU, pas de GPU. 100 phrases françaises typiques
(intents + variations). Mesures :
- **Cold** : 1er `encode([phrase])` après `warmup` du chargement.
- **Warm med / P95** : médiane / P95 de 100 `encode([phrase])`
  consécutifs (taille 1 — usage prod par message Telegram).
- **Throughput batch** : 100 phrases batch=32, 3 runs, médiane.
- **RSS Δ peak** : delta peak vs RSS du process avant chargement.
- **Disk** : taille du dossier HF cache.

| Tag | Cold (ms) | Warm med (ms) | Warm P95 (ms) | Thr (p/s) | RSS Δ (MB) | Disk (MB) | Verdict UX |
|---|---:|---:|---:|---:|---:|---:|---|
| M0 | 61 | 35 | 76 | 107 | 372 | 183 | OK (mais qualité ✗) |
| M1 | 51 | 56 | 117 | 78 | 406 | 959 | OK |
| **M2** | 120 | 108 | 174 | 27 | 385 | 2253 | OK (cold < 200ms) |
| M3 | 77 | 107 | 175 | 24 | 366 | 2269 | OK |
| M4 | **362** ⚠ | 328 | 438 | 5.6 | 1237 | 9129 | **VETO UX** (cold > 200 ms) |
| M5 | 80 | 94 | 208 | 14 | 354 | 878 | OK |

**Critères UX** (rappel brief) : qualité > vitesse, mais
`cold > 200 ms = veto`. M4 ne passe pas : **éliminé sur perf**, même
si sa qualité est acceptable.

**Note throughput M5** : ONNX manuel (mean pooling + L2 norm en pytorch
côté ARIA) ajoute du overhead vs sentence-transformers natif. Pour
mesurer le vrai potentiel ONNX, voir §5.

---

## 5. Bonus Tâche 4-F — export ONNX local de M2

Tentative `optimum-cli export onnx --model
sentence-transformers/paraphrase-multilingual-mpnet-base-v2
--task feature-extraction /tmp/m2-onnx`. Export OK en ~80 s.

**Important** : le modèle exporté contient déjà la couche pooling
(`sentence_embedding` est exposé directement). Inférence via
`onnxruntime.InferenceSession` direct + L2 normalize côté numpy.

| Modèle | Cold (ms) | Warm med (ms) | Warm P95 (ms) | Thr (p/s) | Disk (MB) |
|---|---:|---:|---:|---:|---:|
| M2 (ST natif) | 120 | 108 | 174 | 27 | 2253 |
| **M2-ONNX** | **51** | **46** | **64** | **31** | **1110** |

**Gain** : warm latency divisée par ~2.4. P95 divisée par ~2.7. Disk
divisé par 2 (poids unique fp32 ONNX au lieu du dossier ST complet).

Sur M3 (e5-base), l'export n'a pas été tenté : e5 est éliminé qualité-
wise (R@1=0.12), donc le gain ONNX serait sans intérêt opérationnel.
Si M3 redevenait candidat (ex : preference de licence, ou nouvelle
mesure post-tuning des préfixes), refaire l'export en T-Embedder2.

**Implication T-Embedder2** : le candidat principal M2 est livrable
en 2 variantes :
1. **M2-ST** (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`)
   — pas de bibliothèque ONNX requise, 108ms warm, 27 p/s.
2. **M2-ONNX** (export local précomputé) — 46ms warm, 31 p/s, mais
   le modèle exporté n'est pas redistribué sur HF, il faut soit
   versionner les ~1.1GB en repo, soit régénérer à l'install. Trade-
   off à arbitrer en T-Embedder2 (cf. synthèse §4).

---

## 6. Reproductibilité

```bash
# T1+T2 inventaire
./venv/bin/python scripts/embedder_bench/inventory_vector_stores.py

# T3 qualité (6 modèles)
./venv/bin/python scripts/embedder_bench/benchmark_quality.py

# T3 pairwise (6 modèles)
./venv/bin/python scripts/embedder_bench/pairwise_distribution.py

# T4 perf CPU (6 modèles)
./venv/bin/python scripts/embedder_bench/benchmark_perf.py

# Bonus ONNX export local (M2)
./venv/bin/optimum-cli export onnx \
    --model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
    --task feature-extraction /tmp/m2-onnx
```

Dépendances pip ajoutées dans le venv ARIA pendant T-Embedder1 :
- `psutil` (mesure RSS) — `./venv/bin/pip install psutil`

Les autres dépendances (`sentence-transformers`, `transformers`,
`torch`, `optimum`, `onnxruntime`) étaient déjà présentes.

Sorties JSON brutes (non versionnées, dans `/tmp`) :
- `aria_vector_inventory.json` (T1+T2)
- `aria_bench_quality.json` (T3 qualité)
- `aria_bench_pairwise.json` (T3 pairwise)
- `aria_bench_perf.json` (T4 perf)

**Caveat reproductibilité** : le script `inventory_vector_stores.py`
ouvre `chroma_db/` à la racine du projet (legacy). ChromaDB met à jour
les timestamps internes du SQLite à chaque ouverture, ce qui fait
apparaître les fichiers binaires comme modifiés en `git status` après
exécution. Restaurer avec `git checkout -- chroma_db/` après chaque
run. À résoudre proprement quand le store legacy sera supprimé
(hors-scope T-Embedder).
