# scripts/embedder_bench/benchmark_quality.py
#
# Benchmark qualité multilingue — 6 modèles × 5 cas terrain bug #18.
# Lecture seule de ~/.aria/intents.json. N'écrit rien dans la mémoire.
#
# Usage :
#   ./venv/bin/python scripts/embedder_bench/benchmark_quality.py
#
# Sortie :
#   - /tmp/aria_bench_quality.json  : résultats bruts (consommé par
#     audit_embedder_benchmark.md)
#   - stdout : tableau récap (Recall@1, Recall@3, Gap moyen, Spread)
#
# Cas terrain : audit_intent_matching.md §7. Oracles validés présents
# dans intents.json (cf. audit_embedder_inventory.md §2.5).
#
# Dépendances pip : sentence-transformers, transformers, torch, numpy,
#                   optimum, onnxruntime.

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import (  # noqa: E402
    REGISTRY,
    UnifiedEncoder,
    cosine_matrix,
    rank_of,
    topk,
)


F1_THRESHOLD = 0.45  # Seuil ATTACH actuel en prod (audit sprint 5 §6)
SPLIT_LOWER_BOUND = 0.40  # Branche SPLIT si best ∈ [0.40, 0.45)


# ──────────────────────────────────────────────────────────────────────────────
# Cas terrain
# ──────────────────────────────────────────────────────────────────────────────

