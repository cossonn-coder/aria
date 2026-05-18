# Audit `scripts/migrate_embedder.py` — appels HNSW-dépendants

**Sprint 7 / phase 2, tour 6.** Audit pré-fix, sans modification de code.

**Contexte.** Le tour T-Mempalace-Preprod a échoué à l'Étape B du
script avec `chromadb.errors.InternalError: Error finding id`
parce que le palace copié à chaud héritait du drift sqlite/HNSW
côté prod et que le fork MemPalace avait quarantained les
segments dégradés à l'ouverture. La fonction
`collection.peek(limit=1)` (ligne 244) tente de lire l'embedding
d'un sample, ce qui touche l'index HNSW. Sur un palace avec
segments quarantained, cet appel raise.

Ce document inventorie tous les appels du script qui peuvent
toucher l'index HNSW, donne le code intégral des fonctions
concernées, confirme par lecture du fork et de chromadb quelles
informations sur la collection sont récupérables en SQLite-only,
et liste les pistes de fix sans rédiger le fix lui-même.

---

## Section 1 — Inventaire des appels HNSW-dépendants

Le script ouvre `chromadb.PersistentClient(path=...)` directement
au lieu de passer par l'API fork
(`mempalace.palace.get_collection`) — c'est intentionnel côté
script de migration (il manipule la collection bas-niveau pour
delete/recreate, opérations que le wrapper fork ne propose pas
sur sa surface publique). Les objets `collection` manipulés
sont donc des `chromadb.api.models.Collection.Collection` bruts.

**Convention de classification :**
- **HNSW-required** : l'appel demande au backend une opération
  qui implique le segment vecteur sur disque (HNSW index +
  blob embeddings). Échoue sur palace avec segments quarantained.
- **SQLite-only** : l'appel se résout entièrement par la base
  `chroma.sqlite3` (collections, segments, embeddings table,
  embedding_metadata, etc.). Insensible à l'état HNSW.

### Tableau récapitulatif

| # | Étape | Ligne | Appel | Catégorie | Finalité | Alternative SQLite-only |
|---|---|---|---|---|---|---|
| 1 | A | 205-206 | `tarfile.open(...).add(palace_path, ...)` | Filesystem | Snapshot tar.gz du répertoire palace. Lit tous les fichiers du palace mais c'est de l'I/O filesystem, pas une opération chromadb. | n/a (intentionnellement filesystem). |
| 2 | B | 233 | `collection.count()` | **SQLite-only** | Compter les entrées avant migration. | Idem. |
| 3 | B | 244 | `collection.peek(limit=1)` | **HNSW-required** ⚠ | Lire un embedding sample pour en déduire la dim actuelle, puis cohérence avec `from-model`. | Lecture directe de `collections.dimension` en SQL (cf. Section 3) ; ou `collection.get(limit=1, include=["documents","metadatas"])` sans embeddings + dim depuis SQLite ; ou même `_expected_dim(from_model)` sans interroger la collection (la dim source est *connue* puisque c'est l'argument CLI). |
| 4 | C (check) | 281, 284-285 | `marker_path.exists()`, `marker_path.read_text(...)` | Filesystem | Idempotence via fichier marker `.embedder-migration-marker`. | n/a (filesystem). |
| 5 | D | 366 | `collection.count()` | **SQLite-only** | Borne haute de la pagination. | Idem. |
| 6 | D | 376-380 | `collection.get(limit=PAGE, offset=..., include=["documents","metadatas"])` | **SQLite-only** ✓ | Lire tous les ids, documents et metadatas pour les ré-encoder. Crucially, `"embeddings"` n'est PAS dans include — donc le rust binding ne touche pas l'HNSW. | Idem (déjà optimal). |
| 7 | E | 465 | `client.delete_collection(COLLECTION_NAME)` | **Écriture** | Drop de la collection (et de ses segments). | n/a (intention de détruire). |
| 8 | E | 471-474, 481 | `client.create_collection(...)` | **Écriture** | Recréation de la collection avec un nouveau segment HNSW vierge. | n/a (intention de créer). |
| 9 | E | 491-496 | `collection.add(ids=..., embeddings=..., documents=..., metadatas=...)` | **Écriture** | Insertion des nouveaux vecteurs mpnet ; chromadb construit l'HNSW sain. | n/a. |
| 10 | F | 513 | `client.get_collection(COLLECTION_NAME)` | Pas d'I/O HNSW immédiate | Récupère le handle de la nouvelle collection. | n/a (lazy, pas d'I/O HNSW à ce point). |
| 11 | F | 514 | `collection.count()` | **SQLite-only** | Vérifier count préservé. | Idem. |
| 12 | F | 528 | `collection.peek(limit=1)` | **HNSW-required** ⚠ | Vérifier dim post-migration (768). Mais la collection vient juste d'être recréée à l'étape E, donc l'HNSW est sain par construction — pas le même risque qu'à l'étape B. | Lecture de `collections.dimension` en SQL (cf. Section 3) ; cohérent avec ce qu'on ferait pour étape B. |
| 13 | G | 322-330 | `marker_path.write_text(...)` × 2 | Filesystem | Écriture des deux markers (`.embedder-migration-marker` et `.mempalace-embedder.json`). | n/a. |
| 14 | main | 802 | `chromadb.PersistentClient(path=...)` | SQLite + segments catalog | Ouverture du client persistant. Charge SQLite et énumère les segments via le catalog ; ne charge pas l'HNSW en mémoire (lazy). Sur le palace prod cette ouverture déclenche ce qui se déclenche côté fork — et c'est précisément l'endroit où la quarantaine des segments dérivés se produit (`fork chroma.py` — pas dans ce script). | n/a, intrinsèque. |
| 15 | main | 810 | `client.get_collection(COLLECTION_NAME)` | Pas d'I/O HNSW immédiate | Récupère le handle source. | n/a. |
| 16 | main | 825-840 | bloc rollback / try/except autour de E+F | n/a | Encadre l'écriture pour permettre le rollback depuis snapshot. | n/a. |

