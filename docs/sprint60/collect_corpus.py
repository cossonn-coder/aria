"""
Collecte des photos du corpus du sprint 60 (lecture seule du palace).

Nico envoie chaque photo sur Telegram avec la légende « corpus <nom> »
(ex. « corpus p1 face jour »). L'épisodique garde « description | légende »
et le chemin du fichier : on copie chaque photo dans docs/sprint60/corpus/<nom>.jpg.
Usage : venv/bin/python docs/sprint60/collect_corpus.py
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import config  # noqa: E402
from memory.mempalace_store import get_collection  # noqa: E402

_CAPTION_RE = re.compile(r"\|\s*corpus\s+(.+?)\s*$", re.IGNORECASE)

out_dir = ROOT / "docs" / "sprint60" / "corpus"
out_dir.mkdir(exist_ok=True)
col = get_collection(config.mempalace_path)
res = col.get(where={"type": "image_input"}, include=["documents", "metadatas"])
for doc, meta in zip(res["documents"], res["metadatas"]):
    m = _CAPTION_RE.search(doc or "")
    if not m:
        continue
    name = re.sub(r"\W+", "_", m.group(1).lower()).strip("_")
    dest = out_dir / f"{name}.jpg"
    shutil.copyfile(meta["path"], dest)
    print(f"{name:30s} ← {Path(meta['path']).name}  ({meta['timestamp'][:16]})")
