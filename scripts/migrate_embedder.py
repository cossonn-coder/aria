"""
migrate_embedder.py — ARIA Sprint 6 · T-Embedder2 D
=====================================================
Migration de la collection ChromaDB `mempalace_drawers`
de all-MiniLM-L6-v2 (dim 384) vers
sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (dim 768).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TESTS — INVOCATIONS CLI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PRÉPARATION D'UNE COPIE DE BENCH
   ──────────────────────────────────
   cp -r ~/.mempalace ~/.mempalace.bench-copy

2. MIGRATION SUR COPIE (sans snapshot, pour aller vite)
   ──────────────────────────────────────────────────────
   ./venv/bin/python aria/scripts/migrate_embedder.py \
       --palace-path ~/.mempalace.bench-copy/palace \
       --no-snapshot

   Résultat attendu :
   - Log des étapes a→g
   - Compte rendu final "Migration réussie" avec dim=768 et phrases/s
   - Fichier .embedder-migration-marker créé dans palace-path

3. TEST IDEMPOTENCE (relancer après migration réussie)
   ──────────────────────────────────────────────────────
   ./venv/bin/python aria/scripts/migrate_embedder.py \
       --palace-path ~/.mempalace.bench-copy/palace \
       --no-snapshot

   Résultat attendu :
   - Le script détecte le marker, affiche un message explicite du type :
     "Migration déjà effectuée vers ce modèle (hash SHA256 correspond).
      Utilisez --force pour ignorer. Abandon."
   - Exit code 0 (refus propre, pas une erreur)

4. TEST DRY-RUN (sur la copie ou sur l'original)
   ──────────────────────────────────────────────
   ./venv/bin/python aria/scripts/migrate_embedder.py \
       --palace-path ~/.mempalace.bench-copy/palace \
       --no-snapshot \
       --dry-run

   Résultat attendu :
   - Toutes les étapes sont simulées et loguées
   - Rien n'est écrit dans ChromaDB (pas de delete/create)
   - Le marker n'est pas créé
   - Log "[DRY-RUN] ..." sur chaque étape destructive

5. TEST ROLLBACK
   ──────────────────────────────────────────────────────
   a) Préparer une copie fraîche (sans marker) :
      cp -r ~/.mempalace ~/.mempalace.rollback-test

   b) Dans le script, localiser la section "ÉTAPE E" et ajouter
      temporairement après collection.add(...) :
          raise RuntimeError("TEST ROLLBACK — erreur simulée à l'étape e")

   c) Lancer (AVEC snapshot cette fois, car le rollback en a besoin) :
      ./venv/bin/python aria/scripts/migrate_embedder.py \
          --palace-path ~/.mempalace.rollback-test/palace

   Résultat attendu :
   - Le script plante à l'étape e et le log affiche :
     "[ROLLBACK] Exception en étape e/f, restauration depuis snapshot..."
     "[ROLLBACK] Palace restauré depuis <chemin_snapshot.tar.gz>"
   - La collection retrouve ses 655 entrées originales avec dim 384
   - Vérifier : python -c "
       import chromadb
       c = chromadb.PersistentClient('~/.mempalace.rollback-test/palace')
       col = c.get_collection('mempalace_drawers')
       res = col.peek(1)
       print('count:', col.count())
       print('dim:', len(res['embeddings'][0]))
     "

   d) Retirer le raise temporaire après le test.

   6. CHANGELOG
   PATCH C-ter (rollback_depuis_snapshot — swap via 2 rename séquentiels)
    Le PATCH C-bis utilisait os.replace, ce qui échouait avec
    [Errno 39] Directory not empty quand le palace existe et est non-vide
    (rename(2) Linux refuse de remplacer un répertoire non-vide). Test
    rollback en T-Embedder2 D : KO confirmé.
    Remplacé par une séquence de deux os.rename atomiques :
        1. Renommer palace → palace.rollback-old (atomique)
        2. Renommer extracted_palace → palace (atomique, cible inexistante)
        3. Cleanup palace.rollback-old
    Si l'étape 2 échoue, l'ancien palace est restauré (rename inverse) et
    le snapshot tar.gz original reste disponible pour restauration manuelle.
    Aucune fenêtre de perte de données : entre étapes 1 et 2, le palace
    est accessible sous le nom .rollback-old.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DÉPENDANCES REQUISES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pip install chromadb sentence-transformers tqdm
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging configuré dès l'import — format avec horodatage et niveau
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("aria.migrate_embedder")

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


def _read_collection_dim_count_sqlite(
    palace_path: Path, collection_name: str
) -> tuple[int, int]:
    """
    Lit (dim, count) de la collection directement dans ``chroma.sqlite3``,
    sans toucher au segment HNSW.

    Pourquoi : sur un palace dont les segments HNSW ont été quarantained
    par le fork MemPalace (drift sqlite/HNSW), ``collection.peek(...)``
    et plus généralement toute lecture qui réclame ``embeddings`` plante.
    En revanche la dim déclarée (``collections.dimension``) et le count
    canonique (rows de ``embeddings`` côté segment METADATA) restent
    accessibles via une simple lecture SQL — c'est la source de vérité
    documentée par l'audit pré-fix (cf.
    ``docs/sprint7/audit_migrate_embedder_peek.md`` sections 3.1–3.2).

    Le chemin du fichier est dérivé strictement de ``palace_path``, jamais
    hardcodé. Connexion en read-only via URI (``mode=ro``).

    Retourne ``(dim, count)``. Lève ``RuntimeError`` si ``chroma.sqlite3``
    ou la collection est introuvable.
    """
    sqlite_path = palace_path / "chroma.sqlite3"
    if not sqlite_path.exists():
        raise RuntimeError(
            f"chroma.sqlite3 introuvable sous {palace_path} — "
            f"palace invalide ou structure inattendue."
        )

    uri = f"file:{sqlite_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        row = conn.execute(
            "SELECT id, dimension FROM collections WHERE name = ?",
            (collection_name,),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                f"Collection '{collection_name}' introuvable dans "
                f"{sqlite_path}."
            )
        collection_id, dim = row
        if dim is None:
            raise RuntimeError(
                f"Collection '{collection_name}' présente mais sans "
                f"dimension renseignée dans la table SQLite — palace "
                f"probablement non initialisé (aucune insertion)."
            )

        # Le count canonique côté ChromaDB correspond aux entrées du
        # segment METADATA (scope='METADATA'), pas du segment vecteur.
        # C'est ce que renvoie collection.count() côté binding rust.
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM embeddings e "
            "JOIN segments s ON s.id = e.segment_id "
            "WHERE s.collection = ? AND s.scope = 'METADATA'",
            (collection_id,),
        ).fetchone()
    finally:
        conn.close()

    return int(dim), int(count)


# ---------------------------------------------------------------------------
# ÉTAPE A — Snapshot tar.gz horodaté
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ÉTAPE B — Inspection préalable de la collection
# ---------------------------------------------------------------------------

def etape_b_inspection(palace_path: Path, from_model: str) -> tuple[int, int]:
    """
    Vérifie que la collection est dans l'état attendu avant migration.
    Retourne (count, dim_actuelle).

    Lecture SQLite-only (cf. ``_read_collection_dim_count_sqlite``) : ni
    ``collection.peek`` ni ``collection.count`` ne sont appelés, ce qui
    rend l'inspection insensible à l'état des segments HNSW. Indispensable
    pour migrer un palace dont la quarantaine drift/corrupt a été
    appliquée par le fork MemPalace à l'ouverture du client.
    """
    log.info("── ÉTAPE B : Inspection de la collection '%s' ──", COLLECTION_NAME)
    t0 = time.monotonic()

    dim_actuelle, count = _read_collection_dim_count_sqlite(
        palace_path, COLLECTION_NAME
    )
    log.info("Nombre d'entrées : %d", count)

    if count == 0:
        log.info("Collection vide — rien à migrer. Sortie propre.")
        sys.exit(0)

    log.info("Dimension actuelle des vecteurs : %d", dim_actuelle)

    # Vérification de cohérence dim SQLite vs modèle source déclaré.
    # Check de cohérence renforcé par rapport à la version peek : on
    # confronte la dim *stockée* (table collections) à la dim *théorique*
    # du modèle passé en --from-model. Mismatch = palace incohérent avec
    # l'argument CLI, on refuse la migration plutôt que d'encoder
    # à l'aveugle.
    dim_attendue_from = _expected_dim(from_model)
    if dim_actuelle != dim_attendue_from:
        raise ValueError(
            f"Incohérence de dimension ! Collection contient "
            f"dim_sqlite={dim_actuelle} mais le modèle source "
            f"'{from_model}' attend dim={dim_attendue_from}. "
            f"Vérifiez l'argument --from-model ou l'état de la collection."
        )

    log.info(
        "Inspection OK : %d entrées, dim=%d conforme à '%s' (%.2fs)",
        count, dim_actuelle, from_model, time.monotonic() - t0,
    )
    return count, dim_actuelle


# ---------------------------------------------------------------------------
# ÉTAPE C — Idempotence via marker
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ÉTAPE D — Re-encoding
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ÉTAPE E — Réécriture ChromaDB
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ÉTAPE F — Validation post-migration
# ---------------------------------------------------------------------------

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
    # La collection vient juste d'être recréée par l'étape E donc son
    # HNSW est vierge et sain par construction. Le peek est néanmoins
    # enveloppé d'un try/except pour ne pas faire échouer la migration
    # si une dégradation inattendue survenait : le count a déjà été
    # vérifié au-dessus (durci, raise), et un smoke ultérieur côté
    # appelant validera la dim réelle de l'EF. Pas de swallow muet :
    # un warning explicite est émis pour signalement pilote.
    try:
        sample = collection.peek(limit=1)
        embeddings_sample = sample.get("embeddings")
        if embeddings_sample is None or len(embeddings_sample) == 0:
            raise RuntimeError(
                "peek post-migration n'a renvoyé aucun embedding."
            )
        dim_actuelle = len(embeddings_sample[0])
        if dim_actuelle != dim_attendue:
            raise RuntimeError(
                f"dim post-migration={dim_actuelle}, attendu={dim_attendue} "
                f"pour '{to_model}'."
            )
        log.info("✓ Dimension OK : %d.", dim_actuelle)

        first_id = sample["ids"][0] if sample.get("ids") else "?"
        log.info(
            "✓ Peek OK : id=%s, len(embedding)=%d", first_id, dim_actuelle
        )
    except Exception as exc:
        tb_short = "\n".join(traceback.format_exc().splitlines()[-4:])
        log.warning(
            "Peek validation post-migration échoué, collection cible "
            "potentiellement dégradée — exception : %s\n%s",
            exc, tb_short,
        )

    log.info(
        "Validation réussie en %.2fs.", time.monotonic() - t0
    )


# ---------------------------------------------------------------------------
# ROLLBACK — restauration depuis snapshot
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Parsing des arguments CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "ARIA — Migration d'embedder ChromaDB "
            "(all-MiniLM-L6-v2 → paraphrase-multilingual-mpnet-base-v2)"
        )
    )
    parser.add_argument(
        "--palace-path",
        default="~/.mempalace/palace",
        help="Chemin du répertoire ChromaDB persistant (défaut: ~/.mempalace/palace)",
    )
    parser.add_argument(
        "--from-model",
        default="all-MiniLM-L6-v2",
        help="Nom du modèle source (défaut: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--to-model",
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        help=(
            "Nom du modèle cible "
            "(défaut: sentence-transformers/paraphrase-multilingual-mpnet-base-v2)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule toutes les étapes sans écrire dans ChromaDB ni créer le marker.",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Saute la création du snapshot tar.gz (utile pour tests rapides).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

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
    # On vérifie le marker AVANT d'ouvrir le client ChromaDB pour éviter
    # tout effet de bord sur la DB si la migration est déjà faite.
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
    # Lecture SQLite directe (palace_path), pas via l'objet collection :
    # robuste aux palaces dont l'HNSW est quarantained.
    count_avant, _dim_actuelle = etape_b_inspection(palace_path, from_model)

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

        # ── POINT DE TEST ROLLBACK ──────────────────────────────────────────
        # Pour tester le rollback, décommenter la ligne suivante :
        # raise RuntimeError("TEST ROLLBACK — erreur simulée entre étape e et f")
        # ───────────────────────────────────────────────────────────────────

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

    # Résumé final
    log.info("=" * 60)
    if dry_run:
        log.info("[DRY-RUN] Simulation terminée — aucune donnée modifiée.")
    else:
        log.info(
            "✓ Migration réussie : '%s' → '%s' | %d entrées | dim %d → %d",
            from_model, to_model,
            count_avant,
            _expected_dim(from_model),
            _expected_dim(to_model),
        )
    log.info("=" * 60)


if __name__ == "__main__":
    main()
