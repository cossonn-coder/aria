# Runbook T-Mempalace-Live — Migration palace prod sous fork MemPalace

**Sprint 7 / phase 2.** Migration du palace ARIA de
`all-MiniLM-L6-v2` (dim 384) vers
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
(dim 768) sous le fork MemPalace `feat/configurable-embedder`
(commit `b8caf32`), avec écriture du marker side-channel
`.mempalace-embedder.json` que le fork consomme à l'ouverture.

**Lecture séquentielle obligatoire**. Chaque section a un critère
de succès binaire et une conduite en cas d'échec (`STOP` / `RETRY`
/ `ROLLBACK`). Tags :

- `[GÉNÉRIQUE]` — section exécutable telle quelle aussi bien sur
  une copie pré-prod (tour T-Mempalace-Preprod) que sur le palace
  prod.
- `[PROD]` — section spécifique au run live prod (touche au
  service systemd, à `config.py`, au client Telegram).

Source : `all-MiniLM-L6-v2` (dim 384).
Cible : `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
(dim 768).
Palace prod : `~/.mempalace/palace/`.

---

## Section 0 — [GÉNÉRIQUE] Vérification outils

Avant toute autre commande, vérifier la présence des binaires
système requis par le runbook. Couvre la **dette #14** sprint 6
(le runbook précédent ne vérifiait pas ses propres outils).

```bash
command -v rsync   && \
command -v tar     && \
command -v python3 && \
command -v sqlite3
```

**Attendu** : quatre lignes, chacune affichant un chemin absolu.

**Critère de succès** : exit code 0 sur les quatre `command -v`,
soit toutes les lignes affichées.

**En cas d'échec** : si un seul outil manque → **STOP**. Installer
le manquant via `sudo apt install <pkg>` (rsync, tar, sqlite3
sont dans les paquets éponymes Debian). Ne pas tenter d'enchaîner
sur les sections suivantes.

---

## Section 1 — [GÉNÉRIQUE] Pré-vol environnement

Vérifie que le venv ARIA pointe bien sur le fork MemPalace, que
sentence-transformers est importable, et que l'état git est
propre. Couvre la **dette #15** sprint 6 : par défaut, tout
check pré-vol échoué = **STOP**, ne pas improviser.

```bash
cd ~/Nextcloud/projects/aria

# 1. Vérification fork MemPalace actif dans le venv
./venv/bin/python -c "import mempalace; print(mempalace.__file__)"
# Attendu : un chemin contenant 'mempalace-fork'
#           (ex: /home/nico/Nextcloud/projects/mempalace-fork/mempalace/__init__.py)
# Pattern INTERDIT : chemin sous venv/lib/.../site-packages/mempalace/
#
# Justification : `pip show mempalace` retourne une Location
# site-packages même quand le package est installé en editable
# (comportement trompeur pip 25, cf. docs/sprint7/install_notes.md).
# Seul `mempalace.__file__` est fiable.

# 2. Vérification sentence-transformers importable (import seul, pas de chargement de modèle)
./venv/bin/python -c "from sentence_transformers import SentenceTransformer; print('import OK')"
# Attendu : 'import OK'

# 3. État git ARIA
git rev-parse --abbrev-ref HEAD
# Attendu : feat/sprint6-embedder-audit

git status --porcelain | grep -v '^??' || true
# Attendu : sortie vide. Les fichiers untracked ('??')
# sont ignorés (ils sont autorisés à ce stade).
```

**Critère de succès** : (1) chemin mempalace-fork affiché, (2)
`import OK` affiché, (3) branche correcte, (4) `git status
--porcelain | grep -v '^??'` vide (untracked tolérés).

**En cas d'échec** :
- (1) chemin sous site-packages → fork pas actif. **STOP**.
  Cf. `docs/sprint7/install_notes.md` pour réinstaller en editable.
- (2) ImportError → **STOP**. `./venv/bin/pip install
  sentence-transformers` puis relancer la section.
- (3) mauvaise branche → **STOP**. `git checkout
  feat/sprint6-embedder-audit`.
- (4) working tree sale → **STOP**. Stash ou commit les
  modifications en cours avant de poursuivre.

---

## Section 2 — [PROD] Arrêt service ARIA

Le palace prod doit être fermé (pas de writer concurrent) pendant
la migration. Le service systemd ARIA tient le seul process qui
écrit dans `~/.mempalace/palace/` en prod.

```bash
sudo systemctl stop aria.service
systemctl is-active aria.service
# Attendu : inactive

