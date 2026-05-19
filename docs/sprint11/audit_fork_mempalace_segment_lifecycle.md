# Sprint 11 — Item #21 — Tour 2 : audit fork MemPalace (lifecycle segment)

**Date** : 2026-05-19
**Branche** : `feat/sprint11-closets-doc` (continuité du tour 1)
**Mode** : audit lecture seule du fork MemPalace, aucune mutation
**Question pivot** : trancher lecture A vs B du §6.1 de
`docs/sprint10/audit_mempalace_artefacts.md` sur la (non-)matérialisation
du dossier segment `3b1fb30f-…` (collection `mempalace_closets`).

---

## Section 1 — Localisation du fork

### Chemin et version

```
$ ./venv/bin/python -c "import mempalace; print(mempalace.__file__)"
/home/nico/Nextcloud/projects/mempalace-fork/mempalace/__init__.py

$ ./venv/bin/python -c "import mempalace; print(mempalace.__version__)"
3.3.5
```

Installation editable (`pip install -e`) sur clone git
`/home/nico/Nextcloud/projects/mempalace-fork/`.

### État git du fork

```
HEAD : b8caf3259021d27c2689928458ac02d5a0defd01
Date : 2026-05-13 18:41:26 +0200
Branche : feat/configurable-embedder
Message : feat(embedding): configurable embedder via model_name parameter
```

Aligné avec le commit cité par `runbook_t_mempalace_live.md` (sprint 7)
comme version live prod.

### Arborescence racine pertinente

Package Python `mempalace/` :

```
mempalace/
├── backends/
│   ├── __init__.py
│   ├── base.py          (12 Ko, contrats BaseBackend/BaseCollection)
│   ├── chroma.py        (62 Ko, ChromaBackend — cible de cet audit)
│   └── registry.py      (6 Ko, dispatch)
├── palace.py            (lock/path management)
├── searcher.py
├── repair.py
└── … (33 autres modules, hors scope)
```

`mempalace/backends/chroma.py` est le seul module qui interagit avec
chromadb. Tout le code de quarantine y est concentré.

### Dépendance chromadb

```
$ ./venv/bin/python -c "import chromadb; print(chromadb.__version__)"
1.5.5
```

(Confirmé via lecture indirecte du sprint 9 audit, cohérent avec
audit_drift_hnsw_metric §1.)

---

## Section 2 — Code matérialisant `.drift-<TS>`

### Localisation

`mempalace/backends/chroma.py`, fonction `quarantine_stale_hnsw`
(lignes 238-335). Appelée une seule fois par
`ChromaBackend._prepare_palace_for_open()` au cold-start (lignes
1289-1317), gated par `ChromaBackend._quarantined_paths` (une
fois par palace par process).

### Code intégral (lignes 238-335)

