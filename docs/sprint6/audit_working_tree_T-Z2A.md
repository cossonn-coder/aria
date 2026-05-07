# Audit working tree — sprint 6 / T-Z2-A

**Date** : 2026-05-07
**Branche** : `feat/sprint2-image-pipeline` (HEAD `b1d78ab`, +3 sur origin)
**Mode** : lecture seule, aucun changement git appliqué.

---

## Section 1 — Vue d'ensemble

### `git status` (sortie complète)

```
Sur la branche feat/sprint2-image-pipeline
Votre branche est en avance sur 'origin/feat/sprint2-image-pipeline' de 3 commits.
  (utilisez "git push" pour publier vos commits locaux)

Modifications qui ne seront pas validées :
  modifié :         .gitignore
  modifié :         CLAUDE.md
  modifié :         README.md
  modifié :         agents/base_agent.py
  modifié :         agents/controller/controller_agent.py
  modifié :         agents/registry_agent.py
  modifié :         cognition/cognitive_trace.py
  modifié :         cognition/memory_context.py
  modifié :         config.py
  modifié :         context.md
  modifié :         core/kernel.py.bak
  modifié :         embedding/embedder.py
  modifié :         embedding/embedding_contract.py
  modifié :         intent/intent.py
  modifié :         tests/cognition/test_cognitive_scenarios.py
  modifié :         tests/cognition/test_intent_engine.py
  modifié :         tests/cognition/test_intent_recall.py
  modifié :         tests/cognition/test_kernel_integration.py
  modifié :         tests/execution/test_llm_execution_router.py
  modifié :         tests/kernel_sandbox.py

Fichiers non suivis:
  aria-sprint-3.1.zip
  bin/
  docs/sprint4/
  docs/sprint6/audit_embedder_external.md
  docs/sprint6/audit_git_pre_renommage.md
  docs/sprint6/audit_taxonomy.md
  docs/sprint6/context_sprint_6_kickoff_v2.md
  scripts/bench_cpu.py
  scripts/count_memory_by_wing.py
  scripts/test_onnx.py
  scripts/test_onnx_embedder.py
  test_deepseek_tools.py
```

### Comptage et stat

- `git status --short | wc -l` → **32** entrées (20 M + 12 ??).
- `git diff --stat | tail -1` → **20 files changed, 1449 insertions(+), 1351 deletions(-)**.
- `git diff --stat -w | tail -1` (ignore whitespace) → **6 files changed, 269 insertions(+), 171 deletions(-)**.
- Dernier commit : `2026-05-07 15:32:41 +0200 b1d78ab T11 sprint 5: clôture sprint 5 — audit intent matching + kickoff sprint 6`.

### Découverte critique : ⚠️ 14/20 modifs sont des conversions LF→CRLF

`git diff --stat` (avec ws) compte 20 fichiers et ~2800 lignes touchées.
`git diff --stat -w` (sans ws) ne compte plus que **6 fichiers** et 440 lignes.

→ **14 fichiers ne diffèrent du HEAD que par leurs fins de ligne** (LF dans le blob HEAD, CRLF dans le working tree).

Vérification `od -c` sur `agents/base_agent.py` :

```
HEAD blob :    # aria/agents/base_agent.py\n\nfrom abc import ABC, abstractmethod\n
Working tree : # aria/agents/base_agent.py\r\n\r\nfrom abc import ABC, abstractmethod\r\n
```

`file(1)` confirme : `agents/base_agent.py: ... with CRLF line terminators`.

Cause probable : un outil ou éditeur (extraction de zip ? sync Nextcloud ? éditeur Windows en passthrough ?) a réécrit ces fichiers avec CRLF. À traiter séparément des vraies modifs — `git checkout -- <file>` les remet en LF, ou un `.gitattributes` avec `* text=auto` règle le problème durablement.

---

## Section 2 — Fichiers modifiés (20)

Trié par catégorie. Les 14 fichiers "CRLF only" sont regroupés en bas — ils n'ont pas de modif sémantique.

### 2A — Vraies modifs sémantiques (6 fichiers)

