# tests/test_storage_isolation.py
#
# Non-régression sprint 17 tronçon 01 : un AriaKernel construit en test
# écrit dans tmp_path (fixture autouse `isolate_storage`), jamais dans le
# palace ni dans intents.json de prod.

import intent.intent_store as intent_store
from config import config
from core.kernel import AriaKernel
from tests.cognition.test_cognitive_scenarios import run


def test_kernel_writes_under_tmp_path(tmp_path):
    k = AriaKernel()
    run(k, "je veux construire une maison")

    assert config.mempalace_path.startswith(str(tmp_path))
    assert str(intent_store.STORE_PATH).startswith(str(tmp_path))
    # Le palace temporaire a bien reçu l'écriture épisodique
    assert (tmp_path / "palace" / "chroma.sqlite3").exists()