```python
def quarantine_stale_hnsw(palace_path: str, stale_seconds: float = 300.0) -> list[str]:
    """Rename HNSW segment dirs that look unsafe to open.

    This catches two classes of HNSW corruption before ChromaDB opens the
    native segment reader:

    1. stale-by-mtime segments whose ``index_metadata.pickle`` fails the
       existing format sniff-test;
    2. structurally impossible HNSW payloads where ``link_lists.bin`` is much
       larger than ``data_level0.bin``.

    The second check is intentionally not gated by mtime. A segment with a
    300x link/data ratio is unsafe regardless of whether its mtime is recent;
    letting Chroma open it can SIGSEGV before Python fallback code runs.

    The original directory is renamed, not deleted, so recovery remains
    possible if the heuristic ever misfires.
    """

    db_path = os.path.join(palace_path, "chroma.sqlite3")
    if not os.path.isfile(db_path):
        return []

    try:
        sqlite_mtime = os.path.getmtime(db_path)
    except OSError:
        return []

    moved: list[str] = []

    try:
        entries = os.listdir(palace_path)
    except OSError:
        return []

    for name in entries:
        if "-" not in name or name.startswith(".") or ".drift-" in name:
            continue

        seg_dir = os.path.join(palace_path, name)
        if not os.path.isdir(seg_dir):
            continue

        hnsw_bin = os.path.join(seg_dir, "data_level0.bin")
        if not os.path.isfile(hnsw_bin):
            continue

        try:
            hnsw_mtime = os.path.getmtime(hnsw_bin)
        except OSError:
            continue

        payload_ratio = _hnsw_link_to_data_ratio(seg_dir)
        payload_corrupt = payload_ratio is not None and payload_ratio > _HNSW_LINK_TO_DATA_MAX_RATIO

        if not payload_corrupt and sqlite_mtime - hnsw_mtime < stale_seconds:
            continue

        # Stage 2: integrity gate. Mtime drift alone is not corruption because
        # Chroma flushes HNSW asynchronously. A healthy metadata file proves the
        # ordinary stale-by-mtime case is just flush lag.
        if not payload_corrupt and _segment_appears_healthy(seg_dir):
            logger.info(
                "HNSW mtime gap %.0fs on %s exceeds threshold but segment "
                "metadata and payload size are intact — flush-lag, not "
                "corruption. Leaving in place.",
                sqlite_mtime - hnsw_mtime,
                seg_dir,
            )
            continue

        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = f"{seg_dir}.drift-{stamp}"

        if payload_corrupt:
            reason = (
                f"link_lists.bin/data_level0.bin ratio {payload_ratio:.1f}x "
                f"exceeds {_HNSW_LINK_TO_DATA_MAX_RATIO:.1f}x"
            )
        else:
            reason = (
                f"sqlite {sqlite_mtime - hnsw_mtime:.0f}s newer than HNSW "
                "and integrity check failed"
            )

        try:
            os.rename(seg_dir, target)
            moved.append(target)
            logger.warning(
                "Quarantined corrupt HNSW segment %s (%s); renamed to %s",
                seg_dir,
                reason,
                target,
            )
        except OSError:
            logger.exception("Failed to quarantine corrupt HNSW segment %s", seg_dir)

    return moved
```

### Conditions de déclenchement (extraites du code)

Un dossier `<name>` est renommé `<name>.drift-<TS>` **si et seulement si**
toutes les conditions ci-dessous sont vraies :

1. `name` contient `-` (heuristique UUID), ne commence pas par `.`,
   ne contient pas déjà `.drift-` (ligne 274).
2. `<palace>/<name>/` est un dossier (ligne 278).
3. `<palace>/<name>/data_level0.bin` existe (ligne 282-283). **Si
   absent → skip**.
4. ET une des deux sous-conditions :
   - `payload_corrupt` : ratio `link_lists.bin / data_level0.bin` >
     `_HNSW_LINK_TO_DATA_MAX_RATIO` (=10.0) — ligne 290-291.
   - `sqlite_mtime - hnsw_mtime >= stale_seconds` (=300s) **ET**
     `_segment_appears_healthy(seg_dir)` retourne False (lignes
     293-307). L'integrity check sniffe `index_metadata.pickle`
     (premier octet `0x80`, dernier octet `0x2e`, taille ≥ 16
     bytes) sans le désérialiser.

### Caller unique

```
mempalace/backends/chroma.py:1316
    quarantine_stale_hnsw(palace_path)
```

Appelé depuis `ChromaBackend._prepare_palace_for_open()` (ligne 1290),
qui est lui-même invoqué par `make_client()` (ligne 1319+) et par
le path interne `_client()` (ligne 1253). Gate `_quarantined_paths`
ligne 1314 : la fonction ne tourne **qu'une fois par palace par
process**.

Note de l'auteur du fork sur le gate (lignes 1266-1287) :

