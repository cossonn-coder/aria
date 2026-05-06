#!/usr/bin/env python3
"""
Étape 1 — Inspecte la configuration ChromaDB (métrique, embedding function).
Usage : python scripts/diagnose_chroma_metric.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from config import config

client = chromadb.PersistentClient(path=config.mempalace_path)

for col_name in ["mempalace_drawers", "mempalace_closets"]:
    try:
        col = client.get_collection(col_name)
    except Exception as e:
        print(f"[{col_name}] introuvable : {e}")
        continue

    print(f"\n{'='*55}")
    print(f"Collection     : {col.name}")
    print(f"Metadata       : {col.metadata}")

    ef = getattr(col, "_embedding_function", None)
    if ef is not None:
        print(f"EF type        : {type(ef).__name__}")
        name_fn = getattr(ef, "name", None)
        if callable(name_fn):
            print(f"EF name()      : {name_fn()}")
        elif name_fn is not None:
            print(f"EF name        : {name_fn}")
    else:
        print("EF             : non exposée via _embedding_function")

    # Compte les entrées par wing pour référence
    try:
        result = col.get(include=["metadatas"], limit=5000)
        from collections import Counter
        wings = Counter(
            (m.get("wing", "<none>") if m else "<none>")
            for m in result["metadatas"]
        )
        print(f"Wings          : {dict(wings)}")
    except Exception as e:
        print(f"Comptage wings : {e}")
