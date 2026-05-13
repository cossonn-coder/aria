# scripts/embedder_bench/inventory_vector_stores.py
#
# Inventaire exhaustif des collections vectorielles utilisées par ARIA.
# Lecture seule, ne modifie rien. Lance depuis la racine du projet :
#   ./venv/bin/python scripts/embedder_bench/inventory_vector_stores.py
#
# Sortie : tableau récap stdout + JSON dans /tmp/aria_vector_inventory.json
# (consommé par audit_embedder_inventory.md).
#
# Dépendances pip (déjà dans venv ARIA) :
#   chromadb, numpy

import json
import os
import sys
from collections import Counter
from pathlib import Path

import chromadb
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from config import config  # noqa: E402


def dir_size_bytes(path: Path) -> int:
    """Taille récursive d'un dossier (sans suivre les symlinks)."""
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def inspect_chroma_store(path: str, label: str) -> dict:
    """Inventaire d'un store ChromaDB persistant."""
    p = Path(path)
    out = {"label": label, "path": str(p), "exists": p.exists(), "collections": []}
    if not p.exists():
        return out

    out["disk_size"] = dir_size_bytes(p)
    out["disk_size_human"] = human_size(out["disk_size"])

    try:
        client = chromadb.PersistentClient(path=str(p))
    except Exception as e:
        out["error"] = f"PersistentClient failed: {e}"
        return out

    try:
        cols = client.list_collections()
    except Exception as e:
        out["error"] = f"list_collections failed: {e}"
        return out

    for col_meta in cols:
        try:
            col = client.get_collection(col_meta.name)
        except Exception as e:
            out["collections"].append({"name": col_meta.name, "error": str(e)})
            continue

        total = col.count()
        col_info = {"name": col_meta.name, "count": total}

        # Échantillon pour dimension + distribution wings
        if total > 0:
            try:
                sample = col.get(limit=1, include=["embeddings", "metadatas"])
                embs = sample.get("embeddings")
                if embs is not None and len(embs) > 0:
                    vec = np.asarray(embs[0])
                    col_info["dim"] = int(vec.shape[0])
                else:
                    col_info["dim"] = None
                metas = sample.get("metadatas") or []
                if metas:
                    col_info["sample_meta_keys"] = sorted(metas[0].keys()) if metas[0] else []
            except Exception as e:
                col_info["dim_error"] = str(e)

            # Distribution par wing/type (toute la collection)
            try:
                full = col.get(include=["metadatas"])
                wings = Counter()
                types = Counter()
                rooms_per_wing = {}
                for m in full.get("metadatas") or []:
                    if not m:
                        wings["<no_wing>"] += 1
                        continue
                    w = m.get("wing", "<no_wing>")
                    t = m.get("type", "<no_type>")
                    r = m.get("room", "<no_room>")
                    wings[w] += 1
                    types[t] += 1
                    rooms_per_wing.setdefault(w, Counter())[r] += 1
                col_info["by_wing"] = dict(wings)
                col_info["by_type"] = dict(types)
                col_info["rooms_per_wing"] = {
                    w: dict(rc.most_common(5)) for w, rc in rooms_per_wing.items()
                }
            except Exception as e:
                col_info["meta_distribution_error"] = str(e)

        out["collections"].append(col_info)

    return out


def inspect_intents_json(path: str) -> dict:
    """Inventaire du fichier intents.json (pas un store vectoriel — embeddings reconstruits au boot)."""
    p = Path(path)
    out = {"path": str(p), "exists": p.exists()}
    if not p.exists():
        return out

    out["disk_size"] = p.stat().st_size
    out["disk_size_human"] = human_size(out["disk_size"])

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        out["error"] = f"parse failed: {e}"
        return out

    if isinstance(data, dict) and "intents" in data:
        intents = data["intents"]
    elif isinstance(data, list):
        intents = data
    elif isinstance(data, dict):
        # Schéma {intent_id: {...}} (production ARIA)
        intents = [v for v in data.values() if isinstance(v, dict)]
    else:
        intents = []
        out["unknown_schema"] = type(data).__name__

    out["count_total"] = len(intents)
    statuses = Counter(i.get("status", "<no_status>") for i in intents if isinstance(i, dict))
    out["by_status"] = dict(statuses)
    out["names_sample"] = [i.get("name") for i in intents[:10] if isinstance(i, dict)]
    has_persisted_embedding = any(
        isinstance(i, dict) and ("embedding" in i or "vector" in i) for i in intents
    )
    out["has_persisted_embedding"] = has_persisted_embedding

    return out


def main() -> dict:
    report = {
        "embedding_model": config.EMBEDDING_MODEL,
        "stores": [],
    }

    # MemPalace (mempalace_path) — seul store vectoriel actif depuis
    # le décommissionnement de chroma_db/ legacy (T-Embedder2 Tâche B).
    report["stores"].append(inspect_chroma_store(config.mempalace_path, "mempalace_palace"))

    # intents.json — pas un store vectoriel, embeddings reconstruits au boot.
    intents_path = os.path.expanduser("~/.aria/intents.json")
    report["intents_json"] = inspect_intents_json(intents_path)

    out_path = Path("/tmp/aria_vector_inventory.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    # ── Affichage stdout ──────────────────────────────────────────────
    print(f"\n=== ARIA — Inventaire vectoriel ===")
    print(f"EMBEDDING_MODEL : {report['embedding_model']}")
    print()
    for store in report["stores"]:
        print(f"── Store : {store['label']} ({store['path']})")
        if not store.get("exists"):
            print("   absent.")
            continue
        if "error" in store:
            print(f"   erreur : {store['error']}")
            continue
        print(f"   disk : {store['disk_size_human']}")
        for col in store.get("collections", []):
            if "error" in col:
                print(f"   - {col['name']}: erreur {col['error']}")
                continue
            dim = col.get("dim", "?")
            print(f"   - {col['name']}: count={col['count']} dim={dim}")
            if "by_wing" in col:
                print(f"     by_wing  : {col['by_wing']}")
            if "by_type" in col:
                print(f"     by_type  : {col['by_type']}")
        print()

    ij = report["intents_json"]
    print(f"── intents.json : {ij['path']}")
    if ij.get("exists"):
        print(f"   count={ij.get('count_total')} statuses={ij.get('by_status')} "
              f"persisted_embedding={ij.get('has_persisted_embedding')}")
        print(f"   sample_names={ij.get('names_sample')}")
    else:
        print("   absent.")

    print(f"\nReport JSON : {out_path}")
    return report


if __name__ == "__main__":
    main()