### Synthèse

Deux appels HNSW-required dans tout le script : **étape B
ligne 244** et **étape F ligne 528**. Tous les deux sont des
`collection.peek(limit=1)` dont la finalité est la même —
déduire la dim des vecteurs.

- **Étape B (244)** : c'est le bloqueur sur palace dégradé.
  L'appel n'est pas *fonctionnellement* nécessaire : la dim
  source est déjà connue (`from_model` est un argument CLI avec
  default `all-MiniLM-L6-v2`, mappé à 384 par `_expected_dim`).
  Le peek sert uniquement à *valider* la cohérence entre la
  dim réellement stockée et la dim déclarée. C'est un check de
  sécurité, pas une dépendance fonctionnelle.
- **Étape F (528)** : appel sur la collection juste recréée à
  l'étape E. L'HNSW est vierge et sain par construction (un
  delete_collection a effacé l'ancien, create_collection a
  bâti un nouveau). Risque empirique très faible, mais on
  pourrait le supprimer aussi par cohérence.

**Aucun appel FONCTIONNELLEMENT HNSW-required** dans le script :
les deux peek() sont des validations dont la finalité (dim) est
récupérable autrement (Section 3).

---

## Section 2 — Code intégral des fonctions touchées

### Constantes et utilitaires (lignes 126-183)

```python
# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
COLLECTION_NAME = "mempalace_drawers"
MARKER_FILENAME = ".embedder-migration-marker"

# Marker side-channel introduit par le fork MemPalace (T-Mempalace-Patch,
# commit b8caf32). Écrit à la racine du palace, lu par
# ChromaBackend._resolve_embedding_function pour réinstancier la bonne
# sentence-transformers EF à l'ouverture. Sans lui, le fork retombe sur le
# default MiniLM 384 et plante sur la première query (dim 768 vs 384).
MEMPALACE_EMBEDDER_MARKER_FILENAME = ".mempalace-embedder.json"
MEMPALACE_EMBEDDER_MARKER_VERSION = 1

# Dimensions attendues par modèle (source de vérité locale, sans appel réseau)
MODEL_EXPECTED_DIM: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": 768,
    "paraphrase-multilingual-mpnet-base-v2": 768,
}

BATCH_SIZE = 32  # taille de batch pour l'encodage et l'insertion ChromaDB


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    """Retourne le hash SHA-256 hex d'une chaîne UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_palace(path_str: str) -> Path:
    """Résout le chemin palace (gère le ~ initial)."""
    return Path(path_str).expanduser().resolve()


def _expected_dim(model_name: str) -> int:
    """
    Retourne la dimension attendue pour un modèle connu.
    Lève ValueError si le modèle est inconnu du registre local.
    """
    if model_name in MODEL_EXPECTED_DIM:
        return MODEL_EXPECTED_DIM[model_name]
    # Essai avec préfixe sentence-transformers/ ajouté ou retiré
    alt = (
        f"sentence-transformers/{model_name}"
        if not model_name.startswith("sentence-transformers/")
        else model_name.split("/", 1)[1]
    )
    if alt in MODEL_EXPECTED_DIM:
        return MODEL_EXPECTED_DIM[alt]
    raise ValueError(
        f"Modèle '{model_name}' inconnu du registre local. "
        f"Modèles connus : {list(MODEL_EXPECTED_DIM.keys())}"
    )
```

### `etape_a_snapshot` (lignes 190-218)

```python
def etape_a_snapshot(palace_path: Path, dry_run: bool) -> Path | None:
    """
    Crée un snapshot tar.gz horodaté du répertoire palace.
    Retourne le chemin du snapshot créé, ou None si dry_run.
    """
    log.info("── ÉTAPE A : Snapshot du palace ──")
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = palace_path.parent / f"mempalace_drawers_backup_{ts}.tar.gz"

    if dry_run:
        log.info("[DRY-RUN] Snapshot simulé → %s (non créé)", snapshot_path)
        return None

    t0 = time.monotonic()
    try:
        with tarfile.open(snapshot_path, "w:gz") as tar:
            tar.add(palace_path, arcname=palace_path.name)
        elapsed = time.monotonic() - t0
        size_mb = snapshot_path.stat().st_size / (1024 ** 2)
        log.info(
            "Snapshot créé : %s (%.1f Mo, %.1fs)",
            snapshot_path, size_mb, elapsed,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Impossible de créer le snapshot : {exc}"
        ) from exc

    return snapshot_path
```

### `etape_b_inspection` (lignes 225-268) — **point de blocage**