sudo journalctl -u aria.service -n 5 --no-pager
# Vérifier shutdown propre (pas de Traceback final)
```

**Critère de succès** : `systemctl is-active` retourne `inactive`,
les 5 dernières lignes ne contiennent pas de stacktrace.

**En cas d'échec** : si `is-active` retourne `failed` ou
`activating`, attendre 5 s puis recontrôler. Si toujours pas
`inactive` après 30 s → **STOP**, investiguer
(`sudo systemctl status aria.service` complet).

---

## Section 3 — [GÉNÉRIQUE] Backup du palace

Sauvegarde rsync horodatée avant toute écriture. Le script
`migrate_embedder.py` crée son propre snapshot tar.gz à l'étape A,
mais on garde une seconde copie de niveau filesystem en filet
indépendant (au cas où le snapshot du script serait corrompu).

```bash
TS=$(date +%Y%m%dT%H%M%S)
rsync -a ~/.mempalace/palace/ \
        ~/.mempalace/palace.backup-pre-live-${TS}/

du -sh ~/.mempalace/palace
du -sh ~/.mempalace/palace.backup-pre-live-${TS}
# Attendu : tailles comparables (à quelques octets près)

echo "Backup créé : ~/.mempalace/palace.backup-pre-live-${TS}"
```

**Critère de succès** : exit code 0 du `rsync`, les deux `du -sh`
affichent des tailles de même ordre de grandeur.

**En cas d'échec** : `rsync` retourne non-zéro → **STOP**.
Probable problème de droits ou de place disque (`df -h
~/.mempalace`).

> Conserver la variable `${TS}` ou noter à la main la valeur du
> timestamp pour la section R.

---

## Section 4 — [GÉNÉRIQUE] Migration via migrate_embedder.py

Lance le script de migration (commit `bd77233` ou plus récent).
Le script enchaîne les étapes A→G :

- **A** — snapshot tar.gz horodaté (filet de rollback du script).
- **B** — inspection (count, dim 384).
- **C** — vérification idempotence via `.embedder-migration-marker`.
- **D** — re-encoding des documents avec le modèle cible (mpnet).
- **E** — réécriture de la collection ChromaDB.
- **F** — validation post-migration (count préservé, dim 768).
- **G** — écriture des **deux** markers : `.embedder-migration-marker`
  (hash sha256 historique ARIA) **et** `.mempalace-embedder.json`
  (marker side-channel consommé par le fork MemPalace à
  l'ouverture). Le second est le **livrable critique du sprint 7**
  — sans lui, le fork retombe sur l'ONNX MiniLM par défaut et
  plante sur la première query (dim mismatch 768 vs 384).

Le modèle cible est passé explicitement via `--to-model` plutôt
que par le défaut du script (le défaut est défini ligne 739 de
`scripts/migrate_embedder.py` à
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`,
mais on l'explicite ici pour que le runbook soit autoporteur —
un lecteur ne doit pas avoir à ouvrir le script pour savoir ce
qui est migré).

```bash
cd ~/Nextcloud/projects/aria

./venv/bin/python scripts/migrate_embedder.py \
    --palace-path ~/.mempalace/palace \
    --to-model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
    2>&1 | tee /tmp/migrate_live_$(date +%Y%m%dT%H%M%S).log
```

**Patterns à grep dans le log** :

```bash
grep -E "ÉTAPE [A-G]|✓ Migration réussie|marker .mempalace-embedder.json" \
     /tmp/migrate_live_*.log | tail -20
```

**Attendu dans le log** :

- En-tête `from-model : all-MiniLM-L6-v2 (dim=384)` et
  `to-model : sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (dim=768)`.
- `── ÉTAPE A : Snapshot du palace ──` puis
  `Snapshot créé : ...mempalace_drawers_backup_*.tar.gz`.
- `── ÉTAPE B : Inspection ...` avec `Nombre d'entrées : N`
  (noter N) et `Dimension actuelle des vecteurs : 384`.
