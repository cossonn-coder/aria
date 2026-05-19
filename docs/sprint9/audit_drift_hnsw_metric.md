# T-Drift-HNSW-Metric — Instrumentation discriminante de la repro

**Sprint** : 9 (cible dette #20) — complément de `audit_drift_hnsw.md`
**Date** : 2026-05-19
**Branche** : `feat/sprint9-drift-hnsw`
**Statut** : audit, aucun fix appliqué

---

## TL;DR

La métrique enrichie pivote le diagnostic. **`PersistentLocalHnswSegment._persist()`
(Python) n'est appelé par AUCUNE des 7 méthodes** — non pas parce qu'elles
oublient de le faire, mais parce que **le code Python est mort code en
chromadb 1.5.5**. L'API par défaut depuis 1.5.x est `RustBindingsAPI`
(`chromadb/config.py:120`), qui route tous les writes via
`chromadb_rust_bindings.Bindings.add/upsert/...` directement vers la couche
Rust native. Le segment manager Python `LocalSegmentManager` n'est jamais
exercé : `_instances` reste vide après 51 add() (mesuré). Le rapport initial
`audit_drift_hnsw.md` §2 a disséqué un chemin obsolète.

Conséquences sur le diagnostic du sprint 9 et l'ordre de fix proposé en §6
du premier audit : **changement substantiel** — voir §5.

---

## 1. Setup vs repro initiale

`docs/sprint9/repro_drift.py` étendu avec :

- **Métrique 1 — pickle mtime** : `index_metadata.pickle.mtime` échantillonné
  juste avant la séquence de fermeture (sampler dans le runner, écrit
  dans `<palace>/_runner_state.json`), après fermeture (driver), après
  reload (driver). Ce fichier est touché uniquement par
  `PersistentLocalHnswSegment._persist()` côté Python (`local_persistent_hnsw.py:255`).
- **Métrique 2 — monkey-patch `_persist`** : wrapper posé en début de runner
  sur `chromadb.segment.impl.vector.local_persistent_hnsw.PersistentLocalHnswSegment._persist`.
  Log par ligne (timestamp, méthode, segment_id,
  `_num_log_records_since_last_persist`, frame caller) dans
  `/tmp/aria_drift_repro/persist_calls.log`.
- **`persist-then-close` réparé** : chemin canonique
  `client._system.instance(SegmentManager)._instances.values()` filtré
  par `isinstance(impl, PersistentLocalHnswSegment)`. Diag écrit dans
  `_runner_state.json` (`inspected`, `persisted`, `errors`).

Tout le reste (50 docs + `sleep(2)` + sentinel, palaces jetables sous
`/tmp/aria_drift_repro/<méthode>/`) est inchangé.

Environnement : python 3.13.5, chromadb 1.5.5, mempalace 3.3.5,
chroma-hnswlib 0.7.6 (nécessaire pour résoudre l'import `hnswlib` côté
chromadb — détaillé §6).

---

## 2. Tableau de résultats étendu

```
méthode                | drift (s) | pickle_Δclose (s) | _persist calls | count reload | note
--------------------------------------------------------------------------------------------
no-close               |     2.124 |               N/A |              0 |           51 | complet
backend-close          |     2.168 |               N/A |              0 |           51 | complet
client-close           |     2.468 |               N/A |              0 |           51 | complet
client-context-mgr     |     2.472 |               N/A |              0 |           51 | complet
persist-then-close     |     2.128 |               N/A |              0 |           51 | complet
sigterm                |     2.124 |               N/A |              0 |           51 | complet
sigkill                |     2.104 |               N/A |              0 |           51 | complet
```

`pickle_Δclose = N/A` parce que `index_metadata.pickle` **n'existe jamais
dans le dossier segment**. Vérifié manuellement :

```
$ ls /tmp/aria_drift_repro/backend-close/<seg-uuid>/
data_level0.bin  header.bin  length.bin  link_lists.bin
```

Pas de `index_metadata.pickle`. `/tmp/aria_drift_repro/persist_calls.log`
est lui aussi inexistant pour les 7 méthodes (0 appel monkey-patch capturé).

Diag `persist-then-close` (depuis `_runner_state.json`) :
`{"inspected": 0, "persisted": 0, "errors": []}` — `SegmentManager._instances`
est vide, donc aucune instance à flusher.

---

## 3. Lecture des résultats

Les deux métriques convergent vers la même réponse, sans ambiguïté
résiduelle :

- **`index_metadata.pickle` jamais créé** sur les 7 méthodes. Or
  `_persist()` est l'unique callsite qui écrit ce fichier
  (`pickle.dump(self._persist_data, ...)` ligne 256 du segment). Absence
  du fichier ⇒ `_persist()` jamais exécuté.
- **0 appels capturés par le monkey-patch** sur les 7 méthodes,
  confirmation directe.
- **`LocalSegmentManager._instances` vide** après 51 add() ⇒ le
  code path Python qui peuplait ce dict (`_instance(segment)` via
  `get_segment` ligne 219) n'est pas traversé par les writes.

Le coupable est `chroma_api_impl = "chromadb.api.rust.RustBindingsAPI"`
(`chromadb/config.py:120`, défaut depuis 1.5.x). Tous les writes passent
par `RustBindingsAPI.add()` → `self.bindings.add(...)` → couche Rust
(`chromadb_rust_bindings.abi3.so`). L'API Bindings (`chromadb_rust_bindings.pyi`)
n'expose **aucun** `stop`, `close`, `flush`, `persist`. La seule cleanup
côté Python est `del self.bindings` dans `RustBindingsAPI.stop()`
(`chromadb/api/rust.py:130`).

Le drift de ≈ 2 s observé sur toutes les méthodes (égal au `sleep(2)`
injecté) provient donc du **code Rust** qui mmap `data_level0.bin` et
écrit incrémentalement à chaque `bindings.add()`. Aucune intervention
côté Python n'a moyen de déclencher un flush HNSW propre — la métrique
pickle aurait pu le révéler, elle révèle au contraire que la couche
Python n'est jamais touchée.

---

## 4. Verdict par méthode

| méthode               | `_persist()` Python appelé ? | Conséquence diagnostic |
|-----------------------|------------------------------|------------------------|
| `no-close`            | **NON** (0 / pickle absent)  | Comme attendu          |
| `backend-close`       | **NON** (0 / pickle absent)  | Le fork ne déclenche pas de flush via la couche Python — il ne peut pas, le code path Python est mort |
| `client-close`        | **NON** (0 / pickle absent)  | `Client.close()` se réduit à `SharedSystemClient._release_system()` → `System.stop()` → `RustBindingsAPI.stop()` → `del self.bindings`. Rien ne flushe HNSW côté Python |
| `client-context-mgr`  | **NON** (0 / pickle absent)  | `__exit__` appelle `close()` — strictement équivalent au précédent |
| `persist-then-close`  | **NON** (`_instances={}`)    | Le SegmentManager local n'est pas exercé ; aucune instance à flusher. Le forçage manuel est **structurellement impossible** par cette API |
| `sigterm`             | **NON** (0 / pickle absent)  | Cohérent avec `no-close` (PTB attrape SIGTERM puis exit naturel) |
| `sigkill`             | **NON** (0 / pickle absent)  | Cohérent (process tué avant tout cleanup) |

Toutes les méthodes donnent `count_after_reload = 51` : le replay WAL
côté Rust reconstruit l'index en mémoire au reload. Le drift reste
**bénin** comme établi dans l'audit initial §5.

---

## 5. Recommandation pour le tour suivant

La métrique enrichie **invalide partiellement le §6 du premier audit**.
Ordre de fix proposé initialement (ARIA atexit → fork flush reflexif →
upstream patch sur `Segment.stop()`) reposait sur l'hypothèse que
`PersistentLocalHnswSegment._persist()` était sur le chemin actif. Il
ne l'est pas. Pivot nécessaire avant tout fix :

1. **Avant fix, déterminer ce que la couche Rust expose comme cleanup.**
   Pistes à investiguer (par lecture du `.so` ou de la source upstream
   `chromadb_rust_bindings`, hors-scope ce tour) :
   - existe-t-il un `Bindings.stop()` / `Bindings.flush()` non documenté
     dans le `.pyi` ?
   - le `__del__` du `Bindings` côté Rust flushe-t-il ?
   - le `hnsw_cache_size` (paramètre `Bindings.__init__`) implique-t-il
     une politique d'eviction qui flushe ?
2. **Si la couche Rust expose un flush** : le fork peut l'appeler avant
   `del self.bindings` (via accès `client._server.bindings`). Le test
   de non-régression est trivial à étendre depuis cette repro
   (ajouter une 8e méthode qui appelle ce flush, vérifier drift → 0
   et `index_metadata.pickle` non plus mais l'équivalent format Rust
   touché).
3. **Si la couche Rust n'expose rien** : il faut soit forker chromadb-rust,
   soit attendre upstream, soit accepter le drift comme propriété du
   design Rust. Dans ce dernier cas, le filet `quarantine_stale_hnsw`
   + replay WAL existant reste suffisant et la dette #20 se referme
   en "documentation + non-régression sur la quarantaine".

L'ordre ARIA → fork → upstream reste valide en principe (atexit ARIA
préalable nécessaire à toute solution), mais l'étape fork doit cibler
les **bindings Rust**, pas le code Python. Sans cette correction, un
fix prématuré patcherait à l'aveugle sur du dead code.

---

## 6. Note de reproduction

Le venv `/home/nico/projects/aria/venv/` ne contenait pas le package
`hnswlib` au moment de cette repro. L'audit initial l'avait pourtant
exercé (rapport `audit_drift_hnsw.md` §5 montrait des résultats), ce qui
laisse penser qu'`hnswlib` a été désinstallé entre temps ou que la repro
initiale a été lancée depuis un autre interpréteur. Installation
nécessaire : `pip install chroma-hnswlib==0.7.6` (extra `dev` de
chromadb 1.5.5, cf. `METADATA`). Le wheel PyPI `hnswlib` (0.8.0) ne
satisfait pas — l'API attendue par chromadb (`hnswlib.Index.file_handle_count`)
n'existe que dans le fork `chroma-hnswlib`.

Hors-scope sprint 9, à noter pour reproductibilité future.