```python
def etape_b_inspection(collection, from_model: str) -> tuple[int, int]:
    """
    Vérifie que la collection est dans l'état attendu avant migration.
    Retourne (count, dim_actuelle).
    """
    log.info("── ÉTAPE B : Inspection de la collection '%s' ──", COLLECTION_NAME)
    t0 = time.monotonic()

    count = collection.count()
    log.info("Nombre d'entrées : %d", count)

    if count == 0:
        log.info("Collection vide — rien à migrer. Sortie propre.")
        sys.exit(0)

    # Lire un vecteur exemple pour connaître la dimension actuelle.
    # NB : ChromaDB renvoie `embeddings` comme numpy.ndarray ; tester sa
    # truthiness directement (`not arr`) lève ValueError. On vérifie donc
    # explicitement présence et longueur.
    sample = collection.peek(limit=1)
    embeddings_sample = sample.get("embeddings")
    if embeddings_sample is None or len(embeddings_sample) == 0:
        raise RuntimeError(
            "Impossible de lire un embedding exemple depuis la collection. "
            "La collection est peut-être corrompue."
        )

    dim_actuelle = len(embeddings_sample[0])
    log.info("Dimension actuelle des vecteurs : %d", dim_actuelle)

    # Vérification de cohérence avec le modèle source déclaré
    dim_attendue_from = _expected_dim(from_model)
    if dim_actuelle != dim_attendue_from:
        raise ValueError(
            f"Incohérence de dimension ! Collection contient dim={dim_actuelle} "
            f"mais le modèle source '{from_model}' attend dim={dim_attendue_from}. "
            f"Vérifiez l'argument --from-model ou l'état de la collection."
        )

    log.info(
        "Inspection OK : %d entrées, dim=%d conforme à '%s' (%.2fs)",
        count, dim_actuelle, from_model, time.monotonic() - t0,
    )
    return count, dim_actuelle
```

### `etape_c_check_marker` (lignes 275-304)

```python
def etape_c_check_marker(palace_path: Path, to_model: str, dry_run: bool) -> None:
    """
    Vérifie si la migration vers to_model a déjà été effectuée.
    Lève SystemExit si le marker correspond au modèle cible.
    """
    log.info("── ÉTAPE C : Vérification idempotence (marker) ──")
    marker_path = palace_path / MARKER_FILENAME
    target_hash = _sha256(to_model)

    if marker_path.exists():
        existing_hash = marker_path.read_text(encoding="utf-8").strip()
        if existing_hash == target_hash:
            log.warning(
                "Migration déjà effectuée vers '%s' (hash SHA256 correspond : %s…).\n"
                "Relancer avec --force pour ignorer (non implémenté par sécurité).\n"
                "Abandon propre.",
                to_model, target_hash[:12],
            )
            sys.exit(0)
        else:
            log.info(
                "Marker présent mais hash différent (%s… → %s…) : "
                "migration vers un nouveau modèle, on continue.",
                existing_hash[:12], target_hash[:12],
            )
    else:
        log.info("Aucun marker trouvé — première migration.")

    if dry_run:
        log.info("[DRY-RUN] Marker non écrit (sera créé après étape g en mode normal).")
```

### `etape_c_write_marker` (lignes 307-333) — appelée à l'étape G

```python
def etape_c_write_marker(palace_path: Path, to_model: str, dry_run: bool) -> None:
    """Écrit les markers de fin de migration (appelé en fin d'étape g).

    Deux markers sont posés côte à côte à la racine du palace :

    * ``.embedder-migration-marker`` — hash SHA-256 du modèle cible, lu par
      :func:`etape_c_check_marker` pour l'idempotence ARIA (refus propre si
      la migration a déjà été faite).
    * ``.mempalace-embedder.json`` — marker side-channel introduit par le
      fork MemPalace (T-Mempalace-Patch). Idempotent : on ré-écrit
      à chaque migration réussie pour rester la source de vérité.
    """
    if dry_run:
        log.info("[DRY-RUN] Marker non écrit.")
        return
    marker_path = palace_path / MARKER_FILENAME
    marker_path.write_text(_sha256(to_model), encoding="utf-8")
    log.info("Marker écrit : %s", marker_path)

    mempalace_marker_path = palace_path / MEMPALACE_EMBEDDER_MARKER_FILENAME
    payload = {"model": to_model, "version": MEMPALACE_EMBEDDER_MARKER_VERSION}
    mempalace_marker_path.write_text(
        json.dumps(payload), encoding="utf-8"
    )
    log.info(
        "marker .mempalace-embedder.json écrit (model=%s)", to_model
    )
```

### `etape_d_reencoding` (lignes 340-428)

```python
def etape_d_reencoding(collection, to_model: str, dry_run: bool):
    """
    Charge le modèle cible et ré-encode tous les documents en batch.
    Retourne (ids, documents, metadatas, new_embeddings).
    """
    log.info("── ÉTAPE D : Re-encoding avec '%s' ──", to_model)

    # Import tardif : pas de dépendance à sentence_transformers si non installé
    try:
        from sentence_transformers import SentenceTransformer
        from tqdm import tqdm
    except ImportError as exc:
        raise ImportError(
            "Dépendances manquantes. Installez : "
            "pip install sentence-transformers tqdm"
        ) from exc

    # Chargement du modèle
    log.info("Chargement du modèle '%s'…", to_model)
    t_load = time.monotonic()
    model = SentenceTransformer(to_model)
    log.info("Modèle chargé en %.1fs.", time.monotonic() - t_load)

    # Lecture complète de la collection
    log.info("Lecture complète de la collection…")
    t_read = time.monotonic()
    total = collection.count()

    # ChromaDB peut limiter get() sans filtre — on pagine par sécurité
    all_ids: list[str] = []
    all_documents: list[str] = []
    all_metadatas: list[dict] = []
    offset = 0
    PAGE = 500  # taille de page pour la lecture

    while offset < total:
        page = collection.get(
            limit=PAGE,
            offset=offset,
            include=["documents", "metadatas"],
        )
        batch_ids = page.get("ids", [])
        if not batch_ids:
            break
        all_ids.extend(batch_ids)
        all_documents.extend(page.get("documents") or [""] * len(batch_ids))
        all_metadatas.extend(page.get("metadatas") or [{}] * len(batch_ids))
        offset += len(batch_ids)

    log.info(
        "%d entrées lues en %.1fs.", len(all_ids), time.monotonic() - t_read
    )

    if len(all_ids) != total:
        raise RuntimeError(
            f"Lecture incomplète : attendu {total} entrées, lu {len(all_ids)}."
        )

    if dry_run:
        log.info(
            "[DRY-RUN] Encodage simulé — %d documents, batch=%d.",
            len(all_documents), BATCH_SIZE,
        )
        # Retourne des embeddings factices pour permettre la validation à sec
        dim_cible = _expected_dim(to_model)
        dummy_embeddings = [[0.0] * dim_cible] * len(all_documents)
        return all_ids, all_documents, all_metadatas, dummy_embeddings

    # Encodage en batch avec barre de progression
    log.info("Encodage de %d documents (batch=%d)…", len(all_documents), BATCH_SIZE)
    t_enc = time.monotonic()
    new_embeddings_np = []

    batches = [
        all_documents[i:i + BATCH_SIZE]
        for i in range(0, len(all_documents), BATCH_SIZE)
    ]
    for batch in tqdm(batches, desc="Encodage", unit="batch"):
        vecs = model.encode(batch, show_progress_bar=False)
        new_embeddings_np.extend(vecs.tolist())

    elapsed_enc = time.monotonic() - t_enc
    phrases_per_sec = len(all_documents) / elapsed_enc if elapsed_enc > 0 else float("inf")
    log.info(
        "Encodage terminé : %d phrases en %.1fs → %.1f phrases/s",
        len(all_documents), elapsed_enc, phrases_per_sec,
    )

    return all_ids, all_documents, all_metadatas, new_embeddings_np
```