- `── ÉTAPE C : Vérification idempotence (marker) ──`
  → `Aucun marker trouvé — première migration.` (sur un
  palace vierge MiniLM). Si message `Migration déjà effectuée
  vers '...' (hash SHA256 correspond...)` : le palace a déjà
  été migré, sortie propre code 0, passer à la section 5.
- `── ÉTAPE D : Re-encoding avec '...mpnet-base-v2' ──`,
  `Modèle chargé en X.Xs`, puis `Encodage terminé : N
  phrases en X.Xs → ~Y phrases/s`.
- `── ÉTAPE E : Réécriture ChromaDB ──` puis `Insertion
  terminée : N entrées`.
- `── ÉTAPE F : Validation post-migration ──` puis
  `✓ Count OK : N entrées.` et `✓ Dimension OK : 768.`.
- `── ÉTAPE G : Écriture du marker d'idempotence ──` puis
  **les deux lignes** :
  - `Marker écrit : .../palace/.embedder-migration-marker`
  - `marker .mempalace-embedder.json écrit (model=sentence-transformers/paraphrase-multilingual-mpnet-base-v2)`
- Ligne finale : `✓ Migration réussie : 'all-MiniLM-L6-v2' →
  'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
  | N entrées | dim 384 → 768`.
- Exit code du script : 0.

**Critère de succès** : exit code 0 ET ligne finale `✓ Migration
réussie` ET ligne `marker .mempalace-embedder.json écrit` présente
dans le log.

**En cas d'échec** :
- Exit code non-zéro avant l'étape E → palace prod intact (le
  script n'a rien réécrit). **STOP**, investiguer le log.
- Exit code non-zéro entre étapes E et F → le script déclenche
  son rollback automatique. Chercher dans le log
  `[ROLLBACK] Palace restauré depuis : ...tar.gz` :
  - si présent → palace revenu pré-migration côté script,
    déclencher quand même la **section R** (le service est
    toujours arrêté, rétablir l'état complet).
  - si absent → rollback du script échoué. **STOP** total,
    conserver le log, le tar.gz du script et le backup rsync de
    la section 3. Restauration manuelle via le backup rsync.

---

## Section 5 — [GÉNÉRIQUE] Vérification markers post-migration

Vérifie côte à côte la présence et le contenu des deux markers
écrits à l'étape G. Le `.mempalace-embedder.json` est la
nouveauté sprint 7 — son absence ou un `model` incorrect dedans
signifie que la section 4 a échoué silencieusement et que le fork
ne pourra pas réinstancier la bonne EF à l'ouverture.

```bash
# Marker fork MemPalace (le marker critique sprint 7)
cat ~/.mempalace/palace/.mempalace-embedder.json
# Attendu (JSON sur une ligne, lisible) :
# {"model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "version": 1}

# Marker historique ARIA (hash sha256 du modèle cible)
cat ~/.mempalace/palace/.embedder-migration-marker
# Attendu : une chaîne hex de 64 caractères, sans espace ni
#           saut de ligne en fin.
```

**Vérification programmatique du marker fork** :

```bash
./venv/bin/python -c "
import json, pathlib
p = pathlib.Path.home() / '.mempalace/palace/.mempalace-embedder.json'
data = json.loads(p.read_text())
expected = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
assert data['model'] == expected, f'mismatch: {data!r}'
assert data['version'] == 1, f'version: {data!r}'
print('marker fork OK :', data)
"
```

**Critère de succès** : les deux fichiers existent, le marker
fork contient exactement
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
en valeur de `model`, le marker historique contient une chaîne
hex de 64 caractères.

**En cas d'échec** :
- Marker fork absent ou `model` ≠ valeur attendue → la
  section 4 n'a pas écrit le marker (script trop ancien ?
  vérifier `git log --oneline scripts/migrate_embedder.py | head -3`,
  doit inclure `bd77233` ou successeur). **En prod : déclencher
  section R immédiatement.** En pré-prod : **STOP**, ne pas
  poursuivre.
- Marker historique absent → étape G interrompue. Même conduite
  que ci-dessus.

---

## Section 6 — [GÉNÉRIQUE] Smoke test ouverture palace + query