> The proactive HNSW checks are a *cold-start* protection […]. Once a
> long-running process has opened the palace cleanly, re-firing the stale
> check on every reconnect is a *runtime thrash* […]. Real runtime drift is
> still handled — palace-daemon's `_auto_repair` calls
> `quarantine_stale_hnsw` directly on observed HNSW errors, which bypasses
> this gate.

ARIA n'utilise pas `palace-daemon` — donc pour ARIA, `quarantine_stale_hnsw`
ne tourne **que** au cold-start du process, jamais en runtime.

---

## Section 3 — Code matérialisant `.corrupt-<TS>`

### Localisation

`mempalace/backends/chroma.py`, fonction `quarantine_invalid_hnsw_metadata`
(lignes 697-775). Appelée juste avant `quarantine_stale_hnsw` dans
`_prepare_palace_for_open` (ligne 1315).

### Code intégral (lignes 697-775)

```python
def quarantine_invalid_hnsw_metadata(palace_path: str) -> list[str]:
    """Quarantine segment dirs whose ``index_metadata.pickle`` is unreadable or invalid.

    Chroma's persisted HNSW metadata is untrusted disk state. If a segment has
    labels but no valid positive dimensionality, current Chroma versions can
    accept the pickle and crash later in the Rust loader. We rename the entire
    segment out of the way before ``PersistentClient`` opens so Chroma can
    rebuild cleanly instead of touching known-bad metadata.
    """
    try:
        entries = os.listdir(palace_path)
    except OSError:
        return []

    moved: list[str] = []
    for name in entries:
        if "-" not in name or name.startswith(".") or ".drift-" in name or ".corrupt-" in name:
            continue
        seg_dir = os.path.join(palace_path, name)
        if not os.path.isdir(seg_dir):
            continue

        meta_path = os.path.join(seg_dir, "index_metadata.pickle")
        if not os.path.isfile(meta_path):
            continue

        reason = None
        try:
            persisted = _SafePersistentDataUnpickler.load(meta_path)
        except (EOFError, OSError):
            logger.debug(
                "Skipping invalid-HNSW quarantine for transient metadata read in %s",
                meta_path,
                exc_info=True,
            )
            continue
        except pickle.UnpicklingError as exc:
            if "truncated" in str(exc).lower() or "ran out of input" in str(exc).lower():
                logger.debug(
                    "Skipping invalid-HNSW quarantine for transient metadata read in %s",
                    meta_path,
                    exc_info=True,
                )
                continue
            reason = f"invalid index_metadata.pickle: {exc}"
        except Exception as exc:
            reason = f"invalid index_metadata.pickle: {exc}"
        else:
            if not isinstance(persisted, dict) and not (
                hasattr(persisted, "dimensionality") or hasattr(persisted, "id_to_label")
            ):
                reason = f"unrecognized index_metadata.pickle payload: {type(persisted).__name__}"
            else:
                dimensionality, id_to_label = _persisted_metadata_fields(persisted)
                if id_to_label is not None and not isinstance(id_to_label, dict):
                    reason = f"invalid id_to_label type {type(id_to_label).__name__}"
                else:
                    has_labels = bool(id_to_label)
                    if has_labels and not _valid_dimensionality(dimensionality):
                        reason = (
                            "labels present but dimensionality is missing or invalid "
                            f"({dimensionality!r})"
                        )
                    elif dimensionality is not None and not _valid_dimensionality(dimensionality):
                        reason = f"invalid dimensionality {dimensionality!r}"

        if reason is None:
            continue

        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = f"{seg_dir}.corrupt-{stamp}"
        try:
            os.rename(seg_dir, target)
            moved.append(target)
            logger.warning("Quarantined invalid HNSW metadata in %s: %s", seg_dir, reason)
        except OSError:
            logger.exception("Failed to quarantine invalid HNSW metadata in %s", seg_dir)

    return moved
```

### Conditions de déclenchement

1. `name` contient `-`, ne commence pas par `.`, ne contient pas déjà
   `.drift-` ni `.corrupt-` (ligne 713).