### `etape_e_rewrite_chroma` (lignes 435-501)

```python
def etape_e_rewrite_chroma(
    client,
    ids: list[str],
    embeddings: list,
    documents: list[str],
    metadatas: list[dict],
    dry_run: bool,
) -> None:
    """
    Supprime et recrée la collection avec les nouveaux embeddings.
    Approche défensive sur la signature de create_collection.
    """
    log.info("── ÉTAPE E : Réécriture ChromaDB ──")

    if dry_run:
        log.info(
            "[DRY-RUN] delete_collection('%s') simulé.", COLLECTION_NAME
        )
        log.info(
            "[DRY-RUN] create_collection('%s', hnsw:space=cosine) simulé.",
            COLLECTION_NAME,
        )
        log.info(
            "[DRY-RUN] collection.add(%d entrées en batches de %d) simulé.",
            len(ids), BATCH_SIZE,
        )
        return

    # Suppression
    log.info("Suppression de la collection '%s'…", COLLECTION_NAME)
    client.delete_collection(COLLECTION_NAME)
    log.info("Collection supprimée.")

    # Recréation — approche défensive sur le paramètre metadata
    log.info("Recréation de la collection '%s' (hnsw:space=cosine)…", COLLECTION_NAME)
    try:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Collection créée avec metadata hnsw:space=cosine.")
    except TypeError as exc:
        log.warning(
            "create_collection a rejeté le paramètre metadata (%s). "
            "Recréation sans metadata.", exc,
        )
        collection = client.create_collection(name=COLLECTION_NAME)
        log.info("Collection créée sans metadata (fallback).")

    # Insertion en batch
    total = len(ids)
    log.info("Insertion de %d entrées en batches de %d…", total, BATCH_SIZE)
    t0 = time.monotonic()

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    elapsed = time.monotonic() - t0
    log.info(
        "Insertion terminée : %d entrées en %.1fs.", total, elapsed
    )
```

### `etape_f_validation` (lignes 508-550)

```python
def etape_f_validation(client, count_avant: int, to_model: str) -> None:
    """Vérifie que la migration s'est déroulée correctement."""
    log.info("── ÉTAPE F : Validation post-migration ──")
    t0 = time.monotonic()

    collection = client.get_collection(COLLECTION_NAME)
    count_apres = collection.count()
    dim_attendue = _expected_dim(to_model)

    # Vérification du compte
    if count_apres != count_avant:
        raise RuntimeError(
            f"Validation ÉCHOUÉE : count avant={count_avant}, "
            f"count après={count_apres}. Données manquantes !"
        )
    log.info("✓ Count OK : %d entrées.", count_apres)

    # Vérification de la dimension via peek.
    # Cf. note dans etape_b_inspection : `embeddings` est un numpy.ndarray,
    # impossible de tester sa truthiness directement.
    sample = collection.peek(limit=1)
    embeddings_sample = sample.get("embeddings")
    if embeddings_sample is None or len(embeddings_sample) == 0:
        raise RuntimeError(
            "Validation ÉCHOUÉE : impossible de lire un embedding post-migration."
        )
    dim_actuelle = len(embeddings_sample[0])
    if dim_actuelle != dim_attendue:
        raise RuntimeError(
            f"Validation ÉCHOUÉE : dim post-migration={dim_actuelle}, "
            f"attendu={dim_attendue} pour '{to_model}'."
        )
    log.info("✓ Dimension OK : %d.", dim_actuelle)

    # Vérification du premier id préservé
    first_id = sample["ids"][0] if sample.get("ids") else "?"
    log.info(
        "✓ Peek OK : id=%s, len(embedding)=%d", first_id, dim_actuelle
    )

    log.info(
        "Validation réussie en %.2fs.", time.monotonic() - t0
    )
```

### `rollback_depuis_snapshot` (lignes 557-713)