| Fichier | +/- | Catégorie présumée | Aperçu |
|---|---|---|---|
| `CLAUDE.md` | +44 / -22 (-w) | doc / convention projet | Réécriture des règles d'architecture (règle 1 : précise "posés APRÈS le spread de `extra`" + ref bug W4 sprint 3.1 dette #11) ; ajout d'une section "État réel post-sprint-4" pour les couches mémoire (épisodique 408 entrées, sémantique non alimentée, classifier cassé, intentual non implémenté). |
| `context.md` | +173 / -147 (-w) | doc / contexte session | Réécriture massive du fichier de reprise. Date passée à "1er Mai 2026", état "sprint 3.0 (UX critique) clos". Ajout d'une section "Workflow de cette session (à mémoriser)" décrivant le double pipeline architecte (claude.ai) / implémenteur (Claude Code). |
| `config.py` | +5 / -1 (-w) | config | Ajout de `deepseek_api_key` (champ + chargement env `DEEPSEEK_API_KEY`). Changement de `EMBEDDING_MODEL` : `"all-MiniLM-L6-v2"` → `"yilunzhang/all-mpnet-base-v2-onnx"`. **Modif liée au travail embedder hors-workflow.** |
| `embedding/embedder.py` | +56 / -17 (-w) | embedder hors-workflow | Refactor majeur : ajout d'imports conditionnels ONNX (`optimum.onnxruntime`, `transformers`), branche `is_onnx` détectée par suffixe `-onnx` dans le nom de modèle, double chemin d'init (SentenceTransformer vs ORTModel + AutoTokenizer + mean_pooling manuel). **Cœur du travail embedder hors-workflow.** |
| `embedding/embedding_contract.py` | +1 / -0 (-w) | embedder hors-workflow | Ajout d'un commentaire d'en-tête `#aria/embedding/embedding_contract.py`. Probablement effet de bord du travail sur l'embedder. |
| `tests/execution/test_llm_execution_router.py` | +14 / -14 (-w) | code sprint 5 post-commit ? | Renomme `store_interaction` → `write_interaction` partout (commentaire d'intent + `@patch("execution.routers.llm_router.store_interaction")` → `write_interaction`). Cohérent avec la migration W5 → `memory.writer.write_interaction` (commits T4-T8). **Le test n'a apparemment pas été mis à jour avec les commits du sprint 5 — c'est un oubli.** |

### 2B — Modifs CRLF uniquement (14 fichiers)

Aucun changement sémantique. `git diff -w` retourne **vide** pour tous ceux-ci. Les +/- listés sont l'illusion du diff mode standard.

| Fichier | +/- (diff std) | Catégorie présumée | Aperçu |
|---|---|---|---|
| `.gitignore` | +30 / -30 | CRLF only | Diff montre toutes les lignes "supprimées+ajoutées", contenu identique. |
| `README.md` | +124 / -124 | CRLF only | Idem. |
| `agents/base_agent.py` | +80 / -80 | CRLF only | `file` : "with CRLF line terminators". Confirmé par `od -c`. |
| `agents/controller/controller_agent.py` | +73 / -73 | CRLF only | Idem. |
| `agents/registry_agent.py` | +28 / -28 | CRLF only | Idem. |
| `cognition/cognitive_trace.py` | +30 / -30 | CRLF only | Idem. |
| `cognition/memory_context.py` | +15 / -15 | CRLF only | Idem. |
| `core/kernel.py.bak` | +290 / -290 | CRLF only + obsolète | Voir Section 3 — c'est un .bak. |
| `intent/intent.py` | +197 / -197 | CRLF only | `file` : "with CRLF line terminators". |
| `tests/cognition/test_cognitive_scenarios.py` | +77 / -77 | CRLF only | Idem. |
| `tests/cognition/test_intent_engine.py` | +51 / -51 | CRLF only | `file` : "with CRLF line terminators". |
| `tests/cognition/test_intent_recall.py` | +37 / -37 | CRLF only | Idem. |
| `tests/cognition/test_kernel_integration.py` | +61 / -61 | CRLF only | Idem. |
| `tests/kernel_sandbox.py` | +57 / -57 | CRLF only | Idem. |

---

## Section 3 — Fichiers non suivis (12)

| Fichier | Taille | mtime | Type | Recommandation |
|---|---|---|---|---|
| `aria-sprint-3.1.zip` | 619 624 o | 2026-05-02 12:04 | archive | **supprimer** (snapshot daté, redondant avec git+tag `sprint-3.1`) |
| `bin/` (3 fichiers) | 14 160 o | 2026-05-04 14:33 | scripts deepseek | **commit branche courante** ou .gitignore (à arbitrer) |
| `docs/sprint4/` (2 fichiers) | 24 053 o | 2026-05-02 12:38 | doc | **commit branche courante** (doc sprint 4 non commitée) |
| `docs/sprint6/audit_embedder_external.md` | 8 540 o | 2026-05-07 20:37 | doc audit | **commit branche courante** (livrable sprint 6) |
| `docs/sprint6/audit_git_pre_renommage.md` | 11 913 o | 2026-05-07 20:38 | doc audit | **commit branche courante** (livrable sprint 6 / T-Z1) |
| `docs/sprint6/audit_taxonomy.md` | 31 068 o | 2026-05-07 20:23 | doc audit | **commit branche courante** (livrable sprint 6) |
| `docs/sprint6/context_sprint_6_kickoff_v2.md` | 23 042 o | 2026-05-07 20:36 | doc kickoff | **commit branche courante** (livrable sprint 6) |
| `scripts/bench_cpu.py` | 1 446 o | 2026-05-07 16:44 | script bench | **archive embedder** (lié à l'évaluation des modèles d'embedding) |
| `scripts/count_memory_by_wing.py` | 1 195 o | 2026-05-02 11:26 | script diag | **commit branche courante** (outil diagnostic mémoire, daté sprint 4) |
| `scripts/test_onnx.py` | 1 737 o | 2026-05-07 16:47 | script test | **archive embedder** (test ONNX exploratoire) |
| `scripts/test_onnx_embedder.py` | 296 o | 2026-05-07 17:09 | script test | **archive embedder** (test classe Embedder en mode ONNX) |
| `test_deepseek_tools.py` | 10 520 o | 2026-05-04 14:09 | script test/intégration | **à arbitrer** (test des outils `bin/` ; placement à la racine inhabituel) |

### Investigations détaillées

#### `aria-sprint-3.1.zip`

`unzip -l` (extrait) :
```
Archive:  aria-sprint-3.1.zip
6d1c3c94f38119d15a2d3964494afa0c9bee372d
  Length      Date    Time    Name
  ...
        0  2026-05-02 11:14   aria-sprint-3.1/
      281  2026-05-02 11:14   aria-sprint-3.1/.gitignore
     2302  2026-05-02 11:14   aria-sprint-3.1/CLAUDE.md
     ...
   167600  2026-05-02 11:14   aria-sprint-3.1/chroma_db/85363a1d-.../data_level0.bin
   548864  2026-05-02 11:14   aria-sprint-3.1/chroma_db/chroma.sqlite3
```

→ Snapshot complet du repo au commit `6d1c3c9` (= `docs(sprint-4): kickoff context for architectural sprint`), incluant `chroma_db/` (donc des données mémoire prod). À supprimer **après confirmation que le tag git `sprint-3.1` couvre bien le code** — ce qui semble être le cas (tag présent localement, non pushé seulement pour `sprint-5`). **Le contenu de `chroma_db/` peut contenir des données utilisateur sensibles** ; ne pas commit ce zip.

#### `core/kernel.py.bak`

- Présent dans git history (suivi). Modifié dans le working tree par CRLF only.
- `core/kernel.py` existe également (8494 o, mtime 2026-05-06).
- `diff core/kernel.py.bak core/kernel.py` : divergence forte (291 vs 202 lignes, contenu différent — le `.bak` a des imports doublons `LLMRouter` venant de deux modules différents, signe d'une version intermédiaire en cours de refactor).
- **Recommandation** : à supprimer du repo (suivi historiquement, mais c'est un `.bak` qui n'a rien à faire en commit). Demande arbitrage Nico car déjà tracké.

#### `test_deepseek_tools.py` (racine repo)

Tête de fichier :
```python
#!/usr/bin/env python3
"""
test_deepseek_tools.py — Valide que ask-deepseek, write-deepseek et extract-chat fonctionnent.
Usage : python3 test_deepseek_tools.py
        python3 test_deepseek_tools.py --tool ask   # tester un seul outil
"""
import argparse, json, os, subprocess, sys, tempfile, textwrap
from pathlib import Path
# Charge le .env du projet aria si la clé n'est pas déjà dans l'environnement
if not os.environ.get("DEEPSEEK_API_KEY"):
    env_file = Path(__file__).resolve().parent / ".env"
    ...
```

→ Script de validation manuelle des outils `bin/ask-deepseek.py`, `bin/write-deepseek.py`, `bin/extract-chat.py`. Pas un test pytest, pas dans `tests/`. Lit `.env` à la racine du projet pour récupérer `DEEPSEEK_API_KEY`. **Pas de secret en clair dans le fichier**, mais il dépend d'un `.env` présent à la racine. Placement à la racine inhabituel (devrait être `scripts/` ou un `tests/integration/`).

#### `bin/`

Trois scripts exécutables (chmod +x) :

- `bin/ask-deepseek.py` — délégateur DeepSeek V4 Flash pour lecture de fichiers volumineux (l'outil mentionné dans `CLAUDE.md`). Shebang dur : `#!/home/nico/Nextcloud/projects/aria/venv/bin/python3` (chemin absolu spécifique machine).
- `bin/extract-chat.py` — extracteur de transcripts Claude Code (.jsonl).
- `bin/write-deepseek.py` — générateur de boilerplate via DeepSeek. Même shebang absolu.

Ces scripts sont référencés dans `CLAUDE.md` (section "Délégation DeepSeek V4 Flash") sous le chemin `~/.local/bin/`. Présents ici dans `bin/` du repo : **soit c'est la version source qu'on commit dans le repo, soit c'est une copie locale à ignorer**. À arbitrer.

#### `docs/sprint6/*.md`

| Fichier | Lignes | 1ère section visible |
|---|---|---|
| `audit_embedder_external.md` | 192 | "## Contexte et objectif initial" — bilan session GPU/embedding (passthrough VM Debian, GTX 1060 occupée par VM Windows gaming, décision de rester CPU). |
| `audit_git_pre_renommage.md` | 163 | Capture du livrable T-Z1 (audit git réalisé au tour précédent). Format `● Bash(...)` — ressemble à un copier-coller de la sortie de Claude Code. |
| `audit_taxonomy.md` | 510 | "Je travaille sur la taxonomie pragmatique des messages reçus..." — brief V1. **Confirme : un seul fichier qui contient les 3 versions** (V1 + V2-Gemini commençant ligne 382 `##### v2 version gemini :`, + V2-DeepSeek commençant ligne 433 `##### v2 version deepseek :`). |
| `context_sprint_6_kickoff_v2.md` | 532 | "# ARIA — Reprise sprint 6 (v2)" daté 7 mai 2026. Mentionne explicitement "tag `sprint-5` local non pushé", "travaux hors-workflow réalisés sur l'embedder", "taxonomie complétée en V2". |

→ Tous des livrables sprint 6 de la session courante. À commit sur la branche actuelle.

#### `scripts/` nouveaux

- `scripts/bench_cpu.py` (mtime 7 mai 16:44) — benchmark sentence-transformers sur CPU (4 modèles testés : mpnet, bge-m3, multilingual-e5-small, paraphrase-MiniLM). `torch.set_num_threads(18)`. **Lié au travail embedder hors-workflow.**
- `scripts/test_onnx.py` (mtime 7 mai 16:47) — test ONNX du modèle `yilunzhang/all-mpnet-base-v2-onnx` avec ORTModelForFeatureExtraction + mean pooling. **Lié au travail embedder hors-workflow.**
- `scripts/test_onnx_embedder.py` (mtime 7 mai 17:09) — test que `Embedder(config.EMBEDDING_MODEL)` fonctionne en mode ONNX (le fichier ouvert dans l'IDE actuellement). **Lié au travail embedder hors-workflow.**
- `scripts/count_memory_by_wing.py` (mtime 2 mai 11:26) — outil diag répartition mémoire par wing. Daté du sprint 4 (mtime). **Pas lié à l'embedder.**

#### `docs/sprint4/`

- `docs/sprint4/audit_memory_layer.md` (19 186 o, mtime 2 mai 12:28)
- `docs/sprint4/decisions_sprint4.md` (4 867 o, mtime 2 mai 12:38)

Documents sprint 4 non commités. Pourraient être livrables d'archive du sprint 4 oubliés. À commit sur la branche actuelle.

### Présence éventuelle de secrets

`test_deepseek_tools.py` lit `DEEPSEEK_API_KEY` depuis le `.env` à la racine — pas de clé en dur. Les scripts `bin/ask-deepseek.py` et `bin/write-deepseek.py` font de même via `dotenv`. **Aucun fichier non suivi ne semble contenir de secret en clair**, mais `.env` (probablement à la racine) doit déjà être listé dans `.gitignore` (à vérifier au moment du commit).

---

## Section 4 — Fichiers supprimés (D)

Aucun fichier en statut `D` (deleted) dans `git status`. Section vide.

---

## Section 5 — Synthèse pour arbitrage

### Tableau croisé

| Catégorie | Nb fichiers M | Nb fichiers ?? |
|---|---|---|
| travail embedder hors-workflow | 3 (`config.py`, `embedding/embedder.py`, `embedding/embedding_contract.py`) | 3 (`scripts/bench_cpu.py`, `scripts/test_onnx.py`, `scripts/test_onnx_embedder.py`) |
| livrables sprint 5/6 non commités (doc, audit, oubli) | 1 (`tests/execution/test_llm_execution_router.py` — oubli mise à jour test post-T8) | 6 (`docs/sprint6/*.md` x4, `docs/sprint4/*.md` x2) |
| artefacts à supprimer (zip, .bak, fichiers temp) | 1 (`core/kernel.py.bak` — déjà suivi mais à expurger) | 1 (`aria-sprint-3.1.zip`) |
| **modifs CRLF parasites (rien à archiver, à reverter)** | **14** | — |
| docs projet (CLAUDE.md, context.md) — modifs sémantiques | 2 (`CLAUDE.md`, `context.md`) | — |
| outils déléguation DeepSeek | — | 2 (`bin/`, `test_deepseek_tools.py`) |
| outils diagnostic mémoire | — | 1 (`scripts/count_memory_by_wing.py`) |
| **TOTAL** | **20** | **12** ( = 13 entrées car `bin/` et `docs/sprint4/` sont des dirs comptant chacun pour 1 entrée `??`) |

### Observations clés pour arbitrage

1. **Le bug "20 fichiers modifiés" est en réalité 6 vraies modifs + 14 conversions LF→CRLF**. Les 14 CRLF doivent être traités séparément (probablement `git checkout --` une fois les vraies modifs archivées, ou setup `.gitattributes`). C'est un parasite, pas du travail.

2. **Le travail embedder hors-workflow est précis et limité** : `config.py` (1 ligne EMBEDDING_MODEL + 5 lignes deepseek api key), `embedding/embedder.py` (refactor ONNX), `embedding/embedding_contract.py` (1 commentaire), `scripts/{bench_cpu,test_onnx,test_onnx_embedder}.py`. Total ≈ 6 fichiers cohérents. La modif `deepseek_api_key` dans `config.py` est probablement à séparer car liée aux outils `bin/`, pas à l'embedder ONNX.

3. **`tests/execution/test_llm_execution_router.py` est un oubli du sprint 5** (rename `store_interaction` → `write_interaction` non propagé au test alors que les commits T4-T8 ont migré le code). À traiter à part : commit branche courante avant le push sprint 5, sinon le test plante.

4. **`docs/sprint6/*.md` (4 fichiers, dont le kickoff v2)** sont tous datés du jour (2026-05-07) et constituent les livrables de la session courante. À commit sur la branche actuelle avant tout push/renommage.

5. **`docs/sprint4/` (2 fichiers, mtime 2 mai)** sont d'anciens livrables non commités. Pas critique, mais sale. À commit sur la branche actuelle.

6. **`core/kernel.py.bak`** est suivi par git mais devrait être supprimé : c'est un `.bak`, et en plus il diverge fortement de `core/kernel.py`. Décision Nico requise (suppression `git rm`).

7. **`aria-sprint-3.1.zip`** contient des données utilisateur (`chroma_db/`). À supprimer du disque, surtout pas commit. Le contenu code est déjà couvert par le tag git `sprint-3.1`.

8. **`bin/` et `test_deepseek_tools.py`** sont des outils déjà documentés dans `CLAUDE.md` mais référencés sous `~/.local/bin/`. Décision : les commit dans le repo (et adapter `CLAUDE.md` ?) ou les `.gitignore` (et garder la copie `~/.local/bin` comme source) ? Arbitrage Nico.

9. **`scripts/count_memory_by_wing.py`** : outil diagnostic propre, daté du sprint 4. Cohérent avec les autres scripts `scripts/*.py` déjà suivis. Commit branche courante.

### Plan suggéré (à valider en T-Z2-B)

1. Commit livrables sprint 4/5/6 sur la branche courante : `docs/sprint4/*.md`, `docs/sprint6/*.md`, `tests/execution/test_llm_execution_router.py`, `scripts/count_memory_by_wing.py`. (1 commit)
2. Décider du sort de `bin/` et `test_deepseek_tools.py`. (commit séparé ou .gitignore)
3. Décider du sort de `aria-sprint-3.1.zip` (suppression) et `core/kernel.py.bak` (`git rm`).
4. Reverter les 14 CRLF parasites : `git checkout -- <les 14 fichiers>`. Setup `.gitattributes` si besoin.
5. Archiver le travail embedder restant (3 modifs + 3 scripts) sur `archive/embedder-parallel-work` comme prévu.
6. Reprendre la séquence T-Z2 originale (push sprint 5, ff main, etc.) sur un working tree propre.
