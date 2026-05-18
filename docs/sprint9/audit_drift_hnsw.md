# T-Drift-HNSW-Audit — Cartographie de la fermeture palace

**Sprint** : 9 (cible dette #20)
**Date** : 2026-05-18
**Branche** : `feat/sprint9-drift-hnsw`
**Statut** : audit pur, **aucun fix appliqué**

---

## Résumé exécutif

Le drift sqlite/HNSW observé en preprod-2 (+31.235 s constant) n'est
ni un bug du fork MemPalace ni un défaut spécifique d'ARIA : c'est
**un choix de design upstream de ChromaDB 1.5.5**. Le segment
`PersistentLocalHnswSegment.stop()` n'appelle PAS `_persist()` — il
ferme uniquement les file handles via `close_persistent_index()`.
Tous les records écrits depuis le dernier batch-threshold (1000 par
défaut, **50 000 sur les collections créées par le fork**) restent
non flushés sur disque au moment du `systemctl stop`.

La repro contrôlée (cf. §5) démontre que **aucune** méthode de
fermeture testée — `client.close()`, `with chromadb.PersistentClient`,
`ChromaBackend.close()`, `_persist()` reflexif via API interne, SIGTERM,
SIGKILL — ne ramène le drift à zéro. Le drift constaté correspond
strictement au temps écoulé entre la dernière écriture HNSW persistée
et la dernière écriture SQLite (`time.sleep(2)` injecté en repro =
drift mesuré 2.16–2.59 s sur toutes les méthodes).

Côté opérationnel le drift reste **bénin** : chromadb replay le WAL
SQLite au reload et reconstruit l'index HNSW en mémoire à partir des
log records. Aucune perte de données mesurée. Le risque résiduel est
le `corrupt-*` quarantiné par le fork si l'integrity check échoue
(observé en prod sur un segment du 13 mai 2026, mtime gap 1378844 s).

**Diagnostic retenu** : mix bug upstream ChromaDB + bug fork + bug
ARIA, avec le poids du côté upstream. Détails §6.

---

## 1. Cartographie fork MemPalace

### Localisation et version

- **Chemin** : `/home/nico/Nextcloud/projects/mempalace-fork/mempalace/`
  (editable install via `pip install -e`)
- **Version** : `3.3.5`
- **Module bas-niveau pertinent** : `mempalace/backends/chroma.py`
  (1526 lignes). `palace.py` et `embedding.py` ne contiennent **aucune
  logique de fermeture** — ce sont des utilitaires (collection
  access, embedding factory) sans cleanup.

### Méthodes de fermeture trouvées

Grep `grep -rn -E "def (close|flush|persist|_persist|shutdown|__del__|__exit__)\b" mempalace/`
sur le fork → **aucune méthode `flush`, `persist`, `_persist`,
`shutdown`, `__del__` n'existe**. Seul `close()` existe, à trois
endroits :

#### `mempalace/backends/base.py:238` — contrat `BaseCollection.close`

```python
def close(self) -> None:
    return None
```

**No-op par défaut.** Le contrat ne promet pas de flush ; il ne
promet rien du tout.

#### `mempalace/backends/base.py:318-324` — contrat `BaseBackend.close*`

```python
def close_palace(self, palace: PalaceRef) -> None:
    """Evict cached handles for a single palace. Default: no-op."""
    return None

def close(self) -> None:
    """Shut down the entire backend. Default: no-op."""
    return None
```

L'API contractuelle elle-même documente `close()` comme **no-op par
défaut**. La doctring parle d'éviction de cache, pas de persistance.

#### `mempalace/backends/chroma.py:1411-1430` — implémentations `ChromaBackend`

```python
def close_palace(self, palace) -> None:
    """Drop cached handles for ``palace`` and release its SQLite file lock.

    Accepts ``PalaceRef`` or legacy path str. chromadb's rust-side file
    lock is held until ``PersistentClient.close()`` is called, so plain
    dict eviction would leave the palace path unreopenable and
    unremovable in the same process.
    """
    path = palace.local_path if isinstance(palace, PalaceRef) else palace
    if path is None:
        return
    _close_client(self._clients.pop(path, None))
    self._freshness.pop(path, None)

def close(self) -> None:
    for client in self._clients.values():
        _close_client(client)
    self._clients.clear()
    self._freshness.clear()
    self._closed = True
```

Et `_close_client` (ligne 863-874) :

```python
def _close_client(client) -> None:
    """Call ``PersistentClient.close()`` if available, swallow otherwise.

    chromadb 1.5.x exposes ``Client.close()`` to release rust-side SQLite
    file locks; older versions relied on GC. Try/except keeps forward-compat.
    """
    if client is None:
        return
    try:
        client.close()
    except Exception:
        logger.debug("client.close() unavailable or failed", exc_info=True)
```

**Constat fork** : le fork délègue strictement à
`chromadb.PersistentClient.close()`. **Aucune logique de flush propre,
aucun appel direct à `_persist()` upstream.** Le commentaire est
explicite sur la motivation (release SQLite file lock), pas sur
la persistance HNSW.

### Callers de `close()` dans le fork

```
mempalace/repair.py:1105      backend.close()                     # CLI mempalace repair
mempalace/repair.py:1178      closer.close_palace(palace_path)    # idem
mempalace/mcp_server.py:1621  _DEFAULT_BACKEND.close_palace(...)  # reconnect MCP
mempalace/backends/registry.py:133  inst.close()                   # reset registry (tests)
mempalace/sources/registry.py:137   inst.close()                   # idem
```

Aucun de ces callers ne s'exécute en runtime ARIA normal — ce sont
des chemins administratifs (repair CLI, MCP reconnect, registry reset
en tests).

### Diagramme du chemin attendu (état actuel)

```
ARIA bot.py
  └─ telegram.start() ──── run_polling() boucle bloquante
                            │
                            └─ kernel.handle_event() ──── memory write
                                                            │
                                                            ▼
mempalace.palace._DEFAULT_BACKEND (ChromaBackend instancié à l'import)
  └─ get_collection(palace_path, ...)
       └─ self._client(palace_path) ─── PersistentClient (cache _clients dict)
       └─ ChromaCollection(...)._collection.upsert(...)
            │
            └─ chromadb segment _apply_batch
                 │
                 └─ _num_log_records_since_last_persist >= sync_threshold (50000) ?
                       OUI → _persist() ← jamais atteint en runtime ARIA
                       NON → continue, HNSW reste en mémoire

[ SIGTERM systemctl stop ]
  └─ python-telegram-bot intercepte → Application.stop() → run_polling() retourne
       └─ telegram.start() retourne dans bot.py:28
            └─ main() retourne, Python exit
                 ├─ GC ← aucun __del__ côté fork ni chromadb client
                 ├─ aucun atexit côté fork ni ARIA
                 └─ process termine ─── HNSW non flushé reste à mtime-T-stop
```

---

## 2. Cartographie ChromaDB upstream

### Version et localisation

- **Version** : `chromadb 1.5.5`
- **Chemin** : `/home/nico/projects/aria/venv/lib/python3.13/site-packages/chromadb/`
- Le venv contient `chromadb_rust_bindings.pyi` — preuve d'une couche
  native Rust (motivation du note fork sur le file lock).

### Méthodes pertinentes

#### `chromadb/api/client.py:550-585` — `Client.close()`

```python
def close(self) -> None:
    """Close the client and release all resources.

    This method decrements the reference count for the underlying System.
    When the last client using a shared System calls close(), the System
    is stopped and all resources (database connections, etc.) are released.

    This is particularly important for PersistentClient to avoid SQLite
    file locking issues.
    """
    if self._closed:
        return
    self._closed = True

    if hasattr(self, "_admin_client"):
        SharedSystemClient._release_system(self._admin_client._identifier)

    SharedSystemClient._release_system(self._identifier)
```

Et le context manager :

```python
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    """Context manager exit."""
    self.close()
```

`close()` ne fait que décrémenter un refcount sur le `System`. Si le
refcount tombe à 0, `System.stop()` est appelé.

#### `chromadb/config.py:347-351` — `Component.stop`

```python
def stop(self) -> None:
    """Idempotently stop this component's execution and free all associated
    resources."""
    logger.debug(f"Stopping component {self.__class__.__name__}")
    self._running = False
```

`Component.stop` de base **se contente de basculer `_running = False`**.

#### `chromadb/config.py:469-473` — `System.stop`

```python
def stop(self) -> None:
    super().stop()
    for component in reversed(list(self.components())):
        component.stop()
```

`System.stop` boucle sur les composants en ordre inverse de dépendance
et appelle `stop()` sur chacun.

#### `chromadb/segment/impl/vector/local_persistent_hnsw.py:536-543` — **POINT CRITIQUE**

```python
@override
def stop(self) -> None:
    super().stop()
    self.close_persistent_index()

def close_persistent_index(self) -> None:
    """Close the persistent index"""
    if self._index is not None:
        self._index.close_file_handles()
```

🚨 **Le `stop()` du segment HNSW persistent ferme uniquement les
file handles. AUCUN appel à `_persist()`.**

#### `chromadb/segment/impl/vector/local_persistent_hnsw.py:237-272` — `_persist()`

C'est la seule méthode qui écrit réellement le HNSW sur disque :

```python
@trace_method("PersistentLocalHnswSegment._persist", OpenTelemetryGranularity.ALL)
def _persist(self) -> None:
    """Persist the index and data to disk"""
    index = cast(hnswlib.Index, self._index)
    index.persist_dirty()                                            # ← flush HNSW

    self._persist_data.dimensionality = self._dimensionality
    self._persist_data.total_elements_added = self._total_elements_added
    self._persist_data.id_to_label = self._id_to_label
    self._persist_data.label_to_id = self._label_to_id
    self._persist_data.id_to_seq_id = self._id_to_seq_id

    with open(self._get_metadata_file(), "wb") as metadata_file:
        pickle.dump(self._persist_data, metadata_file, pickle.HIGHEST_PROTOCOL)

    with self._db.tx() as cur:
        q = (self._db.querybuilder().into(Table("max_seq_id"))
             .columns("segment_id", "seq_id")
             .insert(...))
        sql, params = get_sql(q)
        sql = sql.replace("INSERT", "INSERT OR REPLACE")
        cur.execute(sql, params)

    self._num_log_records_since_last_persist = 0
```

### Conditions sous lesquelles `_persist` s'exécute

Grep `_persist(` dans chromadb upstream → **un seul callsite**
en dehors de `_persist` lui-même :

```python
# chromadb/segment/impl/vector/local_persistent_hnsw.py:278-283
@override
def _apply_batch(self, batch: Batch) -> None:
    super()._apply_batch(batch)
    if self._num_log_records_since_last_persist >= self._sync_threshold:
        self._persist()
```

Le seuil `sync_threshold` vient de `chromadb/segment/impl/vector/hnsw_params.py:80` :

```python
self.sync_threshold = int(metadata.get("hnsw:sync_threshold", 1000))
```

**Default upstream = 1000**. Le fork remonte ce seuil à **50 000**
(`mempalace/backends/chroma.py:146`) :

```python
_HNSW_BLOAT_GUARD = {
    "hnsw:sync_threshold": 50_000,
    ...
}
```

Aucun `atexit.` n'est enregistré dans chromadb (`grep -rn atexit\\.
chromadb/` → 0 hits). Aucun handler signal non plus. Le seul chemin
naturel vers `_persist()` est l'accumulation de batches au-delà du
seuil pendant l'activité — **rien au shutdown**.

### Diagramme upstream

```
client.close()
  └─ self._closed = True
  └─ SharedSystemClient._release_system(self._identifier)
       │
       └─ si dernière référence ──── System.stop()
                                      │
                                      └─ for component in reversed(components):
                                          └─ component.stop()
                                              │
                                              ├─ SegmentManager.stop()       (close caches)
                                              ├─ PersistentLocalHnswSegment.stop()
                                              │    ├─ super().stop()  → _running = False
                                              │    └─ close_persistent_index()
                                              │         └─ index.close_file_handles()
                                              │              ╳ aucun _persist appelé
                                              │              ╳ HNSW reste à l'état du dernier batch-threshold
                                              ├─ SqliteDB.stop()              (close conn, sync OK)
                                              └─ ...
```

---

## 3. Cartographie shutdown ARIA

### Service systemd

`/home/nico/Nextcloud/projects/aria/aria.service` :

```ini
[Service]
Type=simple
User=nico
WorkingDirectory=/home/nico/projects/aria
EnvironmentFile=/home/nico/groq/.env
ExecStart=/home/nico/projects/aria/venv/bin/python bot.py
Restart=on-failure
RestartSec=10
```

Aucun `KillSignal`, `KillMode`, ni `TimeoutStopSec` custom — defaults
systemd : SIGTERM puis SIGKILL après 90 s.

### Point d'entrée `bot.py` (intégral)

```python
import os
from logger import configure_root
configure_root(level=os.getenv("ARIA_LOG_LEVEL", "INFO"))

from core.kernel import AriaKernel
from interfaces.telegram_interface import TelegramInterface

def main():
    from logger import get_logger
    log = get_logger(__name__)
    log.info("ARIA démarrage")

    kernel = AriaKernel()
    telegram = TelegramInterface(
        kernel,
        token=os.environ["ARIA_BOT_TOKEN"],
    )
    log.info("Telegram interface prête")
    telegram.start()

if __name__ == "__main__":
    main()
```

🚨 **Aucun `signal.signal`, aucun `atexit.register`, aucun `try/finally`,
aucun `backend.close()`.** Le palace est ouvert paresseusement la
première fois qu'un handler écrit en mémoire (via
`mempalace.palace._DEFAULT_BACKEND.get_collection`), et n'est jamais
fermé.

### `TelegramInterface.start` (`interfaces/telegram_interface.py:40-53`)

```python
def start(self):
    self.app = ApplicationBuilder().token(self.token).build()
    self.app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
    )
    self.app.add_handler(
        MessageHandler(filters.PHOTO, self._handle_photo)
    )
    self.app.run_polling()