```python
def rollback_depuis_snapshot(palace_path: Path, snapshot_path: Path | None) -> None:
    """
    Restaure le palace depuis le snapshot tar.gz en cas d'erreur entre e et f.

    Stratégie de swap via 2 rename séquentiels (PATCH C-ter) :
    ──────────────────────────────────────────────────────────
    Le tmpdir est créé sous palace_path.parent (même filesystem que le palace)
    via tempfile.mkdtemp(dir=palace_path.parent), pour garantir que les
    rename restent sur la même partition (sinon rename traverserait des
    filesystems et ne serait plus atomique).

    Le swap se fait en deux os.rename atomiques séquentiels :
        1. palace → palace.rollback-old   (atomique, libère le nom cible)
        2. extracted_palace → palace      (atomique, cible inexistante)
        3. rm -rf palace.rollback-old     (cleanup non critique)

    Motivation : os.replace (PATCH C-bis) échouait avec [Errno 39]
    ENOTEMPTY parce que rename(2) Linux refuse de remplacer un répertoire
    NON-VIDE. Avec deux rename, la cible de chaque rename est soit
    inexistante (étape 2) soit on libère le nom (étape 1).

    Sûreté en cas d'échec :
    - Si étape 1 échoue : palace original intact, snapshot préservé.
    - Si étape 2 échoue : on remet l'ancien palace en place via rename
      inverse (palace.rollback-old → palace). Le snapshot tar.gz reste
      disponible pour restauration manuelle.
    - Si étape 3 échoue : palace déjà restauré ; seul le cleanup du
      .rollback-old reste à faire à la main (logué en WARNING).

    Aucune fenêtre de perte de données : entre étapes 1 et 2, le palace
    reste accessible sous le nom .rollback-old.

    Le tmpdir est nettoyé dans un bloc finally, quelle que soit l'issue.
    """
    log.error("── ROLLBACK : Restauration du palace ──")

    if snapshot_path is None:
        log.error(
            "[ROLLBACK] Aucun snapshot disponible (--no-snapshot utilisé ou dry-run). "
            "Restauration manuelle requise depuis une sauvegarde externe."
        )
        return

    if not snapshot_path.exists():
        log.error(
            "[ROLLBACK] Snapshot introuvable : %s. "
            "Restauration manuelle requise.", snapshot_path,
        )
        return

    # Créer le tmpdir sous palace_path.parent — même partition que le palace cible
    tmpdir_path: Path | None = None
    try:
        tmpdir_str = tempfile.mkdtemp(
            prefix="aria_rollback_",
            dir=palace_path.parent,
        )
        tmpdir_path = Path(tmpdir_str)

        # Extraction dans le tmpdir
        log.info("[ROLLBACK] Extraction du snapshot dans %s…", tmpdir_path)
        with tarfile.open(snapshot_path, "r:gz") as tar:
            tar.extractall(path=tmpdir_path)

        # Vérifier que l'extraction a produit le répertoire palace attendu
        # avant de toucher à quoi que ce soit d'existant
        extracted_palace = tmpdir_path / palace_path.name
        if not extracted_palace.exists():
            raise FileNotFoundError(
                f"L'extraction n'a pas produit le répertoire attendu "
                f"'{palace_path.name}' sous {tmpdir_path}. "
                f"Le snapshot était peut-être archivé sous un nom différent."
            )

        # Swap via 2 os.rename séquentiels (cf. docstring pour la motivation).
        old_palace_path = palace_path.with_name(palace_path.name + ".rollback-old")

        # Si un précédent rollback a laissé un .rollback-old en place, le
        # nettoyer avant pour libérer le nom (sinon étape 1 va planter)
        if old_palace_path.exists():
            log.warning(
                "[ROLLBACK] %s existe déjà (rollback antérieur incomplet). "
                "Suppression avant le swap.",
                old_palace_path,
            )
            shutil.rmtree(old_palace_path)

        # Étape 1 : renommer l'ancien palace (atomique)
        if palace_path.exists():
            os.rename(str(palace_path), str(old_palace_path))
            log.info(
                "[ROLLBACK] Ancien palace mis de côté : %s",
                old_palace_path,
            )

        # Étape 2 : promouvoir le palace extrait au nom final (atomique)
        try:
            os.rename(str(extracted_palace), str(palace_path))
        except OSError as exc:
            # En cas d'échec ici, restaurer l'ancien palace si on l'a mis de côté
            log.critical(
                "[ROLLBACK] Promotion du palace extrait échouée : %s. "
                "Tentative de restauration de l'ancien palace.", exc,
            )
            if old_palace_path.exists():
                os.rename(str(old_palace_path), str(palace_path))
                log.info(
                    "[ROLLBACK] Ancien palace remis en place. "
                    "Le palace n'a PAS été restauré depuis le snapshot — "
                    "état post-étape-E préservé. Restauration manuelle "
                    "requise depuis : %s",
                    snapshot_path,
                )
            raise

        # Étape 3 : nettoyer l'ancien palace renommé
        if old_palace_path.exists():
            try:
                shutil.rmtree(old_palace_path)
                log.info(
                    "[ROLLBACK] Ancien palace nettoyé (%s).", old_palace_path,
                )
            except Exception as cleanup_exc:
                log.warning(
                    "[ROLLBACK] Cleanup de %s échoué : %s — "
                    "suppression manuelle : rm -rf %s",
                    old_palace_path, cleanup_exc, old_palace_path,
                )

        if not palace_path.exists():
            raise FileNotFoundError(
                f"Après le swap, '{palace_path}' est introuvable. "
                f"Anomalie système — vérifier {old_palace_path}."
            )

        log.info(
            "[ROLLBACK] Palace restauré depuis : %s", snapshot_path,
        )

    except Exception as exc:
        log.critical(
            "[ROLLBACK] ÉCHEC de la restauration : %s. "
            "Snapshot disponible à : %s — restauration manuelle requise.",
            exc, snapshot_path,
        )

    finally:
        # Nettoyage systématique du tmpdir, même en cas d'erreur
        if tmpdir_path is not None and tmpdir_path.exists():
            try:
                shutil.rmtree(tmpdir_path)
            except Exception as cleanup_exc:
                log.warning(
                    "[ROLLBACK] Nettoyage du tmpdir échoué : %s — "
                    "suppression manuelle : rm -rf %s",
                    cleanup_exc, tmpdir_path,
                )
```