2. Le dossier existe (ligne 716).
3. `index_metadata.pickle` existe (ligne 720). **Si absent → skip**
   (contrairement à `.drift-*` qui regarde `data_level0.bin`).
4. Le pickle est désérialisable en mode whitelist (`_SafePersistentDataUnpickler`,
   ligne 392-426 — accepte uniquement `PersistentData` de chromadb)
   ET passe la validation `dimensionality > 0` quand
   `id_to_label` est non vide.

Si le pickle est *transitoirement* tronqué (EOF / pickle truncated), on
**skip** (lignes 727-740) — pas de rename — pour éviter de quarantine
un segment encore en cours d'écriture.

### Caller unique

```
mempalace/backends/chroma.py:1315
    quarantine_invalid_hnsw_metadata(palace_path)
```

Même call-site que `quarantine_stale_hnsw` (cf. §2). Tourne juste avant.

---

## Section 4 — Code de (re)création du dossier segment

### Recherche `mkdir` / `makedirs` dans le fork

`grep -rnE "mkdir|makedirs" --include="*.py" mempalace/backends/` :

```
mempalace/backends/chroma.py:1367:            os.makedirs(palace_path, exist_ok=True)
```

**Une seule occurrence**, et elle concerne le **dossier palace racine**
(`~/.mempalace/palace/`), pas un dossier segment. Lecture du contexte
(ligne 1367 dans `make_client`) :

```python
@staticmethod
def make_client(palace_path: str):
    [...]
    os.makedirs(palace_path, exist_ok=True)
    [...]
    return chromadb.PersistentClient(path=palace_path)
```

### Conclusion sur la création de dossiers segment

**Le fork MemPalace ne crée aucun dossier segment HNSW**. Ni
`quarantine_stale_hnsw`, ni `quarantine_invalid_hnsw_metadata`, ni
`ChromaBackend.get_collection` n'appellent jamais `mkdir` /
`makedirs` sur un sous-dossier UUID.

La création (ou non-création) des dossiers `<segment_uuid>/` est
**entièrement déléguée à chromadb**, qui depuis 1.5.x route les
writes via `RustBindingsAPI` → `chromadb_rust_bindings.Bindings`
(cf. `docs/sprint9/audit_drift_hnsw_metric.md` §TL;DR).

**Point de délégation explicite** :

```
mempalace/backends/chroma.py:1254
    cached = chromadb.PersistentClient(path=palace_path)

mempalace/backends/chroma.py:1332
    return chromadb.PersistentClient(path=palace_path)

mempalace/backends/chroma.py:1395 / 1397 / 1407
    collection = client.get_collection(collection_name, **ef_kwargs)
    collection = client.create_collection(...)
```

Conformément à la consigne du brief (« on s'arrête au binding,
inutile de lire le code Rust upstream »), l'investigation s'arrête
ici sur la création de dossier. Ce qui suit dans la chaîne d'appels
est en Rust dans `chromadb_rust_bindings` — hors scope.

### Implication structurelle

Tout ce que l'on peut affirmer **filesystem-only** sur la création
de dossiers segment :

- Le fork ne les crée jamais explicitement.
- Le fork *présuppose* qu'ils peuvent exister (la quarantine les
  liste et les renomme).
- Une preuve indirecte de matérialisation par chromadb-rust se déduit
  de §5 ci-dessous (la seule façon dont 3 `.drift-*` consécutifs ont
  pu apparaître pour `3b1fb30f`).

---

## Section 5 — Verdict A vs B (et lecture C émergente)

### Préambule : reformulation rigoureuse des deux lectures

L'audit sprint 10 §6.1 propose :

- **Lecture A** : « Rust HNSW ne crée le dossier qu'à la première
  écriture post-démarrage, et `mempalace_closets` n'est plus jamais
  écrit depuis sprint 4. »