Ouvre le palace migré via l'API MemPalace fork et exécute une
`coll.query()` minimale. Valide deux choses :

1. Le palace s'ouvre **sans crash**, sans quarantine de segment
   HNSW (le crash sprint 6 quarantained 3 segments, cf.
   `docs/sprint7/context_sprint_7_T-Mempalace-Live_kickoff.md`).
2. L'embedding function effectivement réinstanciée par le fork
   est bien **SentenceTransformer-based** (mpnet), PAS l'ONNX
   MiniLM par défaut.

L'ouverture passe par l'API publique du fork
(`mempalace.palace.get_collection`, cf. `mempalace/palace.py:59-73`),
PAS par `chromadb.PersistentClient` directement. C'est ce passage
par le fork qui déclenche la lecture du marker
`.mempalace-embedder.json` côté `ChromaBackend._resolve_embedding_function`
(`mempalace/backends/chroma.py:1155-1185`). Ouvrir avec chromadb
nu court-circuite ce hook et invalide le smoke test (la EF
retombe sur l'ONNX MiniLM par défaut, donc faux positif ou crash
dim mismatch selon le comportement lazy).

Le heredoc commence par une garde redondante avec la Section 1
check 1 (vérification que `mempalace.__file__` contient
`mempalace-fork`), pour éviter un faux positif si la Section 1 a
été sautée ou si l'install editable a été perturbée entre-temps.

```bash
./venv/bin/python <<'EOF'
"""Smoke test palace post-migration — ouverture + query minimale.

Ouvre le palace via l'API fork (mempalace.palace.get_collection)
qui consomme le marker .mempalace-embedder.json. Court-circuiter
ce point d'entrée invalide le test.
"""
from mempalace.palace import get_collection

# Garde "fork actif" — redondant avec Section 1 check 1, mais
# ferme le trou si un opérateur saute la Section 1 ou si pip a
# réinstallé mempalace upstream entre-temps.
import mempalace
assert "mempalace-fork" in mempalace.__file__, (
    f"fork MemPalace non actif (mempalace.__file__ = "
    f"{mempalace.__file__}). Cf. Section 1 check 1."
)

PALACE_PATH = "/home/nico/.mempalace/palace"
COLLECTION = "mempalace_drawers"

# 1. Ouverture via l'API publique du fork (consomme le marker)
col = get_collection(PALACE_PATH, collection_name=COLLECTION, create=False)

# 2. Inspection basique — count et dim
count = col.count()
got = col.get(limit=1, include=["embeddings"])
embeddings = got.embeddings
dim = len(embeddings[0]) if embeddings else None
print(f"[smoke] count={count} dim={dim}")
assert dim == 768, f"dimension attendue 768, vu {dim}"

# 3. Query minimale (côté lecture, déclenche la EF)
res = col.query(query_texts=["Bonjour"], n_results=3)
top_ids = res.ids[0] if res.ids else []
print(f"[smoke] query 'Bonjour' top_ids={top_ids}")
assert len(top_ids) > 0, "query a retourné zéro résultat"

# 4. Vérification du backend EF effectivement chargé.
#    ChromaCollection (wrapper du fork) expose l'objet ChromaDB
#    sous-jacent via _collection ; on lit son _embedding_function.
ef = col._collection._embedding_function
ef_repr = repr(ef)
print(f"[smoke] embedding_function: {ef_repr}")

# Pattern ATTENDU : la classe doit contenir SentenceTransformer
# (le fork écrit SentenceTransformerEmbeddingFunction quand le
#  marker .mempalace-embedder.json est consommé correctement).
assert "SentenceTransformer" in ef_repr, (
    f"backend EF inattendu (attendu SentenceTransformer-based) : {ef_repr}"
)
print("[smoke] OK — backend sentence-transformers actif")
EOF
```

**Pattern INTERDIT en sortie** : toute mention de
`providers=['CPUExecutionProvider']`, `OnnxRuntime`,
`ONNXMiniLM`, ou tout repr qui ne contient pas
`SentenceTransformer`. C'est le signe que le fork est retombé
sur le default ONNX MiniLM faute d'avoir lu (ou compris) le
marker `.mempalace-embedder.json`.