### `main` — orchestration pertinente (lignes 762-880, extraits)

```python
def main() -> None:
    args = parse_args()

    palace_path = _resolve_palace(args.palace_path)
    from_model = args.from_model
    to_model = args.to_model
    dry_run = args.dry_run
    no_snapshot = args.no_snapshot

    # En-tête récapitulatif
    log.info("=" * 60)
    log.info("ARIA — migrate_embedder.py")
    log.info("  palace-path : %s", palace_path)
    log.info("  from-model  : %s (dim=%d)", from_model, _expected_dim(from_model))
    log.info("  to-model    : %s (dim=%d)", to_model, _expected_dim(to_model))
    log.info("  dry-run     : %s", dry_run)
    log.info("  no-snapshot : %s", no_snapshot)
    log.info("=" * 60)

    # Vérification d'existence du répertoire palace
    if not palace_path.exists():
        log.error("Le répertoire palace est introuvable : %s", palace_path)
        sys.exit(1)

    # Import ChromaDB (tardif pour donner un message d'erreur propre)
    try:
        import chromadb
    except ImportError as exc:
        raise ImportError(
            "chromadb n'est pas installé. Lancez : pip install chromadb"
        ) from exc

    # ── ÉTAPE C (pré) — Vérification idempotence ────────────────────────────
    etape_c_check_marker(palace_path, to_model, dry_run)

    # Ouverture du client ChromaDB
    log.info("Ouverture du client ChromaDB persistant : %s", palace_path)
    try:
        client = chromadb.PersistentClient(path=str(palace_path))
    except Exception as exc:
        raise RuntimeError(
            f"Impossible d'ouvrir le client ChromaDB : {exc}"
        ) from exc

    # Récupération de la collection source
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' introuvable dans '{palace_path}' : {exc}"
        ) from exc

    # ── ÉTAPE A — Snapshot ──────────────────────────────────────────────────
    snapshot_path: Path | None = None
    if no_snapshot:
        log.info("── ÉTAPE A : Snapshot ignoré (--no-snapshot) ──")
    else:
        snapshot_path = etape_a_snapshot(palace_path, dry_run)

    # ── ÉTAPE B — Inspection préalable ──────────────────────────────────────
    count_avant, _dim_actuelle = etape_b_inspection(collection, from_model)

    # ── ÉTAPE D — Re-encoding ────────────────────────────────────────────────
    ids, documents, metadatas, new_embeddings = etape_d_reencoding(
        collection, to_model, dry_run
    )

    # ── ÉTAPES E + F — Réécriture et validation (avec rollback si erreur) ───
    t_ef = time.monotonic()
    try:
        # ÉTAPE E — Réécriture ChromaDB
        etape_e_rewrite_chroma(
            client, ids, new_embeddings, documents, metadatas, dry_run
        )

        # ÉTAPE F — Validation post-migration
        if dry_run:
            log.info(
                "[DRY-RUN] Validation simulée — count=%d, dim=%d.",
                count_avant, _expected_dim(to_model),
            )
        else:
            etape_f_validation(client, count_avant, to_model)

    except Exception as exc:
        log.error("Exception entre étapes e/f : %s", exc)
        if not dry_run:
            log.error("[ROLLBACK] Tentative de restauration depuis snapshot…")
            rollback_depuis_snapshot(palace_path, snapshot_path)
        raise  # On re-raise pour que le code de sortie soit non-zéro

    log.info(
        "── ÉTAPES E+F terminées en %.1fs. ──", time.monotonic() - t_ef
    )

    # ── ÉTAPE G — Écriture du marker d'idempotence ──────────────────────────
    log.info("── ÉTAPE G : Écriture du marker d'idempotence ──")
    etape_c_write_marker(palace_path, to_model, dry_run)
```

---

## Section 3 — Cartographie SQLite-only de la collection

### 3.1 `count()`

**SQLite-only.** Confirmé par lecture de chromadb :

- `Collection.count()` → `_client._count(...)`
  (`venv/lib/python3.13/site-packages/chromadb/api/models/Collection.py:43-58`)
- `LocalAPI._count(...)` → `self.bindings.count(str(collection_id), tenant, database)`
  (`venv/lib/python3.13/site-packages/chromadb/api/rust.py:360-367`)

Le call retourne un `int` directement depuis le rust binding, sans
inclure d'embeddings. Empiriquement confirmé sur le palace pré-prod
quarantained : `count()` a retourné `710` à l'étape 3 du tour
T-Mempalace-Preprod malgré la quarantaine.

### 3.2 Dimension de la collection — **SQLite-only, sans peek nécessaire**

**Source de vérité** : table `collections` de `chroma.sqlite3`,
colonne `dimension`. Schéma lu sur le palace pré-prod :

```sql
CREATE TABLE IF NOT EXISTS "collections" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dimension INTEGER,
    database_id TEXT NOT NULL REFERENCES databases(id) ON DELETE CASCADE,
    config_json_str TEXT,
    schema_str TEXT,
    UNIQUE (name, database_id)
);
```

Valeur courante pour les deux collections de prod :

```
1e179386-e78e-49ed-b738-43b1e7f81165|mempalace_drawers|384
64d7d455-9793-4dd7-91fe-c983f2c4da93|mempalace_closets|384
```

**Donc la dim est lisible par une simple requête SQL** :

```sql
SELECT dimension FROM collections WHERE name = 'mempalace_drawers';
```