- **Lecture B** : « le dossier a été renommé en `.drift-*` à chaque
  démarrage successif sans que le Rust ait recréé un dossier clean. »

Observation factuelle sprint 10 (§2.1 + §2.2) :
- `mempalace_closets` est référencé en sqlite avec segment
  `3b1fb30f-7da4-43f1-969e-f0b180ca92e3`.
- Aucun dossier `palace/3b1fb30f-…/` clean sur disque.
- **Trois** `.drift-*` distincts pour `3b1fb30f` dans le palace actif :
  `…drift-20260513-180821/`, `…drift-20260517-221838/`,
  `…drift-20260518-101422/` (168 K chacun).

### Réfutation de A

Si A était vraie (« Rust ne crée le dossier qu'à la première
écriture »), et que `mempalace_closets` n'a aucune écriture depuis
sprint 4, alors **aucun dossier `3b1fb30f-…` n'aurait jamais
existé**. Or `quarantine_stale_hnsw` (§2) ne renomme qu'un dossier
préexistant contenant `data_level0.bin` (ligne 282-283 : `if not
os.path.isfile(hnsw_bin): continue`). L'existence de **trois**
`.drift-*` distincts pour `3b1fb30f`, à trois dates différentes,
prouve que **trois fois** un dossier clean `3b1fb30f-…/` avec
`data_level0.bin` a existé, puis a été renommé.

⇒ **Lecture A est invalidée**.

### Réfutation de B

Si B était vraie (« renommé à chaque démarrage sans que le Rust
recrée »), alors après le premier rename du 13 mai, il n'y aurait
plus de dossier clean `3b1fb30f-…/` à renommer. Les deux `.drift-*`
suivants (17 mai, 18 mai) n'auraient pas pu apparaître.

⇒ **Lecture B est aussi invalidée** dans sa formulation littérale.
Une variante de B (« le Rust recrée puis le fork renomme à chaque
démarrage ») est partiellement compatible avec les faits, mais
échoue sur la fréquence : ARIA tourne en service systemd depuis
sprint 7, il y a eu des dizaines de démarrages, et **seuls trois**
`.drift-*` sont apparus, tous timestampés à des bascules
documentées (cf. sprint10 §2.2).

### Lecture C (émergente, tranchée)

Le mécanisme effectif est :

1. **chromadb-rust matérialise les dossiers segment au cold-start**
   pour chaque segment VECTOR référencé en sqlite, indépendamment
   d'écritures applicatives. Ces dossiers contiennent au minimum
   `data_level0.bin` (preuve filesystem : `quarantine_stale_hnsw`
   skip si absent, mais les `.drift-*` produits font 168 K et le
   sprint 10 §2.2 atteste de leur taille — donc `data_level0.bin`
   était là avant le rename).
2. **Le fork MemPalace renomme `.drift-<TS>` uniquement quand
   `sqlite_mtime - hnsw_mtime >= 300s` ET l'integrity check
   `_segment_appears_healthy` échoue** (cf. §2 conditions 4b). Ce
   n'est PAS « count HNSW ≠ count sqlite » comme le suggérait
   l'audit sprint 10 §2.2 (formulation à corriger dans la doc
   pérenne).