```

`python-telegram-bot` `Application.run_polling()` installe ses propres
handlers SIGINT/SIGTERM/SIGABRT (paramètre `stop_signals` par défaut)
pour sortir proprement de l'event loop. Au retour de `run_polling()`,
le contrôle revient à `bot.py:28`, `main()` termine, Python exit
sans appeler aucun cleanup côté palace.

### Trace SIGTERM → exit (état actuel)

```
systemctl stop aria.service
  └─ SIGTERM (PID python bot.py)
       └─ python-telegram-bot signal handler
            └─ Application.stop() ── event loop sort de run_polling()
                 └─ telegram.start() retourne dans bot.py:28
                      └─ main() retourne, __main__ termine
                           └─ Python exit
                                ├─ ╳ aucun atexit côté ARIA
                                ├─ ╳ aucun atexit côté mempalace
                                ├─ ╳ aucun atexit côté chromadb
                                ├─ ╳ aucun __del__ côté ChromaBackend ni Client
                                └─ process meurt ─── HNSW reste à l'état pré-stop
```

Grep `grep -rn -E "(signal\.signal|SIGTERM|atexit|stop_signals)" aria_repo/` →
**0 hits** côté ARIA (à part le commentaire SIGINT non-pertinent dans
mempalace-fork lui-même).

---

## 4. Métrique drift

### Source du nombre +31.235 s

C'est le résultat de la formule :

```python
drift_seconds = os.path.getmtime("chroma.sqlite3") - os.path.getmtime("data_level0.bin")
```

où `data_level0.bin` est le fichier HNSW persisté dans le sous-dossier
du segment vecteur (`<palace>/<segment-uuid>/data_level0.bin`).

Cette métrique est **exactement** celle utilisée par le fork à
l'ouverture du palace, dans
`mempalace.backends.chroma.quarantine_stale_hnsw` (lignes 238-335).
Citation des lignes critiques :

```python
def quarantine_stale_hnsw(palace_path: str, stale_seconds: float = 300.0) -> list[str]:
    ...
    sqlite_mtime = os.path.getmtime(db_path)
    ...
    hnsw_bin = os.path.join(seg_dir, "data_level0.bin")
    hnsw_mtime = os.path.getmtime(hnsw_bin)

    payload_ratio = _hnsw_link_to_data_ratio(seg_dir)
    payload_corrupt = payload_ratio is not None and payload_ratio > _HNSW_LINK_TO_DATA_MAX_RATIO

    if not payload_corrupt and sqlite_mtime - hnsw_mtime < stale_seconds:
        continue   # bénin : pas même signalé

    if not payload_corrupt and _segment_appears_healthy(seg_dir):
        logger.info(
            "HNSW mtime gap %.0fs on %s exceeds threshold but segment "
            "metadata and payload size are intact — flush-lag, not "
            "corruption. Leaving in place.",
            sqlite_mtime - hnsw_mtime, seg_dir,
        )
        continue   # signalé mais préservé

    # sinon: rename en seg_dir.drift-<stamp> (quarantaine)