Aucune ouverture chromadb requise pour cette lecture — un
`sqlite3.connect(...)` direct suffit. C'est la voie la plus
robuste pour remplacer le `peek` de l'étape B.

### 3.3 Documents et métadonnées — SQLite-only via `get(..., include=["documents","metadatas"])`

L'appel `collection.get(limit=..., offset=..., include=["documents","metadatas"])`
chemine :

- `Collection.get(...)` → `_client._get(...)`
- `LocalAPI._get(...)` → `self.bindings.get(str(collection_id), ids, where, limit, offset, where_document, include, tenant, database)`
  (`venv/lib/python3.13/site-packages/chromadb/api/rust.py:386-430`)

Le paramètre `include` (sans `"embeddings"`) est passé tel quel
au rust binding. Le binding rust ne lit les vecteurs du segment
HNSW que si `"embeddings"` est demandé.

À comparer avec `peek(limit)` qui passe explicitement
`include=IncludeMetadataDocumentsEmbeddings = ["metadatas","documents","embeddings"]`
(`venv/lib/python3.13/site-packages/chromadb/api/rust.py:370-383` et
`venv/lib/python3.13/site-packages/chromadb/api/types.py:529-530`).

C'est exactement la différence qui explique pourquoi l'étape D
(get sans embeddings) passe sur palace quarantained alors que
l'étape B (peek) plante.