CASES = [
    {
        "id": "C1",
        "message": "Les carottes en ragoût recette",
        "false_match": "carottes dans jardin",
        "oracle_candidates": ["recettes santé culinaire", "recette rapide"],
    },
    {
        "id": "C2",
        "message": "Planifier des vacances en Normandie",
        "false_match": "Pourquoi elle ne germent pas",
        "oracle_candidates": ["voyage organisation", "réservation voyage"],
    },
    {
        "id": "C3",
        "message": "recette carotte citron pour 6 personnes ingrédients riches en fer",
        "false_match": "Pourquoi elle ne germent pas",
        "oracle_candidates": ["recettes santé culinaire"],
    },
    {
        "id": "C4",
        "message": "Tu vas bien ?",
        "false_match": "semis en intérieur",
        "oracle_candidates": ["salutation"],
    },
    # C5 : conversation 4 tours — chaque tour scoré séparément.
    {
        "id": "C5_T1",
        "message": (
            "En fait c'est une recette carotte citron pour 6 personnes "
            "avec des ingrédients qui contiennent du fer qu'il me faut."
        ),
        "false_match": "Pourquoi elle ne germent pas",
        "oracle_candidates": ["recettes santé culinaire"],
    },
    {
        "id": "C5_T2",
        "message": "Des lentilles et des épinards, le reste je peux acheter si besoin",
        "false_match": "Pourquoi elle ne germent pas",
        "oracle_candidates": ["recettes santé culinaire"],
    },
    {
        "id": "C5_T3",
        "message": "Une recette carotte citron lentilles épinards pour 6 personnes",
        "false_match": "carottes dans jardin",
        "oracle_candidates": ["recettes santé culinaire"],
    },
    {
        "id": "C5_T4",
        "message": (
            "Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à découper, "
            "un couteau de cuisine, un économe, un piano de cuisine 5 feux, des plats "
            "à gratin, des plats à quiche, les ingrédients de base de cuisine "
            "(huiles, vinaigres, épices, sel)"
        ),
        "false_match": "semis en intérieur",
        "oracle_candidates": ["recettes santé culinaire"],
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Corpus
# ──────────────────────────────────────────────────────────────────────────────

def load_intents(path: str = os.path.expanduser("~/.aria/intents.json")) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = list(data.values())
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("intents.json schema not recognized")
    return [
        {"id": it.get("id"), "name": it.get("name"), "status": it.get("status")}
        for it in items
        if isinstance(it, dict) and it.get("name")
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Décision F1 simulée
# ──────────────────────────────────────────────────────────────────────────────

def f1_decision(scores: np.ndarray, labels: list[str]) -> dict:
    """
    Simule la décision de IntentRecallEngine.resolve avec le seuil prod 0.45.
    Branches simplifiées pour le bench (ATTACH, SPLIT, CREATE) — la vraie
    règle SPLIT compte 'nb scores > 0.40' mais on garde la version de
    l'audit §6 pour comparabilité.
    """
    order = np.argsort(-scores)
    best = float(scores[order[0]])
    best_label = labels[order[0]]
    n_above_split = int(np.sum(scores > SPLIT_LOWER_BOUND))

    if best >= F1_THRESHOLD:
        return {"action": "ATTACH", "intent": best_label, "score": best}
    if n_above_split >= 3:
        return {"action": "SPLIT", "intent": best_label, "score": best,
                "n_above_split": n_above_split}
    return {"action": "CREATE", "intent": None, "score": best}


# ──────────────────────────────────────────────────────────────────────────────
# Métriques par modèle
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_model(spec_tag: str, intents: list[dict]) -> dict:
    spec = next(s for s in REGISTRY if s.tag == spec_tag)
    intent_names = [i["name"] for i in intents]

    print(f"\n── {spec.tag}  {spec.label}")
    enc = UnifiedEncoder(spec, batch_size=32)
    print(f"   loaded in {enc.load_time_s:.1f}s, expected_dim={spec.expected_dim}")

    t0 = time.perf_counter()
    intent_vecs = enc.encode_passages(intent_names)
    t_intents = time.perf_counter() - t0
    actual_dim = int(intent_vecs.shape[1])
    print(f"   encoded {len(intent_names)} intent names in {t_intents:.2f}s, dim={actual_dim}")

    case_results = []
    for case in CASES:
        msg_vec = enc.encode_queries([case["message"]])  # shape (1, dim)
        scores = cosine_matrix(msg_vec, intent_vecs)[0]  # (n_intents,)

        top5 = topk(scores, intent_names, k=5)
        false_match_score = float(scores[intent_names.index(case["false_match"])]) \
            if case["false_match"] in intent_names else None

        oracle_data = []
        for oracle in case["oracle_candidates"]:
            r = rank_of(oracle, scores, intent_names)
            sc = float(scores[intent_names.index(oracle)]) if oracle in intent_names else None
            oracle_data.append({"name": oracle, "rank": r, "score": sc})

        # Choix de l'oracle de référence pour Gap/Recall : celui de score le plus haut
        scored = [o for o in oracle_data if o["score"] is not None]
        primary_oracle = max(scored, key=lambda o: o["score"]) if scored else None
        gap = (primary_oracle["score"] - false_match_score) \
            if primary_oracle and false_match_score is not None else None

        decision = f1_decision(scores, intent_names)

        case_results.append({
            "case": case["id"],
            "message": case["message"],
            "top5": [{"score": s, "name": n} for s, n in top5],
            "oracles": oracle_data,
            "primary_oracle": primary_oracle["name"] if primary_oracle else None,
            "false_match": case["false_match"],
            "false_match_score": false_match_score,
            "gap": gap,
            "decision": decision,
        })

    # ─── Métriques agrégées ─────────────────────────────────────────────
    recall_at_1 = []
    recall_at_3 = []
    gaps = []
    for c in case_results:
        if c["primary_oracle"] is None:
            continue
        ranks = [o["rank"] for o in c["oracles"] if o["rank"] is not None]
        if not ranks:
            continue
        best_rank = min(ranks)
        recall_at_1.append(1 if best_rank == 1 else 0)
        recall_at_3.append(1 if best_rank <= 3 else 0)
        if c["gap"] is not None:
            gaps.append(c["gap"])

    # Spread : score(top1) - médiane(scores) sur le 1er cas comme proxy
    # Mieux : moyenne sur tous les cas
    spreads = []
    for c in case_results:
        scs = [t["score"] for t in c["top5"]]
        if scs:
            # On ne dispose pas de la médiane des 60 ici directement, on ré-encode
            pass

    # Pour spread complet on retourne juste la métrique agrégée plus tard
    # via pairwise_distribution (qui a tous les scores).
    metrics = {
        "n_cases_with_oracle": len(recall_at_1),
        "recall_at_1": float(np.mean(recall_at_1)) if recall_at_1 else None,
        "recall_at_3": float(np.mean(recall_at_3)) if recall_at_3 else None,
        "gap_mean": float(np.mean(gaps)) if gaps else None,
        "gap_min": float(np.min(gaps)) if gaps else None,
        "gap_max": float(np.max(gaps)) if gaps else None,
    }

    print(f"   Recall@1 = {metrics['recall_at_1']:.2f} | "
          f"Recall@3 = {metrics['recall_at_3']:.2f} | "
          f"Gap moyen = {(metrics['gap_mean'] or 0):+.3f}")

    return {
        "tag": spec.tag,
        "hf_id": spec.hf_id,
        "label": spec.label,
        "expected_dim": spec.expected_dim,
        "actual_dim": actual_dim,
        "load_time_s": enc.load_time_s,
        "encode_intents_time_s": t_intents,
        "cases": case_results,
        "metrics": metrics,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    intents = load_intents()
    print(f"Corpus : {len(intents)} intents (depuis ~/.aria/intents.json)")
    print(f"Cas    : {len(CASES)} cas terrain")

    report = {
        "n_intents": len(intents),
        "intents": intents,
        "cases": CASES,
        "f1_threshold": F1_THRESHOLD,
        "split_lower_bound": SPLIT_LOWER_BOUND,
        "models": [],
    }

    tags = sys.argv[1:] if len(sys.argv) > 1 else [s.tag for s in REGISTRY]
    for tag in tags:
        try:
            r = evaluate_model(tag, intents)
            report["models"].append(r)
        except Exception as e:
            import traceback
            traceback.print_exc()
            report["models"].append({"tag": tag, "error": str(e)})

    out_path = Path("/tmp/aria_bench_quality.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"\n→ {out_path}")

    # Tableau récap final
    print("\n=== Synthèse ===")
    print(f"{'Tag':<4} {'Dim':>5} {'R@1':>6} {'R@3':>6} {'Gap':>8} {'Load(s)':>8}")
    for m in report["models"]:
        if "error" in m:
            print(f"{m['tag']:<4}  ERROR: {m['error']}")
            continue
        mt = m["metrics"]
        print(
            f"{m['tag']:<4} "
            f"{m['actual_dim']:>5} "
            f"{(mt['recall_at_1'] or 0):>6.2f} "
            f"{(mt['recall_at_3'] or 0):>6.2f} "
            f"{(mt['gap_mean'] or 0):>+8.3f} "
            f"{m['load_time_s']:>8.1f}"
        )


if __name__ == "__main__":
    main()