**Critère de succès** : exit code 0 du heredoc, lignes
`[smoke] count=N dim=768`, `[smoke] query 'Bonjour' top_ids=[...]`
non vide, `[smoke] OK — backend sentence-transformers actif`.

**En cas d'échec** :
- AssertionError sur le check "mempalace-fork" en tête du
  heredoc → le venv ARIA ne pointe plus le fork MemPalace.
  Cause : install editable cassée, ou Section 1 sautée, ou
  réinstallation pip parasite. **STOP inconditionnel** (prod
  comme pré-prod) : ne pas tenter la migration, retourner à la
  Section 1 et au document `docs/sprint7/install_notes.md` pour
  rétablir le fork en editable.
- Exception levée par `get_collection()` AVANT d'atteindre les
  assertions dim/backend (typiquement
  `mempalace.backends.base.PalaceNotFoundError`,
  `chromadb.errors.NotFoundError`, ou une erreur SQLite/OSError
  remontée par l'init de `PersistentClient`) → le palace n'a
  probablement pas été corrompu par la section 4 (qui écrit le
  marker en dernier, étape G), mais l'ouverture côté fork
  échoue en amont. Causes les plus probables : répertoire
  `~/.mempalace/palace/` disparu ou déplacé entre sections 3 et
  6, collection `mempalace_drawers` introuvable (palace
  fraîchement recréé sans collection), corruption SQLite. Note :
  un marker `.mempalace-embedder.json` cassé ou pointant un
  `model` inconnu ne raise PAS ici — le fork swallow ces
  erreurs (`chroma.py:_read_embedder_marker` catch `OSError`/`ValueError`,
  `chroma.py:_resolve_embedding_function` catch `Exception`) et
  retombe sur l'ONNX MiniLM par défaut, ce qui surface à
  l'AssertionError dim/backend ci-dessous. **En prod : section R
  immédiatement.** Pré-prod : **STOP**, inspecter
  `ls -la ~/.mempalace/palace/`,
  `cat ~/.mempalace/palace/.mempalace-embedder.json` et la
  stacktrace complète.
- AssertionError sur la dim → la section 4 a planté
  silencieusement. **En prod : section R immédiatement.** Pré-prod :
  **STOP**.
- AssertionError sur le backend (ONNX au lieu de
  SentenceTransformer) → marker non consommé par le fork. C'est
  l'échec critique anticipé. **En prod : section R
  immédiatement.** Pré-prod : **STOP**, vérifier
  `mempalace.__file__` (section 1, check 1) et la version du
  fork.
- Crash chromadb / segment HNSW quarantained dans la stacktrace
  → palace corrompu, le backup rsync de la section 3 est le
  filet. **En prod : section R immédiatement.**

---

## Section 7 — [PROD] Bascule config.py EMBEDDING_MODEL

Une fois les sections 4–6 vertes, modifier la valeur de
`EMBEDDING_MODEL` dans `config.py:35` pour que le runtime ARIA
charge le bon modèle au démarrage. La migration palace seule ne
suffit pas — sans ce flip, ARIA va instancier MiniLM au boot et
planter sur la première interaction (dim 384 vs 768).

**Diff à appliquer** :

```diff
diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -32,7 +32,7 @@ class Config:
     gemini_model: str = "gemini-2.0-flash"
     mistral_model: str = "mistral-small-latest"
     sambanova_model: str = "Meta-Llama-3.3-70B-Instruct"
-    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
+    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
```

Édition manuelle (ouvrir `config.py`, remplacer la chaîne), puis
contrôle :

```bash
cd ~/Nextcloud/projects/aria
git diff config.py
# Attendu : exactement le diff ci-dessus, rien d'autre.

./venv/bin/python -c "from config import config; print(config.EMBEDDING_MODEL)"
# Attendu : sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

Commit local (pas de push à ce stade — Nico arbitrera le push en
clôture sprint 7) :

```bash
git add config.py
git commit -m "feat(sprint7): T-Mempalace-Live bascule EMBEDDING_MODEL → mpnet-multilingual"
git log --oneline -3
```

**Message de commit suggéré (alternative plus détaillée)** :

```
feat(sprint7): T-Mempalace-Live bascule EMBEDDING_MODEL → mpnet-multilingual

Active paraphrase-multilingual-mpnet-base-v2 (dim 768) en prod sous
fork MemPalace, après migration du palace via
scripts/migrate_embedder.py. Le marker .mempalace-embedder.json
posé à l'étape G permet au fork de réinstancier
SentenceTransformerEmbeddingFunction à l'ouverture (vs le default
ONNX MiniLM 384 qui plantait sprint 6). Validation : runbook
docs/sprint7/runbook_t_mempalace_live.md sections 4-10.
```

**Critère de succès** : `git diff config.py` montre une seule
ligne modifiée, sortie Python affiche la nouvelle valeur, le
commit est créé en local.

**En cas d'échec** : diff inattendu (autres lignes touchées) →
**STOP**, ne pas commiter, restaurer (`git checkout config.py`) et
recommencer proprement.

---

## Section 8 — [PROD] Redémarrage service ARIA

```bash
sudo systemctl start aria.service
sleep 3
systemctl is-active aria.service
# Attendu : active
```

**Critère de succès** : `is-active` retourne `active`.

**En cas d'échec** : `failed` ou `activating` après 10 s →
**STOP**, consulter `sudo systemctl status aria.service` et la
section 9 pour le détail des logs. Si stack au boot →
**section R**.

---

## Section 9 — [PROD] Vérification log init embedding

Vérifie dans les premières lignes de boot que le runtime a bien
chargé l'EF SentenceTransformer-based pour mpnet (et **pas**
l'ONNX MiniLM par défaut). C'est le signal d'aboutissement de la
chaîne marker→fork→config bascule. Le pattern ONNX dans ce log
était le signal d'échec sprint 6.

```bash
sudo journalctl -u aria.service -n 200 --no-pager | grep -iE "embed|sentence|onnx|provider"
```

**Pattern ATTENDU** (au moins une ligne mentionnant chacun des
deux éléments suivants) :

- la chaîne `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
  (le nom du modèle effectivement chargé).
