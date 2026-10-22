#!/usr/bin/env python3
# scripts/mempalace_sync_threshold.py
#
# Script ponctuel (sprint 30, dette #105) : met fin à la quarantaine HNSW
# (`.drift-*`) qui frappe `mempalace_drawers` à chaque démarrage d'ARIA.
#
# Cause : mempalace crée la collection avec `sync_threshold = 50000`. Le palace
# n'ayant que quelques centaines d'entrées, l'index HNSW n'est jamais persisté
# (`index_metadata.pickle` absent) et mempalace le prend pour un segment corrompu.
# Correctif : baisser le seuil à 100 via `collection.modify(configuration=…)`,
# puis faire ouvrir la collection par un NOUVEAU process (avec une requête) pour
# que chromadb rejoue le journal et écrive le pickle.
#
# Accès chromadb direct assumé : c'est une opération de configuration, pas une
# écriture de drawers (la règle 1 / memory/writer.py vise les données).
#
# Usage :
#   ./venv/bin/python scripts/mempalace_sync_threshold.py           # palace prod (service arrêté)
#   ./venv/bin/python scripts/mempalace_sync_threshold.py <chemin>  # autre palace (tests)
#
# Idempotent : relancé, il réapplique le même seuil et ne trouve plus de `.drift-*`.

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from mempalace.backends.chroma import _vector_segment_id

from config import config
from logger import configure_root, get_logger

log = get_logger("aria.mempalace_sync_threshold")

COLLECTION_NAME = "mempalace_drawers"
HNSW_THRESHOLD = 100

# Code exécuté dans un process neuf : ouvre la collection et fait une requête
# (avec un embedding déjà stocké, pour ne pas charger de modèle). C'est cette
# ouverture qui rejoue le journal et persiste l'index au nouveau seuil.
_REOPEN_CODE = """
import sys, chromadb
col = chromadb.PersistentClient(path=sys.argv[1]).get_collection(sys.argv[2])
emb = col.get(limit=1, include=["embeddings"])["embeddings"]
col.query(query_embeddings=[list(emb[0])], n_results=1)
"""


def main(argv: list[str]) -> int:
    configure_root()

    if argv:
        palace = Path(argv[0])
    else:
        palace = Path(config.mempalace_path)
        # Le service tient le palace ouvert : modifier sous ses pieds est exclu.
        if subprocess.run(["systemctl", "is-active", "--quiet", "aria.service"]).returncode == 0:
            log.error("aria.service est actif : l'arrêter d'abord (sudo systemctl stop aria.service).")
            return 1

    log.info("Palace : %s", palace)

    # 1. Sauvegarde de la base sqlite (source de vérité) avant toute modification.
    db = palace / "chroma.sqlite3"
    backup = palace / f"chroma.sqlite3.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(db, backup)
    log.info("Sauvegarde : %s", backup)

    # 2. Baisse du seuil de persistance HNSW.
    col = chromadb.PersistentClient(path=str(palace)).get_collection(COLLECTION_NAME)
    col.modify(configuration={"hnsw": {"sync_threshold": HNSW_THRESHOLD, "batch_size": HNSW_THRESHOLD}})
    log.info("Seuil HNSW de %s passé à %d (%d entrées).", COLLECTION_NAME, HNSW_THRESHOLD, col.count())

    # 3. Ouverture par un nouveau process, puis contrôle du pickle.
    subprocess.run([sys.executable, "-c", _REOPEN_CODE, str(palace), COLLECTION_NAME], check=True)
    pickle = palace / _vector_segment_id(str(palace), COLLECTION_NAME) / "index_metadata.pickle"
    if not pickle.is_file():
        log.error("Index HNSW non persisté (%s absent) : .drift-* conservés.", pickle)
        return 1
    log.info("Index HNSW persisté : %s", pickle)

    # 4. Ménage des segments mis en quarantaine par les démarrages précédents.
    drifts = sorted(p for p in palace.glob("*.drift-*") if p.is_dir())
    for d in drifts:
        shutil.rmtree(d)
    log.info("%d dossier(s) .drift-* supprimé(s).", len(drifts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
