# Palace ChromaDB — backend, layout filesystem, lifecycle des segments

**Statut** : doc d'architecture pérenne, hors-sprint. Inaugure
`docs/architecture/` comme emplacement pour la doc structurelle stable
d'ARIA. Critère d'admission du dossier : un sujet structurel stable,
non lié à un sprint particulier, qui mérite d'être trouvé sans avoir
à fouiller les sprints clos.

**Créée** : sprint 11, item #21 (2026-05-19).
**Sources matérielles** (artefacts datés) :
`docs/sprint9/audit_drift_hnsw_metric.md` (backend Rust),
`docs/sprint10/audit_mempalace_artefacts.md` (cartographie filesystem),
`docs/sprint11/audit_fork_mempalace_segment_lifecycle.md` (lecture du
code fork).

---

## Layout filesystem du palace

Le palace ARIA vit dans `~/.mempalace/palace/`. À la racine : la base
sqlite `chroma.sqlite3` (source de vérité pour collections, embeddings,
métadonnées) et un dossier par segment HNSW nommé `<segment_uuid>/`
contenant les binaires d'index (`data_level0.bin`, `link_lists.bin`,
`length.bin`, `header.bin`, `index_metadata.pickle`).

Trois markers cachés à la racine du palace ont valeur de sentinelles
attendues par le fork : `.blob_seq_ids_migrated`,
`.embedder-migration-marker`, `.mempalace-embedder.json`. Ne pas les
supprimer.

Un segment VECTOR peut être référencé en sqlite **sans** dossier en
clair sur disque — c'est l'état observé pour `mempalace_closets`,
expliqué au § Lifecycle. Pour la cartographie exhaustive des artefacts
hors palace actif (`locks/`, `.drift-*` et `.corrupt-*` orphelins,
backups datés), voir `docs/sprint10/audit_mempalace_artefacts.md` § 2.

---

## Backend chromadb-rust (RustBindingsAPI)

Depuis chromadb 1.5.x, l'API par défaut est `RustBindingsAPI`
(`chromadb/config.py:120`). Tous les writes routent vers
`chromadb_rust_bindings.Bindings` directement vers la couche Rust
native, sans passer par le segment manager Python.

Conséquence pour le lecteur de code : `chromadb/segment/impl/vector/
local_persistent_hnsw.py` (`PersistentLocalHnswSegment`,
`LocalSegmentManager`) est **dead code** dans le runtime ARIA. Le lire
pour comprendre la persistance HNSW serait trompeur.
`docs/sprint9/audit_drift_hnsw_metric.md` § TL;DR démontre
empiriquement (`LocalSegmentManager._instances` vide après 51 add()) que
ce chemin n'est jamais exercé.

> `docs/sprint9/audit_drift_hnsw.md` § 2 décrit le chemin Python comme
> actif — passage invalidé par son propre complément `_metric`. Toute
> citation de `audit_drift_hnsw.md` § 2 doit s'accompagner du renvoi
> au `_metric`.

---

## Propriété observable : pas de FD persistant

ChromaDB 1.5.5 n'ouvre **aucun FD persistant** sur `chroma.sqlite3`
ni sur les fichiers HNSW au repos comme en service actif. La base est
ouverte à chaque requête puis refermée immédiatement. Trois signaux
convergents (cf. `docs/sprint10/audit_mempalace_artefacts.md` § 3) :
`journal_mode = delete` ; `chroma.sqlite3-wal` et `-shm` absents au
repos ; zéro entrée pointant sur `.mempalace/` dans `/proc/<pid>/fd`
du process `aria.service`.

**Conséquence opérationnelle de premier ordre** : `lsof` est
structurellement inadéquat pour observer ce backend. On ne verra
jamais un FD persistant, même sous charge, sauf à intercepter la
fenêtre courte d'une requête en vol. Toute observation runtime du
palace doit passer par `strace -e openat,read,write` ou par
instrumentation Python dans le process ARIA. Un audit qui se contente
d'un `lsof` rend un verdict vide-par-construction, pas un verdict
d'inactivité.

---

## Lifecycle des segments

Le fork MemPalace ne crée jamais lui-même un dossier segment HNSW.
Le seul `mkdir` du backend (`mempalace/backends/chroma.py:1367`)
concerne le `palace_path` racine. La (re)création des dossiers
`<segment_uuid>/` est entièrement déléguée à chromadb-rust via
`chromadb.PersistentClient(path=palace_path)`.

**Création initiale** : un dossier segment apparaît à l'insertion de
la première entrée dans la collection — mécanisme chromadb-rust
upstream, non documenté plus avant ici.

