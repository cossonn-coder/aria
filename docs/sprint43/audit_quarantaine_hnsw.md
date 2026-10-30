# Audit — quarantaine HNSW du palace (run live 43 bloqué)

**Date** : 2026-10-30. **Méthode** : lecture du code du fork (`mempalace/backends/chroma.py`),
`journalctl` du jour, inspection d'une copie de `chroma.sqlite3` (backup sqlite, palace prod
jamais ouvert en écriture), expériences sur palaces jetables dans le scratchpad.
**Dettes liées** : #31, #105 (et l'incident sprint 30).

## TL;DR

1. **La perte date du 2026-10-23 11:56, pas d'aujourd'hui.** Ce jour-là, au démarrage, le fork a
   renommé l'index HNSW valide de `mempalace_drawers` en
   `cc7e6b6a-….corrupt-20261023-115618` (512 vecteurs). chromadb avait déjà purgé la file
   `embeddings_queue` jusqu'au seq 514 : ces vecteurs n'existent plus nulle part.
2. **Cause racine : faux positif du fork.** chromadb 1.5.5 (backend Rust) écrit
   `index_metadata.pickle` avec `dimensionality: None` (la dimension vit dans
   `collections.dimension`). `quarantine_invalid_hnsw_metadata` exige une dimension entière > 0
   dès qu'il y a des labels → `.corrupt-*`. C'est **exactement** l'incident du sprint 30
   (attribué alors au changement de `sync_threshold`).
3. **chromadb relit ce pickle sans problème** (vérifié : nouveau process, requêtes filtrées et
   non filtrées OK). La quarantaine est donc destructrice et inutile.
4. **Upstream MemPalace a corrigé ce faux positif** : commit `e811b6d1` « fix: avoid false HNSW
   metadata quarantine » (2026-05-11, inclus dans v3.3.6). Il s'applique proprement sur notre fork
   (`b8caf32`, base v3.3.5). Avec ce correctif, ni le palace d'essai ni l'archive du 23/10 ne sont
   mis en quarantaine.
5. **Les `.drift-*` répétés (4 aujourd'hui) sont sans dommage** : le segment recréé n'a pas de
   pickle (jamais persisté), le fork le renomme à chaque démarrage, chromadb le reconstruit depuis
   la file (seq 514→696, intacte). Ils disparaîtront à la première persistance une fois le
   correctif en place.
6. **Réparation possible et testée sur copie** : `scripts/migrate_embedder.py` en mpnet→mpnet
   ré-encode les 690 documents depuis sqlite → 690/690, requêtes OK sur toutes les wings.
7. **L'erreur est muette côté ARIA** : `search_memories` renvoie `{"error": …}`,
   `bridge.retrieve_memories` lit `result.get("results", [])` → 0 hit, aucun log. Rappel
   épisodique **et cache classifier** muets depuis 7 jours sans signal.

## 1. Chronologie

| Date | Événement | Source |
|---|---|---|
| 2026-10-22 23:18 | palace reconstruit (sprint 30, `migrate_embedder`) : `sync_threshold` 1000, `batch_size` 100 | sprint30/00_etat.md, `schema_str` |
| 2026-10-23 09:07 | chromadb persiste l'index (512 éléments) ; `max_seq_id` du segment VECTOR = 514 ; file purgée jusqu'à 514 | `max_seq_id`, `embeddings_queue` min seq = 514 (créé 09:07:54 UTC) |
| 2026-10-23 11:07 | dernière écriture du pickle (mtime) | `.corrupt-20261023-115618/` |
| 2026-10-23 11:56 | démarrage → `.corrupt-*` (dimensionality None) → index vide, chromadb rejoue la file depuis 514 seulement | nom du dossier ; mécanisme reproduit §3 |
| 2026-10-29 → 30 | 5 `.drift-*` (un par démarrage), sans dommage supplémentaire | `journalctl`, `ls ~/.mempalace/palace` |
| 2026-10-30 15:39 | run live 43 : rappel muet → étape 3 en échec | 00_etat.md |

Correction du 00_etat : « HNSW environ 200 [estimation sur la taille de `data_level0.bin`] » est
faux. 321 200 o = capacité préallouée de 100 éléments (100 × 3 212 o, dim 768), identique dans
tous les `.drift-*` ; pas un compte. Le contenu réel de l'index = les seq > 514 de la file (183
opérations).

## 2. Code en cause (fork, `mempalace/backends/chroma.py`)

`_prepare_palace_for_open` (l. ~1290), une fois par palace et par process, avant
`PersistentClient` :

```python
_fix_blob_seq_ids(palace_path)
if palace_path not in ChromaBackend._quarantined_paths:
    quarantine_invalid_hnsw_metadata(palace_path)
    quarantine_stale_hnsw(palace_path)
    ChromaBackend._quarantined_paths.add(palace_path)
```

`quarantine_invalid_hnsw_metadata` (l. 697-775), branche fautive :

```python
has_labels = bool(id_to_label)
if has_labels and not _valid_dimensionality(dimensionality):
    reason = ("labels present but dimensionality is missing or invalid "
              f"({dimensionality!r})")
```

