# tests/test_mempalace_sync_threshold.py
#
# Sprint 30 tronçon 02 (#105) : le script baisse le seuil HNSW, fait persister
# l'index (pickle) et supprime les .drift-*, sur un palace temporaire.

import chromadb
from mempalace.backends.chroma import _vector_segment_id
from mempalace.palace import get_collection

from scripts.mempalace_sync_threshold import COLLECTION_NAME, main


def test_seuil_baisse_pickle_ecrit_drift_supprime(tmp_path):
    palace = str(tmp_path)
    # Collection créée par mempalace (seuil 50000), 150 entrées : au-delà du
    # nouveau seuil 100, pour que la réouverture persiste l'index.
    col = get_collection(palace, collection_name=COLLECTION_NAME)
    n = 150
    col.add(
        ids=[f"id{i}" for i in range(n)],
        documents=[f"doc {i}" for i in range(n)],
        embeddings=[[float(i), 1.0, 0.5] for i in range(n)],
    )
    drift = tmp_path / "0000-fake.drift-x"
    drift.mkdir()

    assert main([palace]) == 0

    conf = chromadb.PersistentClient(path=palace).get_collection(COLLECTION_NAME).configuration_json
    assert conf["hnsw"]["sync_threshold"] == 100
    seg = _vector_segment_id(palace, COLLECTION_NAME)
    assert (tmp_path / seg / "index_metadata.pickle").is_file()
    assert not drift.exists()
    assert list(tmp_path.glob("chroma.sqlite3.bak-*"))
