# ARIA — Kickoff session T-Mempalace-Live (run live prod)

**Date** : 2026-05-14
**État sprint 7** : phase 1 close (patch fork + bascule venv ARIA),
phase 2 ouverte (run live prod, migration palace, bascule
EMBEDDING_MODEL, fumée Telegram).
**Session précédente** : clôture sprint 6 (tag sprint-6 + merge
main), patch MemPalace fork (commit b8caf32), bascule venv ARIA
sur le fork, patch scripts/migrate_embedder.py pour écrire le
marker .mempalace-embedder.json. Tous les tests verts.

---

## Pourquoi nouvelle session

La session précédente a consommé ~70% de sa fenêtre sur la
trajectoire complète : clôture sprint 6 (3 tours), patch fork
MemPalace (1 tour), bascule venv ARIA + patch script ARIA
(1 tour), commit de clôture (1 tour). Le run live prod exige
une fenêtre de raisonnement claire pour réagir si quelque chose
tourne mal — discipline éprouvée au sprint 6 (T-Embedder3 dans
session dédiée).

---

## Acquis techniques

### Fork MemPalace
- Repo : https://github.com/cossonn-coder/mempalace
- Branche : feat/configurable-embedder
- Commit : b8caf3259021d27c2689928458ac02d5a0defd01
- Base : tag upstream v3.3.5
- Tests upstream : 1730 passed / 1 skipped (1726 baseline + 4 nouveaux)
- API ajoutée :
  - `get_embedding_function(device, model_name)` : factory à deux
    branches. model_name=None → ONNX MiniLM 384 (back-compat).
    model_name="..." → SentenceTransformerEmbeddingFunction.
  - Marker `.mempalace-embedder.json` à la racine du palace
    persiste l'identité du modèle. Lu à toute ouverture pour
    réinstancier la bonne EF.
  - Name-spoofing `name() == "default"` conservé sur les deux
    backends pour compat ChromaDB.

### Venv ARIA
- mempalace installé en editable depuis ~/Nextcloud/projects/mempalace-fork/
- `pip show mempalace` retourne Location site-packages (trompeur,
  pip 25). Vérification réelle : `python -c "import mempalace;
  print(mempalace.__file__)"` doit pointer sur mempalace-fork.
- sentence-transformers 5.4.1, chromadb 1.5.5 disponibles.
- Pytest ARIA : 211 passed sous le fork (zéro régression vs
  pré-bascule).
- Doc de trace : docs/sprint7/install_notes.md (commit bd77233).

### Script migrate_embedder.py
- Patche commit bd77233. Écrit maintenant les deux markers à
  l'étape G (etape_c_write_marker) :
  - `.embedder-migration-marker` (hash sha256, marker historique
    ARIA pour idempotence)
  - `.mempalace-embedder.json` (marker side-channel fork,
    consommé par MemPalace à l'ouverture)
- 3 tests nouveaux verts : writes_marker, dry_run_noop, idempotent.

---

## Découverte stratégique : palace conservé inutilisable

Le palace `~/.mempalace/palace.rollback-failed-20260513T131824/`
(migré 768 conservé fin sprint 6, censé être réutilisé pour
économiser 2'30 d'encodage) **n'est pas récupérable**.

À la première ouverture par le fork patché (étape 5 du tour
T-Mempalace-Install-ARIA), ChromaDB a quarantained 3 segments
HNSW : `b28198b8-...` (labels dim None), `3b1fb30f-...`
(drift sqlite/HNSW 2598s, renommé .drift-20260514-070800),
`d45f5f83-...` (drift sqlite/HNSW 494s, idem). Drift hérité
du crash sprint 6.

**Décision Nico (14 mai)** : on part d'un palace vierge.
Aucune donnée mémoire n'est critique à l'heure actuelle.
T-Mempalace-Live = migration from scratch du palace prod actuel
(MiniLM 384) vers mpnet 768.

Conséquence pour la trajectoire : T-Mempalace-Migrate-Reuse (qui
était priorité 6 du kickoff sprint 7 initial) est annulé. On
exécute directement T-Mempalace-Live.

---

## État git ARIA

- Branche : feat/sprint6-embedder-audit, HEAD bd77233.
- 1 commit local non poussé : bd77233 (à pusher en fin de
  T-Mempalace-Live, en même temps que le commit éventuel de
  bascule config.py).
- main : 07c012d (merge sprint 6, déjà poussé).
- Tag sprint-6 : c30a530 sur 254a86e, poussé.
- Working tree clean.

---

## Plan d'exécution T-Mempalace-Live

Cette session devra rédiger les briefs suivants pour Claude Code.
**Ne pas tout enchaîner dans un seul brief** — chaque phase est un
point de non-retour potentiel et mérite arbitrage architecte.

### Phase 1 : runbook T-Mempalace-Live
Rédiger `docs/sprint7/runbook_t_mempalace_live.md` sur le modèle
du runbook T-Embedder3 sprint 6, avec ajouts :
- Section 0 : vérification outils (rsync, tar, command -v) — dette
  #14 sprint 6.
- Section pré-vol : vérifier mempalace.__file__ pointe bien sur
  le fork, vérifier sentence-transformers importable.
- Section migration : exécuter `scripts/migrate_embedder.py` qui
  écrit maintenant le marker .mempalace-embedder.json.
- Section bascule config.py : `EMBEDDING_MODEL = 
  "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"`.
- Section validation runtime : redémarrage service, vérification
  journalctl pour le log d'embedding init (doit mentionner mpnet
  via sentence-transformers, PAS providers=CPUExecutionProvider
  qui était le signal ONNX MiniLM raté du sprint 6).