Pickle de l'archive du 23/10 :
`dimensionality None, total_elements_added 512, max_seq_id None, id_to_label 512, label_to_id 512,
id_to_seq_id 0`. Pickle d'un palace jetable écrit par chromadb 1.5.5 : même forme
(`dimensionality None`, 300/300/300). C'est le format normal du backend Rust.

`quarantine_stale_hnsw` (l. 238-335) : renomme en `.drift-*` si `sqlite_mtime − hnsw_mtime ≥ 300 s`
et `_segment_appears_healthy` faux (pas de pickle) — cas actuel à chaque démarrage, sans perte car
la file n'est purgée qu'à la persistance.

Correctif upstream `e811b6d1` : quand `dimensionality is None`, ne met en quarantaine que si
`_missing_dimensionality_appears_recoverable` est faux (contrôle `total_elements_added` =
`len(id_to_label)` = `len(label_to_id)`, bijection labels↔ids, `data_level0.bin` > 1 024 o,
`link_lists.bin` présent, payload sain). Helpers `_hnsw_payload_appears_sane` et
`_HNSW_MISSING_METADATA_DATA_FLOOR` déjà présents dans le fork. `git apply --check` : OK
(décalage 17 lignes). Le patch ajoute aussi des tests dans `tests/test_backends.py` (applique OK).

## 3. Expériences (scratchpad, palace prod jamais touché)

| # | Palace | Opération | Résultat |
|---|---|---|---|
| E1 | jetable, 350 entrées 768d, `sync_threshold` 100 | écriture puis relecture par un nouveau process, chromadb seul | pickle `dimensionality None` ; requêtes `where={"wing": "big"}` et sans filtre : OK |
| E2 | copie de E1 | `quarantine_invalid_hnsw_metadata` du fork actuel, puis relecture | `.corrupt-*` ; requête : `InternalError: Error finding id` (= symptôme prod) |
| E3 | copie de E1 + archive du 23/10 | même fonction, version upstream `e811b6d1` | aucune quarantaine ; requêtes OK |
| E4 | copie prod (sqlite + segment courant) | `search_memories` (chemin ARIA) sur 3 wings | `Error finding id` sur `aria_episodic`, `aria_conversation`, `aria_classifier` |
| E5 | copie prod | `migrate_embedder.py --from-model mpnet --to-model mpnet --no-snapshot` | 690/690, dim 768, encodage 253 s [CPU, n=1] |
| E6 | copie E5, fork actuel puis fork+correctif | `search_memories` sur 3 wings | 5 hits partout, les deux versions |

Répartition prod (copie sqlite, 2026-10-30 15:40) :

| wing | hors index (seq ≤ 514) | dans l'index |
|---|---|---|
| aria_conversation | 310 | 119 |
| aria_episodic | 161 | 46 |
| aria_classifier | 39 | 12 |
| aria_documents | 0 | 3 |

(« dans l'index » = seq > 514 ; un upsert d'un ancien id le fait passer à droite.)

## 4. Côté ARIA

- `memory/mempalace_store.search` → `mempalace.searcher.search_memories(...)` → `get_collection`
  → `_prepare_palace_for_open`. Aucune option ARIA pour désactiver ou ajuster les quarantaines.
- `memory/mempalace_bridge.py` `retrieve_memories` (l. 63-) : `result.get("results", [])` ;
  un résultat `{"error": …}` devient 0 hit sans log.
- `requirements.txt` l. 10 : `mempalace @ git+https://github.com/cossonn-coder/mempalace.git@b8caf32…`.
  Venv : install éditable de `~/Nextcloud/projects/mempalace-fork` (branche
  `feat/configurable-embedder`, remote `nicofork`).
- `scripts/migrate_embedder.py` : refuse de tourner si `.embedder-migration-marker` porte le hash
  du modèle cible (pas de `--force`) → déplacer le marker avant une ré-exécution mpnet→mpnet.
  Il supprime et recrée `mempalace_drawers` (config par défaut : `sync_threshold` 1000).

## 5. Bombe à retardement sans correctif

Toute persistance future de l'index par chromadb (atteinte du seuil de synchronisation) écrit un
pickle `dimensionality None` ; au démarrage suivant, le fork le met en `.corrupt-*` et la partie
déjà purgée de la file est perdue. Une réparation sans correctif du fork reperdrait donc tout à la
prochaine persistance. Ordre imposé : **correctif du fork d'abord, réparation ensuite.**

## 6. Hors périmètre constaté

- Dossiers `.drift-*` (6) et `.corrupt-*` (1) dans le palace : hygiène, purgeables après réparation
  (garder le `.corrupt-20261023-*` tant que l'audit sert de trace ? 1,7 Mo).
- Dossier segment orphelin après recréation de la collection (vu sur copie E5) : renommé en
  `.drift-*` au démarrage suivant, sans effet.
- Mise à jour complète de mempalace vers v3.3.6+ : 227 commits, 181 fichiers — hors calibrage.