- la mention `SentenceTransformerEmbeddingFunction` ou
  équivalent (`SentenceTransformer` dans un nom de classe ou
  une ligne de chargement de modèle).

**Pattern INTERDIT** (au moins une ligne contenant un des
éléments suivants) :

- `providers=['CPUExecutionProvider']` (signature ONNX
  CPUExecutionProvider).
- `OnnxRuntime`, `onnxruntime`.
- Toute mention de `all-MiniLM-L6-v2` au démarrage post-bascule
  (l'ancien modèle ne doit plus être chargé du tout).

**Critère de succès** : au moins un match sur le pattern
ATTENDU, zéro match sur le pattern INTERDIT.

**En cas d'échec** :
- Match sur pattern INTERDIT → le marker n'a pas été pris en
  compte par le fork à l'ouverture, ou la bascule `config.py`
  n'est pas effective. **Déclencher section R immédiatement.**
- Pattern ATTENDU absent ET pattern INTERDIT absent → log trop
  court, élargir : `sudo journalctl -u aria.service -n 500
  --no-pager | grep -iE "embed|sentence|onnx"`. Si toujours
  rien d'embedding-related, le service ne charge peut-être pas
  encore l'EF (lazy). Passer à la section 10 ; le premier
  message Telegram déclenchera le chargement et permettra de
  trancher.

---

## Section 10 — [PROD] Fumée Telegram

Tests bout-en-bout via le client Telegram. À exécuter
manuellement par Nico, un message à la fois, en laissant tourner
en parallèle dans un terminal séparé :

```bash
sudo journalctl -u aria.service -f -o cat
```

Surveiller en direct l'absence de `ERROR`, `Traceback`,
`dim mismatch`, et le pattern INTERDIT de la section 9.

| # | Prompt exact à envoyer | Cas couvert | Critère de succès |
|---|---|---|---|
| a | `Salut Aria` | Salutation courte — embedding no-op, retrieval léger, soul.md respecté. | Réponse cohérente, conversationnelle. Aucun stacktrace au log. Latence subjective acceptable (< 5 s côté ressenti utilisateur). |
| b | `Note que je préfère le café au thé` | Écriture mémoire neutre. Vérifie que l'écriture côté ARIA fonctionne avec les vecteurs 768 et que le drawer est bien créé. | Critère assoupli (cf. note ci-dessous) : (i) ACK côté ARIA (réponse confirmant la prise en note) ; (ii) aucun stacktrace embedding-related au log ; (iii) vérification programmatique : count `mempalace_drawers` augmenté d'au moins 1 vs avant le message. Si (i) + (ii) mais count inchangé → **borderline**, arbitrage Nico, ne pas déclencher section R automatiquement. |
| c | `Donne-moi une idée de recette rapide` | Requête culinaire, déclenche un retrieval substantiel. Vérifie que `coll.query()` ne crash pas sous la charge réelle d'un dialogue (vs le smoke test minimal de section 6). | Réponse culinaire cohérente. Aucun stacktrace au log. Retrieval ne renvoie pas vide. |
| d | `Planifier des vacances en Normandie` | **Test critique — apport sprint** : valide la fin du bug #18 retrieval français. Sous MiniLM 384, ce prompt drift linguistiquement et oracle voyage retombe rang 53/63. Sous mpnet 768, oracle attendu rang 1 (cf. bench sprint 6 post-M2). | Le retrieval renvoie des drawers liés au voyage / à la Normandie / à des thématiques planning si présents dans le palace. **Critère de succès minimal** : ne renvoie PAS vide pour cause de drift français/anglais, ne renvoie PAS des drawers culinaires/jardin hors-sujet en top-1. Réponse cohérente côté agent. |

**Note critère (b)** : ARIA écrit toutes ses wings logiques
(aria_episodic, aria_semantic, aria_classifier) dans une seule
collection ChromaDB `mempalace_drawers` — les "wings" sont des
champs metadata, pas des collections séparées (cf.
`memory/writer.py` : tous les `write_*` passent par
`mempalace.palace.get_collection(config.mempalace_path)`, qui
résout la collection par défaut `mempalace_drawers`). La
vérification programmatique du count se fait donc bien sur
cette unique collection. Le critère est néanmoins assoupli en
borderline si l'ACK + l'absence de stacktrace embedding-related
sont présents : la dette #17 (couche sémantique non câblée par
le pipeline normal) peut faire que certains messages
n'entraînent aucune écriture sans pour autant signaler une
régression embedding.

