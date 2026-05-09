# scripts/embedder_bench/benchmark_perf.py
#
# Benchmark perf CPU des 6 modèles d'embedding sur la VM Debian 18 vCPU.
#
# Mesures :
#   - Latence cold     : 1er encode([phrase]) après chargement (taille 1)
#   - Latence warm     : médiane de 100 encode([phrase]) consécutifs
#   - Throughput batch : phrases/s sur 100 phrases batch=32, 3 runs, médiane
#   - RAM résidente    : RSS avant chargement / après chargement / après bench
#   - Taille modèle    : du cache HF (~/.cache/huggingface/hub/models--*/)
#
# Sortie : /tmp/aria_bench_perf.json
#
# Dépendances : sentence-transformers, transformers, torch, numpy, optimum,
#               onnxruntime, psutil.

from __future__ import annotations

import gc
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _models import REGISTRY, UnifiedEncoder  # noqa: E402


# 100 phrases françaises typiques (intents + variations + messages)
SENTENCES = [
    "Bonjour, comment allez-vous aujourd'hui ?",
    "Quelle est la météo prévue pour demain à Paris ?",
    "Recette rapide de gratin dauphinois pour 4 personnes",
    "Comment planter des carottes dans un sol argileux",
    "Vol Paris Lisbonne pas cher en septembre",
    "Comment faire pousser des tomates en pot sur un balcon ?",
    "Liste de courses pour un dîner italien végétarien",
    "Conseils pour réparer un robinet qui fuit",
    "Programme d'entraînement musculation 3 fois par semaine",
    "Conjugaison du verbe avoir au subjonctif présent",
    "Histoire de la Révolution française en quelques dates clés",
    "Comment installer Linux Debian sur un vieux laptop ?",
    "Différence entre un emprunt et un crédit immobilier",
    "Recommandation de livres de science-fiction française",
    "Météo en Bretagne ce weekend pour faire de la voile",
    "Réservation d'une chambre d'hôtel pour deux nuits",
    "Quels exercices pour soulager les douleurs lombaires ?",
    "Recette de soupe à la courge butternut et lait de coco",
    "Comment créer un jardin médicinal dans son potager ?",
    "Stratégie d'épargne pour étudiant qui commence à travailler",
] * 5  # 100 phrases


def model_disk_size(hf_id: str) -> int:
    """Taille du dossier HF du modèle (en octets)."""
    cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    folder_name = "models--" + hf_id.replace("/", "--")
    p = cache / folder_name
    if not p.exists():
        return 0
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                pass
    return total


def benchmark_model(spec_tag: str) -> dict:
    spec = next(s for s in REGISTRY if s.tag == spec_tag)
    print(f"\n── {spec.tag}  {spec.label}")

    proc = psutil.Process()
    rss_before = proc.memory_info().rss

    enc = UnifiedEncoder(spec, batch_size=32)
    rss_after_load = proc.memory_info().rss
    print(f"   loaded in {enc.load_time_s:.1f}s  ΔRSS={(rss_after_load - rss_before) / 1e6:.1f} MB")

    # Cold latency : premier encode([phrase]) — utilise un texte unique, batch 1
    t0 = time.perf_counter()
    _ = enc.encode_queries([SENTENCES[0]])
    cold_latency = time.perf_counter() - t0

    # Warm latency : médiane sur 100 encodes consécutifs (un texte à la fois)
    warm_lats = []
    for s in SENTENCES:
        t0 = time.perf_counter()
        _ = enc.encode_queries([s])
        warm_lats.append(time.perf_counter() - t0)
    warm_median = statistics.median(warm_lats)
    warm_p95 = float(np.percentile(warm_lats, 95))

    # Throughput batch=32 : 100 phrases, 3 runs
    runs = []
    for _ in range(3):
        t0 = time.perf_counter()
        _ = enc.encode_queries(SENTENCES)
        runs.append(time.perf_counter() - t0)
    throughput_runs = [len(SENTENCES) / r for r in runs]
    throughput_median = statistics.median(throughput_runs)

    rss_peak = proc.memory_info().rss
    print(f"   cold={cold_latency * 1000:.0f}ms | "
          f"warm_med={warm_median * 1000:.0f}ms | "
          f"warm_p95={warm_p95 * 1000:.0f}ms | "
          f"throughput={throughput_median:.1f}/s | "
          f"RSS peak={(rss_peak - rss_before) / 1e6:.1f} MB")

    return {
        "tag": spec.tag,
        "hf_id": spec.hf_id,
        "label": spec.label,
        "load_time_s": enc.load_time_s,
        "cold_latency_s": cold_latency,
        "warm_latency_median_s": warm_median,
        "warm_latency_p95_s": warm_p95,
        "throughput_batch32_runs": throughput_runs,
        "throughput_batch32_median_per_s": throughput_median,
        "rss_before_bytes": rss_before,
        "rss_after_load_bytes": rss_after_load,
        "rss_peak_bytes": rss_peak,
        "rss_load_delta_mb": (rss_after_load - rss_before) / 1e6,
        "rss_peak_delta_mb": (rss_peak - rss_before) / 1e6,
        "model_disk_bytes": model_disk_size(spec.hf_id),
    }


def free_memory():
    """Tente de libérer la mémoire entre modèles."""
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
    except Exception:
        pass


def main():
    print(f"VM : 18 vCPU, pas de GPU. Bench perf {len(SENTENCES)} phrases.")

    report = {"n_sentences": len(SENTENCES), "models": []}

    tags = sys.argv[1:] if len(sys.argv) > 1 else [s.tag for s in REGISTRY]
    for tag in tags:
        try:
            r = benchmark_model(tag)
            report["models"].append(r)
        except Exception as e:
            import traceback
            traceback.print_exc()
            report["models"].append({"tag": tag, "error": str(e)})
        free_memory()

    out_path = Path("/tmp/aria_bench_perf.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"\n→ {out_path}")

    print("\n=== Synthèse perf ===")
    print(f"{'Tag':<4} {'Dim?':>5} {'Cold':>7} {'Warm':>7} {'P95':>7} {'P/s':>7} {'RSS MB':>8} {'Disk':>10}")
    for m in report["models"]:
        if "error" in m:
            print(f"{m['tag']:<4}  ERROR: {m['error']}")
            continue
        disk_mb = m["model_disk_bytes"] / 1e6
        print(
            f"{m['tag']:<4} "
            f"{'-':>5} "
            f"{m['cold_latency_s'] * 1000:>6.0f}ms "
            f"{m['warm_latency_median_s'] * 1000:>6.0f}ms "
            f"{m['warm_latency_p95_s'] * 1000:>6.0f}ms "
            f"{m['throughput_batch32_median_per_s']:>6.1f} "
            f"{m['rss_peak_delta_mb']:>8.1f} "
            f"{disk_mb:>9.0f}M"
        )


if __name__ == "__main__":
    main()