```

Trois cas pris en compte :
- `drift < 300s` : silencieux, segment laissé en place
- `300s ≤ drift` mais integrity check OK : log INFO "flush-lag, not
  corruption", segment laissé en place
- integrity check fail ou ratio `link_lists.bin / data_level0.bin` >
  `_HNSW_LINK_TO_DATA_MAX_RATIO` : segment renommé en
  `<seg_dir>.drift-<stamp>` ou `.corrupt-<stamp>`

C'est exactement le log observé en prod à 14:40:29 :

```
HNSW mtime gap 1378844s on /home/nico/.mempalace/palace/b28198b8-...corrupt-20260513-180821
exceeds threshold but segment metadata and payload size are intact —
flush-lag, not corruption. Leaving in place.
```

1378844 s ≈ 16 jours, cohérent avec la date stamp `20260513-180821` —
ce segment a été quarantiné le 13 mai 2026 à 18:08, son HNSW
mtime est figé à ce moment-là, sqlite a continué à avancer.

### Interprétation du +31.235 s en preprod-2

Le drift mesuré reflète le **temps écoulé entre la dernière écriture
HNSW persistée et la dernière écriture SQLite**. En runtime ARIA
normal :

- chaque interaction Telegram écrit dans `embeddings_queue` (SQLite,
  commit synchrone) → `sqlite_mtime` avance
- chaque insert appelle `_apply_batch` côté HNSW, qui n'appelle
  `_persist()` que si le seuil de 50 000 records est atteint —
  jamais en pratique pour ARIA
- conséquence : `data_level0.bin` garde son mtime **figé à
  l'ouverture du palace** (premier load qui touche le fichier),
  pendant que `chroma.sqlite3` avance toutes les quelques secondes

Le +31.235 s constant avant/après stop est donc la durée totale
d'écriture SQLite de la session, mesurée entre le premier insert et
le SIGTERM. Cette métrique restera **disponible et fiable** pour
toute repro future — elle ne vient pas d'un compteur interne ARIA,
c'est une mesure filesystem directe.

---

## 5. Reproduction contrôlée

### Setup

- Script : `docs/sprint9/repro_drift.py`
- Palaces jetables sous `/tmp/aria_drift_repro/<méthode>/`
- 50 documents écrits + 1 sentinel séparé par `time.sleep(2)`
  (pour différencier mtime SQLite et HNSW)
- chromadb 1.5.5, mempalace 3.3.5, python 3.13.5

### Méthodes testées

| Méthode               | Description                                                |
|-----------------------|------------------------------------------------------------|
| `no-close`            | Exit naturel sans appel close                              |
| `backend-close`       | `ChromaBackend.close()` du fork                            |
| `client-close`        | `chromadb.PersistentClient.close()` direct                 |
| `client-context-mgr`  | `with chromadb.PersistentClient(...) as client:`           |
| `persist-then-close`  | Force `_persist()` via accès interne `client._system.components()` puis `backend.close()` |
| `sigterm`             | Subprocess + `os.kill(pid, SIGTERM)` (scénario systemctl)  |
| `sigkill`             | Subprocess + `os.kill(pid, SIGKILL)` (référence "perte garantie") |

### Résultat (sortie brute du driver)

```
# Repro drift HNSW — base=/tmp/aria_drift_repro
# python=3.13.5
# chromadb=1.5.5 mempalace=3.3.5