Vérification programmatique du count (à exécuter avant ET après
le message `b`) :

```bash
./venv/bin/python -c "
from mempalace.palace import get_collection
col = get_collection(
    '/home/nico/.mempalace/palace',
    collection_name='mempalace_drawers',
    create=False,
)
print(col.count())
"
```

**Critère de succès global section 10** : 4/4 ou 3/4 messages
conformes avec borderline isolé sur (a), (b) ou (c). Le cas (d)
ne tolère pas de borderline — c'est l'aboutissement fonctionnel
du sprint.

**En cas d'échec** :
- (d) retourne du culinaire/jardin/etc. en top-1, ou retrieval
  vide → bug #18 pas résolu, ou marker non consommé.
  **Déclencher section R.**
- (a), (b) ou (c) : stacktrace au log → noter, déclencher
  **section R** si l'erreur est embedding-related (dim
  mismatch, EF introuvable). Sinon (erreur applicative non liée
  à l'embedding), arbitrage Nico nécessaire.

---

## Section R — [PROD] Procédure de rollback

**Conditions de déclenchement (au moins une suffit)** :

- Section 5 : marker `.mempalace-embedder.json` absent OU
  `model` ≠ valeur attendue OU marker historique absent.
- Section 6 : palace ne s'ouvre pas, `coll.query()` crash, ou
  backend EF non SentenceTransformer (pattern ONNX en sortie).
- Section 9 : pattern ONNX (`CPUExecutionProvider`,
  `OnnxRuntime`) dans `journalctl`.
- Section 10 (a/b/c) : erreur embedding-related (dim mismatch,
  EF introuvable) dans le log.
- Section 10 (d) : retrieval français manifestement cassé
  (top-1 hors-sujet ou résultats vides pour drift linguistique).

**Procédure ordonnée** :

```bash
# 1. Arrêt service
sudo systemctl stop aria.service
systemctl is-active aria.service
# Attendu : inactive

# 2. Suppression du palace migré cassé
rm -rf ~/.mempalace/palace

# 3. Restauration depuis le backup rsync de la section 3
#    (sélectionner le bon TS à la main — celui noté en section 3)
ls -lt ~/.mempalace/ | grep palace.backup-pre-live-
#    Identifier le backup-pre-live-<TS> à restaurer, puis :
rsync -a ~/.mempalace/palace.backup-pre-live-<TS>/ \
        ~/.mempalace/palace/

# Vérification visuelle de la restauration
ls -la ~/.mempalace/palace/
#    Le marker .mempalace-embedder.json doit être absent
#    (le palace pré-migration n'en avait pas).
cat ~/.mempalace/palace/.mempalace-embedder.json 2>/dev/null \
    || echo "marker fork absent — OK pour un palace pré-migration"

# 4. Annulation de la bascule config.py
cd ~/Nextcloud/projects/aria
git checkout config.py
./venv/bin/python -c "from config import config; print(config.EMBEDDING_MODEL)"
# Attendu : all-MiniLM-L6-v2
#
# Si le commit de bascule a déjà été créé (section 7 atteinte),
# le `git checkout` n'annule pas le commit. Choisir :
#   - revert (crée un commit de revert) :
#       git revert --no-edit HEAD
#   - reset (supprime le commit local, à condition qu'il n'ait
#     PAS été poussé — ce qui est le cas par défaut, le runbook
#     n'autorise pas de push) :
#       git reset --hard HEAD~1

# 5. Redémarrage service
sudo systemctl start aria.service
sleep 3
systemctl is-active aria.service
# Attendu : active

# 6. Vérification retour à MiniLM 384
sudo journalctl -u aria.service -n 100 --no-pager \
    | grep -iE "embed|sentence|onnx|MiniLM"
# Attendu : mention de all-MiniLM-L6-v2 ou de l'ONNX
#           CPUExecutionProvider (signe que le fork est revenu
#           sur son default sans marker). Pas de mpnet.
./venv/bin/python -c "
import chromadb
c = chromadb.PersistentClient('/home/nico/.mempalace/palace')
col = c.get_collection('mempalace_drawers')
peek = col.peek(1)
print('count:', col.count(), '| dim:', len(peek['embeddings'][0]))
"
# Attendu : count cohérent avec la valeur d'avant migration,
#           dim = 384.
```

**À conserver impérativement** pour post-mortem (ne PAS supprimer
en fin de rollback) :

- Le log `/tmp/migrate_live_*.log` de la section 4.
- Le snapshot tar.gz créé par le script à l'étape A
  (`~/.mempalace/mempalace_drawers_backup_*.tar.gz`).
- Le backup rsync de la section 3
  (`~/.mempalace/palace.backup-pre-live-<TS>`) — au moins une
  copie, idéalement celle qui a servi à la restauration.

**Ne PAS relancer** la migration sans avoir identifié et corrigé
la cause de l'échec. Re-tenter à l'aveugle reproduira l'échec.

---

## Notes finales

- **Nom du service systemd ARIA** : `aria.service`, confirmé via
  le runbook T-Embedder3 sprint 6 (`docs/sprint6/runbook_t_embedder3.md`)
  et `CLAUDE.md`. Si une vérification supplémentaire est
  souhaitée côté machine prod : `systemctl list-units --type=service
  | grep -i aria`.
- **Path `config.py`** : `aria/config.py` est mentionné dans le
  brief, mais le fichier se trouve à la racine
  (`/home/nico/Nextcloud/projects/aria/config.py:35`), confirmé
  via `grep -n EMBEDDING_MODEL config.py`. Le diff de la section 7
  utilise ce chemin racine.
- **Étape G du script** : c'est la fonction `etape_c_write_marker`
  qui est appelée en fin de pipeline (le nom de la fonction est
  hérité du sprint 6, mais elle écrit bien les **deux** markers
  côte à côte, lignes 307–333 de `scripts/migrate_embedder.py`).
- **Hors-scope sprint 7** : reflux des `all-MiniLM-L6-v2` hard-codés
  dans les scripts (`scripts/migrate_embedder.py`,
  `scripts/embedder_bench/_models.py`) et les docs sprint 6 — ce
  sont des références historiques ou des défauts du script de
  migration, à conserver.