3. **Le gap mtime n'apparaît que dans des contextes précis** :
   - restauration d'un backup (sqlite_mtime reset à l'extraction,
     hnsw_mtime conservé de l'archive) ;
   - bascule d'embedder où chromadb réécrit la sqlite (nouveaux
     embeddings) sans toucher au segment HNSW de l'ancienne
     collection (closets en l'occurrence).
4. **En fonctionnement normal**, ARIA n'écrit pas dans
   `mempalace_closets` (0 caller prod, cf. CLAUDE.md « Couches
   mémoire »), donc sqlite_mtime de la base ne bouge pas du fait
   de closets — il bouge à cause des writes drawers. Si les writes
   drawers se font sans gap > 300s par rapport au mtime de
   `data_level0.bin` du dossier closets… mais ce dernier ne bouge
   jamais. Donc à terme on devrait dériver — sauf que le **gate
   `_quarantined_paths` (ligne 1314)** empêche `quarantine_stale_hnsw`
   de re-tourner dans le même process. Donc le rename ne peut se
   produire qu'**au cold-start** (un nouveau process).
5. Les trois timestamps des `.drift-*` actifs correspondent
   exactement aux trois bascules documentées : rollback test
   13 mai 18:08, bascule préprod #1 17 mai 22:18, bascule prod
   finale 18 mai 10:14 (cf. sprint10 §2.2). Chacune est un cold-start
   avec gap mtime massif.

**Verdict tranché** : ni A ni B au sens littéral. Le mécanisme réel
est **C** :

> chromadb-rust matérialise un dossier segment au cold-start pour
> chaque segment VECTOR référencé en sqlite ; le fork MemPalace
> renomme ce dossier `.drift-<TS>` à un cold-start ultérieur quand
> et seulement quand le mtime sqlite est ≥ 300s plus récent que le
> mtime de `data_level0.bin` ET l'integrity check du pickle échoue.
> Pour `mempalace_closets` (collection jamais réécrite), cela ne se
> produit qu'aux cold-starts qui suivent une migration ou un
> restore — pas à chaque démarrage normal.

### Hypothèse C ne sera pas davantage investiguée ce tour

Conformément au brief, la confirmation **directe** que chromadb-rust
matérialise le dossier au cold-start nécessiterait soit (a) une
instrumentation runtime (`strace -e openat,mkdir` sur le démarrage
ARIA), soit (b) une lecture du code Rust de `chromadb_rust_bindings`.
**Ni l'un ni l'autre n'est conduit ici** — la preuve indirecte
(existence de trois `.drift-*` consécutifs) est jugée suffisante pour
trancher au niveau requis par la dette #21. Le tour 3 décidera si la
doc pérenne mentionne C comme « inférence solide » ou exige une
preuve runtime.

### Note sur la formulation sprint 10 §2.2 à corriger en tour 3

Sprint 10 §2.2 dit : « le fork MemPalace renomme un dossier HNSW en
`.drift-<TS>` quand il détecte au démarrage que le count HNSW
diffère du count sqlite pour ce segment ». Le code (§2 de cet audit,
ligne 293) montre que c'est en réalité un **mtime gap** sur
`data_level0.bin` + integrity check, **pas** un count delta. La
fonction `_hnsw_element_count` existe (ligne 429+ de `chroma.py`)
mais n'est pas appelée par `quarantine_stale_hnsw` au cold-start.
Le tour 3 corrigera cette formulation dans la doc pérenne ;
l'audit sprint 10 est posé, on ne le réécrit pas.

---

## Section 6 — Implications pour le tour 3 (note préparatoire)

À consommer dans `docs/architecture/chromadb_palace.md` (tour 3) :

- Citer §2 (extrait conditions 1-4 de `quarantine_stale_hnsw`) et §3
  (idem `quarantine_invalid_hnsw_metadata`) comme **mécanique
  pérenne** du palace.
- Citer §4 (fork ne crée pas les dossiers segment → délégation
  chromadb-rust) comme propriété structurelle du backend.
- Citer §5 verdict C comme **réponse à la question A/B** posée par
  sprint 10 §6.1, en explicitant que la formulation initiale §2.2
  sprint 10 (« count HNSW vs count sqlite ») est à remplacer par
  « mtime gap + integrity check ».

À garder uniquement dans cet audit daté (pas dans la doc pérenne) :

- Les hashes git / chemins absolus (`/home/nico/Nextcloud/…`,
  commit `b8caf32`) — datés.
- La réfutation détaillée de A et B (utile pour la traçabilité
  archéologique mais sans valeur pédagogique pour un lecteur futur
  qui n'a pas vu sprint 10 §6.1).