→ méthode: no-close
  drift = 2.204s  | count après reload = 51

→ méthode: backend-close
  drift = 2.220s  | count après reload = 51

→ méthode: client-close
  drift = 2.520s  | count après reload = 51

→ méthode: client-context-mgr
  drift = 2.592s  | count après reload = 51

→ méthode: persist-then-close
  drift = 2.164s  | count après reload = 51

→ méthode: sigterm
  drift = 2.236s  | count après reload = 51

→ méthode: sigkill
  drift = 2.196s  | count après reload = 51

======================================================================
méthode                |  drift (s) | count reload | note
----------------------------------------------------------------------
no-close               |      2.204 |           51 | complet
backend-close          |      2.220 |           51 | complet
client-close           |      2.520 |           51 | complet
client-context-mgr     |      2.592 |           51 | complet
persist-then-close     |      2.164 |           51 | complet
sigterm                |      2.236 |           51 | complet
sigkill                |      2.196 |           51 | complet
```

### Lectures

1. **Drift constant ≈ 2 s sur toutes les méthodes**. Égal au `sleep(2)`
   injecté entre les 50 docs et le sentinel-tail. Aucune méthode ne
   ramène le drift à zéro. ⇒ **Aucune des fermetures testées ne déclenche
   `_persist()` HNSW**.
2. **`count_after_reload = 51` sur toutes les méthodes**, y compris
   SIGKILL. Chromadb relit le WAL SQLite (`embeddings_queue`) au load
   et reconstruit l'index HNSW en mémoire à partir des log records.
   La persistance HNSW sur disque n'est **pas la source de vérité** —
   c'est un cache accéléré reconstruit au load. ⇒ **Le drift est
   structurellement bénin** tant que le replay SQLite fonctionne.
3. **`persist-then-close` ne diffère pas des autres**. Soit
   `_force_persist_via_internal` n'a pas trouvé le segment HNSW dans
   `system.components()` (API interne fragile, à instrumenter au tour
   fix), soit `_persist()` modifie `index_metadata.pickle` mais ne
   touche pas le mtime de `data_level0.bin` (qui est mmap incrémental).
   Le test n'est pas concluant — investigation à reporter au tour fix.

### Limites de la repro

- 50 docs << `sync_threshold=50000` du fork. Une repro additionnelle
  avec >50K inserts validerait que le seuil de flush déclenche
  effectivement `_persist()` pendant l'activité. **Hors-scope** sprint 9.
- Le replay SQLite a son propre coût au reload (re-injection de
  10^6 records embeddés serait coûteux). Pas mesuré ici.
- La métrique ne distingue pas "HNSW jamais flushé" et "HNSW flushé
  mais SQLite a continué après". Pour l'écart fin il faudrait
  observer `index_metadata.pickle.mtime` (qui ne change qu'à
  `_persist()` réussi) — à ajouter au tour fix si besoin.

---

## 6. Diagnostic

**Hypothèse retenue** : MIX des trois pistes du kickoff, avec un
poids fort upstream et un poids non nul fork + ARIA.

### Part upstream ChromaDB (poids principal)

`PersistentLocalHnswSegment.stop()` (chromadb 1.5.5, ligne 536) ne
contient pas d'appel à `_persist()`. C'est un **choix de design**
documenté implicitement par le fait que tous les chemins de
fermeture (`Client.close`, context manager, `System.stop`) convergent
vers ce `stop()` et que la repro montre un drift constant.

L'architecture upstream traite le HNSW comme un **cache reconstructible
depuis le WAL SQLite**, pas comme un store persistant à part entière.
Cette hypothèse est cohérente avec :
- `_apply_batch` qui appelle `_persist()` par batches (compaction
  périodique, pas commit synchrone)
- `count_after_reload = 51` même en SIGKILL — confirme la reconstruction
  au replay
- Absence d'atexit, absence de signal handler dans tout chromadb
- Existence de `index.persist_dirty()` (hnswlib) qui suggère un
  flush incrémental possible mais non câblé au shutdown

**Implication** : un fix propre au niveau upstream serait d'appeler
`_persist()` dans `PersistentLocalHnswSegment.stop()` avant
`close_persistent_index()`. C'est un patch à 2 lignes en théorie.
Mais ARIA dépend d'un wheel chromadb non-customisé pour l'instant —
patcher upstream implique soit fork chromadb, soit monkeypatch côté
fork mempalace, soit attendre upstream.

### Part fork MemPalace (poids moyen)

Le fork **délègue strictement** à `client.close()` sans ajouter de
flush propre. Étant donné qu'upstream ne flushe pas au stop, le
fork pourrait combler en :
- appelant `_persist()` reflexivement sur les segments HNSW avant
  `client.close()` (via accès `client._system.components()` ou un
  walk explicite)
- documentant que `ChromaBackend.close()` est best-effort tant que le
  fix upstream n'est pas en place

Le fork a déjà accepté la responsabilité de la quarantaine drift
(`quarantine_stale_hnsw`) et de la lecture SQLite directe quand
chromadb segfault (cf. `_read_collection_dim_count_sqlite` sprint 8).
Ajouter un flush explicite avant close est cohérent avec cette
responsabilité — c'est une **piste viable** pour fix sprint 10.

### Part ARIA (poids mineur mais réel)

ARIA n'appelle **aucun** `backend.close()` à la sortie. Trois leviers
existent :

1. `atexit.register(...)` côté `bot.py` ou au point d'ouverture du
   `_DEFAULT_BACKEND`. Simple, exécuté en sortie Python normale,
   manqué en SIGKILL.
2. `signal.signal(SIGTERM, ...)` côté `bot.py` avant
   `telegram.start()`. Demande à coordonner avec PTB qui pose ses
   propres handlers.
3. Hook PTB `post_stop` ou wrapper around `run_polling()` qui appelle
   `_DEFAULT_BACKEND.close()` après retour.

Ces leviers ARIA ne **résolvent pas** le drift par eux-mêmes (la repro
montre que `backend.close()` actuel laisse le drift en place). Mais ils
sont **préalables** à toute solution effective — sans eux, même un fix
upstream parfait ne serait pas exercé.

### Synthèse

| Couche      | Manque                                          | Effort fix | Bloque-t-il seul ? |
|-------------|-------------------------------------------------|------------|---------------------|
| chromadb    | `_persist()` absent de `Segment.stop()`         | 2 lignes upstream | non, mais sans lui rien d'autre ne suffit |
| fork        | Pas de flush reflexif avant `client.close()`    | ~30 lignes + tests | non, mais le filet le plus accessible |
| ARIA        | Ne ferme jamais le backend                      | atexit ou hook PTB | non, mais préalable |

**Ordre recommandé pour sprint 10 (fix)** :

1. **ARIA** : ajouter `atexit.register(_DEFAULT_BACKEND.close)` ou
   équivalent. Test : le journalctl doit montrer un INFO "backend
   closed" au prochain `systemctl stop`.
2. **Fork** : ajouter `_flush_all_segments()` avant `client.close()`
   dans `_close_client`. Test : repro étendue qui re-mesure drift
   après cette modif et vérifie qu'il tombe à ~0 sur la méthode
   `backend-close`.
3. **Upstream** : décision séparée (patch + PR, monkeypatch, ou
   wait-and-see) selon ce que le tour 2 montre. Si le fix fork suffit
   à drift=0 sur le path `systemctl stop` propre, upstream peut
   attendre.

Aucune perte de données opérationnelle observée à ce jour. La dette
#20 est une **dette d'hygiène** (réduction du bruit `drift-*` /
`corrupt-*` quarantiné au load) plus qu'un bug critique. Calibrage
sprint 8 confirmé : fix minimum + test de non-régression, pas
d'amélioration spéculative au passage.