**Re-matérialisation au cold-start** : **inférence par élimination**,
preuve runtime directe non faite. Le constat empirique
(cf. `docs/sprint11/audit_fork_mempalace_segment_lifecycle.md` § 5,
verdict C) est que pour `mempalace_closets`, dont l'UUID segment
`3b1fb30f-…` est référencé en sqlite mais sans écriture depuis sprint
4, trois dossiers `.drift-*` distincts ont été produits par le fork
à trois cold-starts successifs. Pour que trois renommages aient pu
avoir lieu, un dossier clean avec `data_level0.bin` a dû exister puis
disparaître par renommage à chaque fois. Aucun code applicatif ne le
crée. Le mécanisme cohérent est donc une re-matérialisation au
cold-start par chromadb-rust pour chaque segment VECTOR référencé en
sqlite, indépendamment de toute écriture applicative.

Cette lecture reste non vérifiée directement. Une preuve runtime
(`strace -e openat,mkdir` sur le démarrage ARIA, ou lecture du code
Rust de `chromadb_rust_bindings`) trancherait définitivement. Pas
nécessaire pour le fonctionnement courant ; le deviendrait si un
débogage futur révélait un comportement contradictoire.

---

## Mécanismes de quarantine du fork MemPalace

Deux mécanismes distincts, à ne pas confondre. Les deux sont des
pré-checks cold-start appelés par
`ChromaBackend._prepare_palace_for_open()` **avant** l'instanciation
du `PersistentClient`, et gates par `_quarantined_paths` pour ne
tourner qu'une fois par palace par process.

### `.drift-<TS>`

`quarantine_stale_hnsw` (`mempalace/backends/chroma.py` lignes
238-335). Pour un dossier segment contenant `data_level0.bin`, le
rename se produit **si et seulement si** : ratio
`link_lists.bin / data_level0.bin > 10x` (corruption structurelle de
payload), **ou** `sqlite_mtime − hnsw_mtime ≥ 300s` couplé à un échec
de l'integrity check sur `index_metadata.pickle` (sniff des octets
`0x80…0x2e`, sans désérialisation). Si le dossier n'a pas de
`data_level0.bin`, la fonction le saute. Le gate `_quarantined_paths`
empêche tout re-firing en runtime — ARIA n'utilise pas
`palace-daemon._auto_repair`, donc en pratique le rename ne peut
survenir qu'au cold-start.

> `docs/sprint10/audit_mempalace_artefacts.md` § 2.2 formule le
> déclencheur comme « count HNSW différent du count sqlite ».
> Formulation imprécise : le vrai déclencheur est le gap mtime
> couplé à l'integrity check décrit ci-dessus. Pour le mécanisme
> réel, voir `docs/sprint11/audit_fork_mempalace_segment_lifecycle.md`
> § 2 qui cite intégralement la fonction.

### `.corrupt-<TS>`

`quarantine_invalid_hnsw_metadata` (lignes 697-775). Déclencheur :
l'`index_metadata.pickle` est désérialisable en mode whitelist
(`_SafePersistentDataUnpickler`, classe unique autorisée :
`chromadb.segment.impl.vector.local_persistent_hnsw.PersistentData`)
**mais** la validation logique échoue (`dimensionality` absente ou
≤ 0 alors que `id_to_label` n'est pas vide, ou type inattendu pour
`id_to_label`). Les erreurs transitoires (pickle tronqué, lecture
interrompue) ne déclenchent pas le rename. À la différence des
`.drift-*`, les `.corrupt-<TS>` conservent leur `index_metadata.pickle`
— trace exploitable pour forensic ultérieur.

---

## Implications opérationnelles

Diagnostic palace : `strace -e openat,read,write,unlink,rename` et
instrumentation Python en process. `lsof` à proscrire pour conclure
sur l'activité du palace.

Hygiène : les dossiers `.drift-*` et `.corrupt-*` sont des artefacts
du fork, pas du palace actif ; aucune lecture en production ne s'y
appuie ; purgeables sans risque filesystem-side dès lors qu'on n'a
plus besoin de la trace forensic (cf. la purge ciblée sprint 10
dette #22).

Audit futur : avant toute conclusion du type « ARIA tient un FD sur
le palace » ou « le palace n'a pas écrit depuis X », vérifier que
l'outil utilisé est compatible avec le backend Rust. Une absence de
FD sous `lsof` ne dit rien d'une absence d'écriture ; un mtime figé
sur `data_level0.bin` ne dit rien de l'inactivité de la collection
si elle a été migrée d'embedder entretemps.
