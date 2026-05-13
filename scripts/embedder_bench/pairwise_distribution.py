# scripts/embedder_bench/pairwise_distribution.py
#
# Distribution des similarités cosine pairwise entre tous les noms d'intents.
# Reproduit l'analyse §5 audit sprint 5 (60 intents → 1770 paires) sur chaque
# modèle d'embedding du benchmark.
#
# Métriques produites :
#   - max pairwise (un modèle plat aura un max ~0.65, un modèle discriminant > 0.85)
#   - top 10 paires
#   - histogramme par buckets de 0.05
#   - count des paires > 0.85, > 0.70, > 0.50
#   - spread = score(top1) - médiane (sur tous les scores pairwise)
#
# Sortie :
#   /tmp/aria_bench_pairwise.json
#
# Dépendances pip : sentence-transformers, transformers, torch, numpy,
#                   optimum, onnxruntime.

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import REGISTRY, UnifiedEncoder, cosine_matrix  # noqa: E402


def load_intent_names(path: str = os.path.expanduser("~/.aria/intents.json")) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = list(data.values()) if isinstance(data, dict) else data
    return [it["name"] for it in items if isinstance(it, dict) and it.get("name")]


def pairwise_analysis(vecs: np.ndarray, names: list[str]) -> dict:
    """
    Calcule la matrice cosine et extrait les métriques de discriminabilité.
    Suppose vecs déjà L2-normalisés.
    """
    n = len(names)
    sim = cosine_matrix(vecs, vecs)  # (n, n)
    # On garde la triangulaire supérieure stricte (i < j)
    iu = np.triu_indices(n, k=1)
    pair_scores = sim[iu]

    # Top 10 paires
    order = np.argsort(-pair_scores)
    top10 = []
    for k in order[:10]:
        i, j = iu[0][k], iu[1][k]
        top10.append({
            "score": float(pair_scores[k]),
            "a": names[i],
            "b": names[j],
        })

    # Histogramme par buckets de 0.05 entre 0 et 1
    buckets = [round(b, 2) for b in np.arange(0.0, 1.05, 0.05)]
    histo = {}
    for lo, hi in zip(buckets[:-1], buckets[1:]):
        cnt = int(np.sum((pair_scores >= lo) & (pair_scores < hi)))
        histo[f"[{lo:.2f},{hi:.2f})"] = cnt

    return {
        "n_intents": n,
        "n_pairs": int(len(pair_scores)),
        "max_pairwise": float(np.max(pair_scores)),
        "min_pairwise": float(np.min(pair_scores)),
        "median_pairwise": float(np.median(pair_scores)),
        "mean_pairwise": float(np.mean(pair_scores)),
        "p95_pairwise": float(np.percentile(pair_scores, 95)),
        "spread_top1_minus_median": float(np.max(pair_scores) - np.median(pair_scores)),
        "count_above_0_85": int(np.sum(pair_scores > 0.85)),
        "count_above_0_70": int(np.sum(pair_scores > 0.70)),
        "count_above_0_50": int(np.sum(pair_scores > 0.50)),
        "top10_pairs": top10,
        "histogram_bucket_0_05": histo,
    }


def main():
    names = load_intent_names()
    print(f"Corpus : {len(names)} intents → {len(names) * (len(names) - 1) // 2} paires")

    report = {"n_intents": len(names), "models": []}

    tags = sys.argv[1:] if len(sys.argv) > 1 else [s.tag for s in REGISTRY]
    for tag in tags:
        spec = next(s for s in REGISTRY if s.tag == tag)
        print(f"\n── {spec.tag}  {spec.label}")
        try:
            enc = UnifiedEncoder(spec)
            t0 = time.perf_counter()
            vecs = enc.encode_passages(names)
            dt = time.perf_counter() - t0
            print(f"   encoded in {dt:.2f}s")
            stats = pairwise_analysis(vecs, names)
            print(f"   max={stats['max_pairwise']:.3f} | "
                  f"median={stats['median_pairwise']:.3f} | "
                  f"spread={stats['spread_top1_minus_median']:.3f} | "
                  f"#>0.85={stats['count_above_0_85']} | "
                  f"#>0.70={stats['count_above_0_70']}")
            report["models"].append({
                "tag": spec.tag,
                "hf_id": spec.hf_id,
                "label": spec.label,
                "actual_dim": int(vecs.shape[1]),
                "stats": stats,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            report["models"].append({"tag": tag, "error": str(e)})

    out_path = Path("/tmp/aria_bench_pairwise.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"\n→ {out_path}")

    # Tableau récap
    print("\n=== Synthèse pairwise ===")
    print(f"{'Tag':<4} {'Dim':>5} {'Max':>6} {'Med':>6} {'Spread':>7} {'>0.85':>6} {'>0.70':>6} {'>0.50':>6}")
    for m in report["models"]:
        if "error" in m:
            print(f"{m['tag']:<4}  ERROR: {m['error']}")
            continue
        s = m["stats"]
        print(
            f"{m['tag']:<4} "
            f"{m['actual_dim']:>5} "
            f"{s['max_pairwise']:>6.3f} "
            f"{s['median_pairwise']:>6.3f} "
            f"{s['spread_top1_minus_median']:>7.3f} "
            f"{s['count_above_0_85']:>6} "
            f"{s['count_above_0_70']:>6} "
            f"{s['count_above_0_50']:>6}"
        )


if __name__ == "__main__":
    main()
