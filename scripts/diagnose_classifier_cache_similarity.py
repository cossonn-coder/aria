#!/usr/bin/env python3
"""
Étape 2 — Prouve le mismatch embedder entre écriture et lecture du cache classifier.

Pour chaque document du wing aria_classifier :
  - Affiche le texte stocké (JSON)
  - Extrait le message brut du JSON
  - Recherche avec (A) le JSON exact, (B) le message brut
  - Compare les similarités pour montrer le mismatch

Usage : python scripts/diagnose_classifier_cache_similarity.py
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.mempalace_store import search

WING = "aria_classifier"
N_DOCS = 10  # nombre de documents à tester

def run():
    # Récupère tous les docs de aria_classifier via une requête large
    # On utilise une requête neutre pour lister les candidats
    result = search(query="message", wing=WING, n=200)
    docs = result.get("results", [])

    if not docs:
        print(f"[WARN] Aucun document dans wing={WING}. Cache vide.")
        return

    print(f"Documents trouvés : {len(docs)} (affichage des {min(N_DOCS, len(docs))} premiers)\n")
    print(f"{'─'*70}")

    tested = 0
    for hit in docs[:N_DOCS]:
        stored_text = hit.get("text", "")
        doc_id      = hit.get("id", "?")

        # Tente de parser le JSON pour extraire le message brut
        try:
            parsed      = json.loads(stored_text)
            message_raw = parsed.get("message", "")
            operation   = parsed.get("operation", "?")
        except (json.JSONDecodeError, TypeError):
            print(f"[SKIP] doc_id={doc_id} — texte non JSON : {stored_text[:60]!r}")
            continue

        print(f"doc_id    : {doc_id[:40]}...")
        print(f"operation : {operation}")
        print(f"message   : {message_raw[:70]!r}")

        # (A) Recherche avec le JSON complet (= ce qui a été embedé)
        r_json = search(query=stored_text, wing=WING, n=1)
        hits_json = r_json.get("results", [])
        sim_json  = hits_json[0].get("similarity", "N/A") if hits_json else "N/A"
        dist_json = hits_json[0].get("distance",   "N/A") if hits_json else "N/A"
        match_json = (hits_json[0].get("id") == doc_id) if hits_json else False

        # (B) Recherche avec le message brut (= ce que _search_cache fait)
        r_raw = search(query=message_raw, wing=WING, n=1) if message_raw else {"results": []}
        hits_raw = r_raw.get("results", [])
        sim_raw  = hits_raw[0].get("similarity", "N/A") if hits_raw else "N/A"
        dist_raw = hits_raw[0].get("distance",   "N/A") if hits_raw else "N/A"
        match_raw = (hits_raw[0].get("id") == doc_id) if hits_raw else False

        print(f"  (A) query=JSON complet  → sim={sim_json!s:>8}  dist={dist_json!s:>8}  same_doc={match_json}")
        print(f"  (B) query=message brut  → sim={sim_raw!s:>8}  dist={dist_raw!s:>8}  same_doc={match_raw}")
        print(f"{'─'*70}")
        tested += 1

    print(f"\nConclusion : {tested} documents testés.")
    print("Si (A) sim~1.0 et (B) sim<<0.9 → mismatch JSON-vs-message confirmé.")
    print("Si (A) et (B) sim~1.0 → mismatch absent, problème ailleurs.")

if __name__ == "__main__":
    run()