- Section fumée Telegram : 4 messages-test (salutation, écriture
  mémoire neutre, requête culinaire, "Planifier des vacances en
  Normandie" pour valider la fin du bug #18 retrieval français).

### Phase 2 : test pré-prod sur copie du palace prod
AVANT toute touche au palace prod, copier le palace actuel,
exécuter migrate_embedder.py sur la copie, ouvrir la copie via
le fork, valider que :
- Le marker .mempalace-embedder.json est écrit.
- La copie ouvre sans crash, sans quarantine HNSW.
- Une requête `coll.query()` retourne des résultats cohérents
  (= les vecteurs 768 résolvent bien aux drawers existants).
Cette phase n'existait pas explicitement au sprint 6 — on
l'ajoute pour avoir un filet de plus avant la prod.

### Phase 3 : run live prod
Exécution du runbook section par section, arrêt service ARIA,
migration sur le palace prod (le palace est petit, ~5 min max),
bascule config.py, redémarrage, fumée Telegram.

### Phase 4 : nettoyage post-succès
Suppression des artefacts sprint 6 (`palace.rollback-failed-*`,
`palace_preprod_*`, `mempalace_drawers_backup_*.tar.gz`,
`/tmp/migrate_*.log`). Ces fichiers étaient conservés
explicitement "à nettoyer après la première migration réussie
post-patch MemPalace, pas avant" — c'est ce moment-là.

### Phase 5 : clôture sprint 7
Si tout est vert : push branche feat/sprint6-embedder-audit
(commits bd77233 + ceux ajoutés cette session), tag sprint-7,
merge main, push.

---

## Dettes ouvertes héritées

- **#9** : psutil non documenté dans requirements (toujours)
- **#10** : pas de fichier de dépendances versionné ARIA
- **#11** : DeprecationWarning Python 3.14 sur tar.extractall dans
  migrate_embedder.py
- **#13** : discipline workflow consignes CLAUDE.md hors-brief
- **#14** : runbook ne vérifie pas les outils CLI requis (intégré
  dans le runbook T-Mempalace-Live, section 0)
- **#15** : discipline pilote sur check pré-vol échoué (stop +
  rollback léger par défaut)
- **#16** : audit de surface des packages tiers auto-administrants
  (cause racine semi-échec sprint 6)
- **PR upstream MemPalace** : optionnelle. Le patch est propre,
  testé, conserve la backward compat, et le marker side-channel
  est une solution générique utile à d'autres utilisateurs. À
  considérer en fin de sprint 7 si capacité.
- **Bascule shells de `_resolve_embedding_function` legacy** (sans
  palace_path) côté MemPalace : mcp_server.py et autres callers
  identifiés au tour T-Mempalace-Patch resteraient sur le default
  MiniLM. Hors-scope ARIA (non utilisé), à corriger dans une PR
  upstream future.

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 7, phase 2 : run live prod T-Mempalace-Live.
> Voici le contexte de transition [PIÈCE JOINTE : ce document].
>
> Phase 1 close hier (clôture sprint 6 + patch fork MemPalace +
> bascule venv ARIA + patch script ARIA, commit bd77233 local non
> poussé). Le palace conservé sprint 6 est inutilisable, on
> migre from scratch le palace prod actuel.
>
> Premier objectif : rédiger le runbook
> docs/sprint7/runbook_t_mempalace_live.md sur le modèle T-Embedder3
> sprint 6, avec ajouts (vérification outils en section 0,
> validation mempalace.__file__ en pré-vol, log embedding init
> attendu mpnet vs ONNX, fumée Telegram avec test du bug #18
> "Planifier des vacances en Normandie").
>
> Objectif suivant : brief T-Mempalace-Preprod — test sur copie
> avant prod, validation que migrate_embedder.py + fork patché +
> nouveau marker produisent un palace lisible avec query() qui
> retourne des résultats cohérents.