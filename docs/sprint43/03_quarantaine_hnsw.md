# Sprint 43 — tronçon 03 : correctif de la fausse quarantaine HNSW + erreur de recherche journalisée

Lire d'abord : `CLAUDE.md`, `docs/sprint43/00_etat.md`, `docs/sprint43/audit_quarantaine_hnsw.md`
(TL;DR, §2, §4).

## Constat (résumé de l'audit)

Le fork mempalace (`~/Nextcloud/projects/mempalace-fork`, installé en éditable dans `./venv`)
met en quarantaine `.corrupt-*`, au démarrage, tout index HNSW dont `index_metadata.pickle` a
`dimensionality: None`. C'est pourtant le format normal écrit par chromadb 1.5.5 : l'index est
perdu à chaque fois (palace prod depuis le 2026-10-23). L'upstream a corrigé ce faux positif dans
le commit `e811b6d1` (« fix: avoid false HNSW metadata quarantine »), déjà présent dans le dépôt
local du fork (remote `origin`). `git apply --check` passe sur le fork.

Côté ARIA, `MempalaceBridge.retrieve_memories` (`memory/mempalace_bridge.py`) lit
`result.get("results", [])` : quand `search_memories` renvoie `{"error": "..."}`, on obtient 0 hit
sans aucune trace.

## Objectif

### A. Fork (`~/Nextcloud/projects/mempalace-fork`, branche `feat/configurable-embedder`)

1. `git cherry-pick -x e811b6d1` (il modifie `mempalace/backends/chroma.py` et
   `tests/test_backends.py`). Conflit éventuel : le résoudre en gardant le comportement du commit
   amont.
2. Tests du fork : `../aria/venv/bin/python -m pytest tests/test_backends.py -q` doit passer
   (66 tests passent avant le patch).
3. `git push nicofork feat/configurable-embedder` (la remote `nicofork` est le dépôt GitHub de
   Nico ; ce push est autorisé).

### B. ARIA

1. `requirements.txt` l. 10 : remplacer le SHA épinglé `b8caf32…` par le SHA complet du commit
   cherry-pické. Mettre à jour le commentaire au-dessus s'il nomme le commit.
2. `memory/mempalace_bridge.py` : ajouter le logger du projet
   (`from logger import get_logger` / `log = get_logger(__name__)`). Dans `retrieve_memories`,
   juste après l'appel `self._store(...)`, si `result` contient la clé `"error"` :
   `log.warning("retrieve_memories error wing=%s room=%s: %s", wing, room, result["error"])`.
   Le comportement reste inchangé (0 hit, pas d'exception).
3. Test dans `tests/mempalace/test_mempalace_bridge.py` : un faux store qui renvoie
   `{"error": "Search error: Error finding id"}` → `retrieve_memories` renvoie `count == 0` et
   un warning contenant `retrieve_memories error` est journalisé (`caplog`).

## Interdit (hors-scope)

- **Ne jamais ouvrir, copier, réparer ni modifier `~/.mempalace/palace`** : la réparation est
  faite par Nico au tronçon 04.
- Pas de montée de version de mempalace, pas d'autre commit amont, pas de modification de
  `quarantine_stale_hnsw` (les `.drift-*` restent, ils sont sans dommage).
- Pas de contournement côté ARIA (`ChromaBackend._quarantined_paths`, monkeypatch).
- Pas de ménage des `.drift-*` / `.corrupt-*`, pas de changement de `scripts/migrate_embedder.py`.
- Ne pas toucher au reste du bridge ni aux autres callers de `_store`.

## Critère de fin

Tests du fork verts, commit poussé sur `nicofork` ; `pytest tests/ -q` vert dans ARIA ; commit
ARIA local avec `requirements.txt` + bridge + test. Dans le rapport : SHA du commit du fork.