*Note de prudence empirique* : nous n'avons pas confirmé
*in vivo* que l'étape D passe sur palace quarantained — nous
sommes morts à l'étape B avant d'y arriver dans le tour
T-Mempalace-Preprod. La déduction repose sur la lecture du code
chromadb (include sans "embeddings" ne touche pas l'HNSW). À
valider empiriquement lors du fix.

### 3.4 Liste des IDs — SQLite-only

Les IDs sont stockés dans la table `embeddings` (colonne
`embedding_id`) :

```
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    segment_id TEXT NOT NULL,
    embedding_id TEXT NOT NULL,
    seq_id BLOB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (segment_id, embedding_id)
);
```

Donc une requête `SELECT embedding_id FROM embeddings WHERE
segment_id = ?` retourne tous les IDs sans toucher l'HNSW. Et le
`collection.get(...)` retourne déjà les IDs dans son champ `ids`
même quand `include=[]`. Pas de souci sur ce point.

### 3.5 Embeddings (vecteurs) eux-mêmes — **HNSW-required**

Les vecteurs ne sont PAS stockés dans la table SQLite
`embeddings` (qui ne contient que les pointeurs id/segment_id).
Ils résident dans le segment vecteur sur disque (`data_level0.bin`,
`link_lists.bin`, `header.bin`, `index_metadata.pickle` sous le
sous-répertoire `<segment_id>/`). Toute lecture de vecteur passe
par ce segment. C'est ce que `peek` demande et c'est ce qui fait
échec sur palace quarantained.

**Conséquence pour la migration** : le script n'a pas besoin de
lire les vecteurs source — il ne les utilise pas (il ré-encode
depuis les `documents`). Donc *aucune* lecture HNSW source n'est
fonctionnellement nécessaire à la migration.

---

## Section 4 — Impact d'un fix sur les étapes D, E, F

### Étape D — re-encoding

**Ne touche PAS l'HNSW source.** Confirmé :

- ligne 366 : `total = collection.count()` — SQLite-only.
- lignes 376-380 : `collection.get(limit=PAGE, offset=offset,
  include=["documents","metadatas"])` — pas de `"embeddings"`
  dans include, donc le rust binding ne lit pas le segment
  vecteur (cf. Section 3.3).
- ligne 418 : `model.encode(batch, show_progress_bar=False)` —
  appel sentence-transformers local, totalement hors chromadb.

Le re-encoding n'a besoin que des documents texte, qui sont
stockés en SQLite. Aucune dépendance sur l'index HNSW source.

### Étape E — réécriture

**Détruit puis recrée la collection** :

- ligne 465 : `client.delete_collection(COLLECTION_NAME)` — drop
  total. La collection et son segment HNSW (sain ou corrompu)
  sont effacés du catalog. Les fichiers du segment vivant sont
  également supprimés du disque.
- lignes 471-481 : `client.create_collection(name=COLLECTION_NAME,
  metadata={"hnsw:space": "cosine"})` — création d'une nouvelle
  collection vierge avec un nouveau `segment_id`.
- lignes 491-496 : `collection.add(...)` en batch — chromadb
  construit l'HNSW à mesure des insertions.

**Note sur les segments quarantained** : les répertoires
`<segment_id>.drift-...` et `<segment_id>.corrupt-...` créés par
le fork à l'ouverture ont été *renommés*, ils n'apparaissent plus
sous leur segment_id d'origine dans le catalog. `delete_collection`
ne les voit pas et ne les nettoie pas — ils survivent en tant que
fichiers orphelins sur disque. Pas un problème de correctness
(la nouvelle collection a un autre segment_id), juste un cleanup
manuel à prévoir post-migration. À noter pour le runbook ou le
post-mortem.

### Étape F — validation

**Sur la nouvelle collection** :

- ligne 513 : `client.get_collection(COLLECTION_NAME)` — handle
  sur la *nouvelle* collection créée à l'étape E.
- ligne 514 : `count_apres = collection.count()` — SQLite-only.
- ligne 528 : `sample = collection.peek(limit=1)` — peek sur la
  nouvelle collection, dont l'HNSW est vierge et sain par
  construction. Risque empirique très faible. Mais si on patche
  l'étape B pour s'affranchir de peek, autant remplacer aussi
  celui-ci par une lecture SQLite-only de `collections.dimension`
  (cohérence + un seul point d'inspection à maintenir).

### Synthèse étapes D/E/F après fix Étape B

Si on remplace le peek de l'étape B par une lecture
SQLite-only de la dim :

- D : déjà SQLite-only sur les lectures, fonctionne.
- E : intrinsèquement destructif/reconstructif, fonctionne sur
  un palace quarantained car le delete écrase tout.
- F : on peut soit garder le peek (sain sur la nouvelle
  collection), soit l'aligner sur la même méthode SQLite-only
  pour homogénéité.

Le fix Étape B est suffisant pour débloquer la migration sur
palace quarantained. Le fix Étape F est cosmétique mais
recommandé pour cohérence.

---

## Section 5 — Stratégies de fix possibles

### a) Remplacer `peek` par une lecture SQLite-only de la dim

**Avantage** : robuste par construction, indépendant de l'état
HNSW, source de vérité officielle chromadb (colonne `dimension`
de la table `collections`).
**Risque** : couplage au schéma SQLite chromadb (changement de
schéma à une version future = casse silencieuse).
**Coût** : ~10 lignes — ouvrir `chroma.sqlite3` en lecture,
exécuter `SELECT dimension FROM collections WHERE name = ?`,
parser. Tout en fail-safe (fallback sur les autres options en
cas de schéma inattendu).

### b) `try/except InternalError` autour de peek, fallback sur la dim attendue

**Avantage** : minimal en termes de diff, pas de couplage SQL.
**Risque** : on perd la vérification de cohérence dim observée
vs dim déclarée. Le check de l'étape B existe précisément pour
détecter le cas "l'utilisateur a passé `--from-model=MiniLM` mais
la collection contient déjà du mpnet" — on ne le détecterait plus.
**Coût** : ~5 lignes, mais c'est un fallback "aveugle" qui
désactive un garde-fou.

### c) Court-circuiter complètement l'étape B sur palaces présumés dégradés

Variantes envisageables :

- flag CLI `--skip-inspection` que l'opérateur active sciemment
  quand il sait que le palace est en drift.
- auto-detection sur présence de fichiers `.drift` / `.corrupt`
  sous palace_path (la signature laissée par le fork).

**Avantage** : pas de risque sur les palaces sains, opt-in
explicite, message clair côté log.
**Risque** : un opérateur qui oublie le flag se prendra le
même crash. L'auto-detection sur `.drift` est plus sûre mais
ajoute un coupling au comportement de quarantine du fork
(qui pourrait changer).
**Coût** : ~15 lignes (option CLI) + branche d'évitement de
peek.

### d) Combiner SQLite-only (a) ET try/except (b) en cascade

Lire la dim depuis SQLite en premier choix ; si la requête SQL
échoue (schéma inattendu, fichier manquant), tomber sur peek ;
si peek échoue, tomber sur `_expected_dim(from_model)` avec un
WARNING explicite.

**Avantage** : tolérance maximale, ne dégrade pas le check de
cohérence quand SQLite répond.
**Risque** : trois branches à maintenir, complexité de test.
**Coût** : ~25 lignes.

### e) Alternative côté lecture : utiliser `collection.get(limit=1, include=["embeddings"])` au lieu de `peek`

**Évaluation** : ne change rien au problème. `get` avec
`include=["embeddings"]` chemine vers la même
`bindings.get(..., include)` rust path que `peek`. Si le segment
HNSW est quarantained, ça échouera pareil.

→ **À écarter**, ne traite pas le bug.

### f) Pré-réparation du palace (avant migration) — hors-scope script

Outil tiers ou patch fork pour reconstruire l'HNSW depuis
SQLite avant de lancer la migration. Plus propre conceptuellement
mais hors-scope d'un fix de `migrate_embedder.py`. À envisager
côté fork MemPalace si on tombe sur ce drift en récurrence.

### Recommandation implicite (sans rédiger le fix)

L'option **(a)** ou **(d)** semblent dominer : elles préservent
la valeur du check de cohérence dim observée vs dim déclarée,
sont alignées sur la source de vérité chromadb (`collections.dimension`),
et débloquent la migration sur palace quarantained. **(b)** est
défendable si on accepte de perdre le check.

L'option **(c)** est légitime en plus de (a) ou (d), pas à la
place : un flag explicite est utile en debug même quand la voie
SQL marche.

Arbitrage Nico requis avant fix.

---

## Annexe — exécution chromadb des trois méthodes clés

Pour traçabilité, citations chromadb 1.x telles qu'installées
dans le venv ARIA (`venv/lib/python3.13/site-packages/chromadb/`) :

- **`Collection.count()`** — `api/models/Collection.py:43-58` →
  `_client._count(...)` → `api/rust.py:360-367` →
  `bindings.count(collection_id, tenant, database)`. Aucun
  paramètre include, aucune lecture de vecteur.

- **`Collection.peek(limit=10)`** — `api/models/Collection.py:174-190` →
  `_client._peek(...)` → `api/rust.py:370-383` → délègue à
  `_get(..., include=IncludeMetadataDocumentsEmbeddings)`.
  `IncludeMetadataDocumentsEmbeddings = ["metadatas","documents","embeddings"]`
  est défini en `api/types.py:530`.

- **`Collection.get(..., include=["documents","metadatas"])`** —
  `api/models/Collection.py:...` → `_client._get(...)` →
  `api/rust.py:386-430` → `bindings.get(collection_id, ids, where,
  limit, offset, where_document, include, tenant, database)`.
  Quand `"embeddings"` n'est pas dans `include`, le binding rust
  ne lit pas le segment vecteur.

C'est la différence d'`include` qui sépare un appel
HNSW-required d'un appel SQLite-only — pas la méthode elle-même.
