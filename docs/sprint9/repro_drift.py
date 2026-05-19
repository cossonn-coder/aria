"""
repro_drift.py — Reproduction contrôlée du drift sqlite/HNSW (dette #20).

Cible : isoler quelle méthode de fermeture du palace MemPalace flushe
réellement le HNSW sur disque et laquelle laisse le drift en place.

Métriques observées (version étendue T-Drift-HNSW-Metric)
---------------------------------------------------------

1. **Drift filesystem** : `mtime(chroma.sqlite3) − mtime(data_level0.bin)`.
   Métrique historique, exactement celle utilisée par
   `mempalace.backends.chroma.quarantine_stale_hnsw` au load.

2. **Pickle mtime delta** : `mtime(index_metadata.pickle)` échantillonné
   juste avant la séquence de fermeture (sampler interne du runner),
   après la fermeture (parent), et après le reload. `index_metadata.pickle`
   est écrit UNIQUEMENT par `PersistentLocalHnswSegment._persist()` —
   c'est donc un témoin direct de flush, sans contamination mmap.

3. **`_persist` call log** : monkey-patch posé en début de runner sur
   `PersistentLocalHnswSegment._persist`. Chaque appel est tracé avec
   timestamp, segment_id, `_num_log_records_since_last_persist`, et la
   frame caller (qui a appelé `_persist` : `_apply_batch`, `stop`, ou
   code externe). Log : `/tmp/aria_drift_repro/persist_calls.log`.

Usage
-----
    # Orchestrateur — lance toutes les méthodes et imprime le tableau
    python docs/sprint9/repro_drift.py driver

    # Worker — appelé par le driver, ne pas lancer à la main sauf debug
    python docs/sprint9/repro_drift.py runner <palace_path> <method>

Le script crée un palace neuf par méthode dans /tmp/aria_drift_repro/<method>,
écrit 50 documents (largement sous le sync_threshold de 50 000 du fork),
applique la méthode de fermeture, recharge le palace, mesure les
métriques 1/2/3.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


METHODS = [
    "no-close",           # exit naturel, aucune fermeture explicite
    "backend-close",      # ChromaBackend.close() (chemin "propre" fork)
    "client-close",       # PersistentClient.close() direct sans passer par le fork
    "client-context-mgr", # with chromadb.PersistentClient(...) as client:
    "persist-then-close", # accès interne _persist() puis backend.close()
    "sigterm",            # subprocess + os.kill(pid, SIGTERM) — le scénario systemctl stop
    "sigkill",            # subprocess + os.kill(pid, SIGKILL) — référence "perte garantie"
]


# Log global partagé par tous les runners (un fichier, sections par méthode).
PERSIST_LOG_PATH = "/tmp/aria_drift_repro/persist_calls.log"


# ---------------------------------------------------------------------------
# Mesure du drift et du pickle mtime
# ---------------------------------------------------------------------------


def _find_segment_dir(palace_path: Path) -> Optional[Path]:
    """Retourne le sous-dossier du segment HNSW, ou None si introuvable."""
    for child in palace_path.iterdir():
        if not child.is_dir():
            continue
        if (child / "data_level0.bin").is_file():
            return child
    return None


def measure_drift(palace_path: Path) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Retourne (sqlite_mtime, hnsw_mtime, drift_seconds).

    drift_seconds = sqlite_mtime − hnsw_mtime, positif quand SQLite est
    plus récent (le cas normal : HNSW lag). None si fichier manquant.
    """
    db = palace_path / "chroma.sqlite3"
    if not db.is_file():
        return None, None, None
    sqlite_mtime = db.stat().st_mtime

    seg_dir = _find_segment_dir(palace_path)
    if seg_dir is None:
        return sqlite_mtime, None, None
    hnsw_mtime = (seg_dir / "data_level0.bin").stat().st_mtime
    return sqlite_mtime, hnsw_mtime, sqlite_mtime - hnsw_mtime


def measure_metadata_mtime(palace_path: Path) -> Optional[float]:
    """Retourne mtime(`index_metadata.pickle`) du segment HNSW, ou None.

    `index_metadata.pickle` n'est touché QUE par `_persist()`. C'est un
    témoin direct du flush, contrairement à `data_level0.bin` qui peut
    être touché par mmap incremental indépendamment de `_persist`.
    """
    seg_dir = _find_segment_dir(palace_path)
    if seg_dir is None:
        return None
    pickle_path = seg_dir / "index_metadata.pickle"
    if not pickle_path.is_file():
        return None
    return pickle_path.stat().st_mtime


# ---------------------------------------------------------------------------
# Monkey-patch instrumentation de `_persist`
# ---------------------------------------------------------------------------


def install_persist_monkeypatch(method: str) -> None:
    """Pose un wrapper autour de `PersistentLocalHnswSegment._persist`.

    Chaque appel à `_persist` est tracé dans PERSIST_LOG_PATH avec :
    - timestamp wall-clock
    - méthode courante (pour filtrer par scénario)
    - segment_id
    - `_num_log_records_since_last_persist` (proxy du volume flushé)
    - frame caller (qui a appelé `_persist` : `_apply_batch`, `stop`, etc.)
    """
    import inspect
    from chromadb.segment.impl.vector.local_persistent_hnsw import (
        PersistentLocalHnswSegment,
    )

    Path(PERSIST_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)

    original = PersistentLocalHnswSegment._persist

    def wrapped(self, *args, **kwargs):
        # Capturer le contexte avant l'appel (le compteur est remis à 0 dedans)
        try:
            seg_id = str(getattr(self, "_id", "?"))
        except Exception:
            seg_id = "?"
        try:
            num_records = getattr(self, "_num_log_records_since_last_persist", -1)
        except Exception:
            num_records = -1

        # Frame caller : la frame [1] est l'appelant direct de _persist.
        # Filename + nom de fonction suffisent à identifier _apply_batch,
        # stop, ou notre forçage manuel.
        caller_repr = "?"
        try:
            stack = inspect.stack()
            if len(stack) >= 2:
                f = stack[1]
                caller_repr = f"{os.path.basename(f.filename)}:{f.lineno}:{f.function}"
        except Exception:
            pass

        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + f".{int((time.time()%1)*1000):03d}"
        line = (
            f"[{ts}] method={method} seg={seg_id} "
            f"num_records_since_last_persist={num_records} caller={caller_repr}\n"
        )
        try:
            with open(PERSIST_LOG_PATH, "a") as fh:
                fh.write(line)
        except Exception:
            pass  # ne jamais faire planter le runner sur un log

        return original(self, *args, **kwargs)

    PersistentLocalHnswSegment._persist = wrapped


# ---------------------------------------------------------------------------
# Runner — exécuté dans le subprocess enfant
# ---------------------------------------------------------------------------


def _write_50_docs(col) -> None:
    docs = [f"document de test numéro {i} — contenu varié" for i in range(50)]
    ids = [f"id_{i:03d}" for i in range(50)]
    col.add(documents=docs, ids=ids)


def _force_persist_via_segment_manager(client) -> dict:
    """Force `_persist()` sur tous les segments HNSW connus du client.

    Chemin canonique : `system.instance(SegmentManager)._instances` —
    le SegmentManager local maintient un dict des SegmentImplementation
    instanciés (cf. `chromadb/segment/impl/manager/local.py:62-101`).

    Retourne un dict de diagnostic : nombre d'instances inspectées,
    nombre d'appels `_persist` réussis, erreurs.
    """
    diag = {"inspected": 0, "persisted": 0, "errors": []}
    try:
        from chromadb.segment import SegmentManager
        from chromadb.segment.impl.vector.local_persistent_hnsw import (
            PersistentLocalHnswSegment,
        )

        seg_mgr = client._system.instance(SegmentManager)
        instances = getattr(seg_mgr, "_instances", {})
        for seg_id, impl in instances.items():
            diag["inspected"] += 1
            if isinstance(impl, PersistentLocalHnswSegment):
                try:
                    impl._persist()
                    diag["persisted"] += 1
                except Exception as exc:
                    diag["errors"].append(f"{seg_id}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        diag["errors"].append(f"top-level: {type(exc).__name__}: {exc}")
    return diag


def _dump_runner_state(palace_path: Path, state: dict) -> None:
    """Écrit l'état échantillonné par le runner dans un fichier lu par le driver."""
    state_path = palace_path / "_runner_state.json"
    try:
        with open(state_path, "w") as fh:
            json.dump(state, fh)
    except Exception as exc:
        print(f"  [runner_state] write failed: {exc}", file=sys.stderr)


def _sample_before_close(palace_path: Path) -> dict:
    """Échantillonne les mtimes juste avant la séquence de fermeture."""
    sqlite_mtime, hnsw_mtime, _ = measure_drift(palace_path)
    pickle_mtime = measure_metadata_mtime(palace_path)
    return {
        "ts_before_close": time.time(),
        "sqlite_mtime_before_close": sqlite_mtime,
        "hnsw_mtime_before_close": hnsw_mtime,
        "pickle_mtime_before_close": pickle_mtime,
    }


def runner(palace_path: Path, method: str) -> None:
    """Worker : ouvre le palace, écrit 50 docs, applique la méthode demandée."""
    # Monkey-patch posé AVANT toute interaction qui pourrait déclencher _persist.
    # Important : l'instrumentation doit voir TOUS les appels, y compris ceux
    # qui surviendraient pendant les add() initiaux.
    install_persist_monkeypatch(method)

    import chromadb
    from mempalace.backends.chroma import ChromaBackend

    backend = ChromaBackend()

    if method == "client-close":
        # Bypass fork — instancier PersistentClient direct
        client = chromadb.PersistentClient(path=str(palace_path))
        col = client.get_or_create_collection("test_col")
        _write_50_docs(col)
        # Petit délai pour différencier mtime SQLite et HNSW (sub-seconde
        # sinon le drift initial peut être 0 et masquer l'effet).
        time.sleep(2)
        col.add(documents=["sentinel-tail"], ids=["sentinel"])
        _dump_runner_state(palace_path, _sample_before_close(palace_path))
        client.close()
        return

    if method == "client-context-mgr":
        with chromadb.PersistentClient(path=str(palace_path)) as client:
            col = client.get_or_create_collection("test_col")
            _write_50_docs(col)
            time.sleep(2)
            col.add(documents=["sentinel-tail"], ids=["sentinel"])
            _dump_runner_state(palace_path, _sample_before_close(palace_path))
        return

    # Tous les autres modes passent par le backend fork
    col = backend.get_or_create_collection(str(palace_path), "test_col")
    _write_50_docs(col)
    time.sleep(2)
    col.add(documents=["sentinel-tail"], ids=["sentinel"])

    if method == "no-close":
        # Sortie naturelle, aucun close. Le GC fera ce qu'il peut.
        _dump_runner_state(palace_path, _sample_before_close(palace_path))
        return

    if method == "backend-close":
        _dump_runner_state(palace_path, _sample_before_close(palace_path))
        backend.close()
        return

    if method == "persist-then-close":
        # Récupérer le client sous-jacent depuis le backend pour forcer _persist
        client = backend._clients.get(str(palace_path))
        state = _sample_before_close(palace_path)
        if client is None:
            state["persist_diag"] = {"error": "client introuvable dans backend._clients"}
            print("  [persist] client introuvable dans backend._clients", file=sys.stderr)
        else:
            diag = _force_persist_via_segment_manager(client)
            state["persist_diag"] = diag
            print(
                f"  [persist] segments inspectés={diag['inspected']} "
                f"persistés={diag['persisted']} errs={diag['errors']}",
                file=sys.stderr,
            )
        _dump_runner_state(palace_path, state)
        backend.close()
        return

    if method in ("sigterm", "sigkill"):
        # Échantillonner AVANT d'attendre le signal — c'est notre meilleure
        # approximation du "before_close" pour les chemins par signal.
        _dump_runner_state(palace_path, _sample_before_close(palace_path))
        # Le driver va nous tuer. On attend.
        print(f"runner ready (pid={os.getpid()}) — waiting for signal", flush=True)
        while True:
            time.sleep(1)


# ---------------------------------------------------------------------------
# Driver — orchestre tous les modes
# ---------------------------------------------------------------------------


def _reset_palace(palace_path: Path) -> None:
    if palace_path.exists():
        shutil.rmtree(palace_path)
    palace_path.mkdir(parents=True)


def _read_runner_state(palace_path: Path) -> dict:
    state_path = palace_path / "_runner_state.json"
    if not state_path.is_file():
        return {}
    try:
        with open(state_path) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _count_persist_calls(method: str) -> tuple[int, list[str]]:
    """Compte les appels `_persist` observés pour `method` dans le log global.

    Retourne (n_calls, lignes_brutes) pour cette méthode.
    """
    log_path = Path(PERSIST_LOG_PATH)
    if not log_path.is_file():
        return 0, []
    needle = f" method={method} "
    lines = []
    try:
        with open(log_path) as fh:
            for line in fh:
                if needle in line:
                    lines.append(line.rstrip("\n"))
    except Exception:
        pass
    return len(lines), lines


def _run_method(base: Path, method: str) -> dict:
    palace_path = base / method
    _reset_palace(palace_path)

    cmd = [sys.executable, __file__, "runner", str(palace_path), method]

    if method in ("sigterm", "sigkill"):
        # Lance en arrière-plan, attend l'écriture, envoie le signal.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            if "runner ready" in line:
                ready = True
                break
        if not ready:
            stdout, stderr = proc.communicate(timeout=5)
            raise RuntimeError(f"runner {method} never signaled ready. stdout={stdout!r} stderr={stderr!r}")

        sig = signal.SIGTERM if method == "sigterm" else signal.SIGKILL
        proc.send_signal(sig)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  ! runner {method} returncode={result.returncode}", file=sys.stderr)
            print(f"    stderr: {result.stderr}", file=sys.stderr)
        else:
            # Echo de la diag du runner pour les méthodes verbeuses (persist-then-close)
            for line in result.stderr.splitlines():
                if "[persist]" in line or "[runner_state]" in line:
                    print(f"    {line}", file=sys.stderr)

    runner_state = _read_runner_state(palace_path)

    # Mesure post-stop, AVANT toute réouverture
    sqlite_mtime, hnsw_mtime, drift_before = measure_drift(palace_path)
    pickle_mtime_after_close = measure_metadata_mtime(palace_path)

    # Recharge — bloc nouveau process, palace_path stable
    reload_cmd = [
        sys.executable, "-c",
        (
            "from mempalace.backends.chroma import ChromaBackend; "
            f"b = ChromaBackend(); "
            f"col = b.get_or_create_collection({str(palace_path)!r}, 'test_col'); "
            f"print('count_after_reload:', col.count())"
        ),
    ]
    reload_result = subprocess.run(reload_cmd, capture_output=True, text=True, timeout=60)
    count_line = next((ln for ln in reload_result.stdout.splitlines()
                       if ln.startswith("count_after_reload")), "")
    count_after = int(count_line.split(":", 1)[1].strip()) if count_line else -1

    pickle_mtime_after_reload = measure_metadata_mtime(palace_path)

    pickle_before = runner_state.get("pickle_mtime_before_close")
    pickle_delta_close = (
        (pickle_mtime_after_close - pickle_before)
        if (pickle_before is not None and pickle_mtime_after_close is not None)
        else None
    )
    pickle_delta_reload = (
        (pickle_mtime_after_reload - pickle_mtime_after_close)
        if (pickle_mtime_after_close is not None and pickle_mtime_after_reload is not None)
        else None
    )

    n_calls, raw_log_lines = _count_persist_calls(method)

    return {
        "method": method,
        "drift_before_reload": drift_before,
        "sqlite_mtime": sqlite_mtime,
        "hnsw_mtime": hnsw_mtime,
        "pickle_mtime_before_close": pickle_before,
        "pickle_mtime_after_close": pickle_mtime_after_close,
        "pickle_mtime_after_reload": pickle_mtime_after_reload,
        "pickle_delta_close": pickle_delta_close,
        "pickle_delta_reload": pickle_delta_reload,
        "persist_calls": n_calls,
        "persist_log_lines": raw_log_lines,
        "persist_diag": runner_state.get("persist_diag"),
        "count_after_reload": count_after,
        "reload_stderr_tail": "\n".join(reload_result.stderr.strip().splitlines()[-5:]),
    }


def driver() -> None:
    base = Path("/tmp/aria_drift_repro")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    # Reset du log global au début du run pour repartir propre
    Path(PERSIST_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    if Path(PERSIST_LOG_PATH).exists():
        Path(PERSIST_LOG_PATH).unlink()

    print(f"# Repro drift HNSW — base={base}")
    print(f"# python={sys.version.split()[0]}")
    try:
        import chromadb
        import mempalace
        print(f"# chromadb={chromadb.__version__} mempalace={getattr(mempalace, '__version__', '?')}")
    except Exception as exc:
        print(f"# imports échec: {exc}")

    results = []
    for method in METHODS:
        print(f"\n→ méthode: {method}", flush=True)
        try:
            r = _run_method(base, method)
        except Exception as exc:
            print(f"  ! exception: {exc}")
            r = {"method": method, "error": str(exc)}
        results.append(r)
        # Affichage immédiat (lignes courtes)
        if "drift_before_reload" in r and r["drift_before_reload"] is not None:
            d = r["drift_before_reload"]
            pd = r.get("pickle_delta_close")
            pds = f"{pd:.3f}s" if isinstance(pd, (int, float)) else "N/A"
            print(
                f"  drift={d:.3f}s | pickle_Δclose={pds} | "
                f"_persist={r.get('persist_calls')} | count_reload={r.get('count_after_reload')}"
            )
        else:
            print(f"  drift = N/A  | err={r.get('error')}")

    # Tableau récap étendu
    print("\n" + "=" * 100)
    print(
        f"{'méthode':<22} | {'drift (s)':>9} | {'pickle_Δclose (s)':>17} | "
        f"{'_persist calls':>14} | {'count reload':>12} | note"
    )
    print("-" * 100)
    for r in results:
        method = r["method"]
        d = r.get("drift_before_reload")
        pd = r.get("pickle_delta_close")
        npc = r.get("persist_calls", 0)
        c = r.get("count_after_reload", -1)
        ds = f"{d:.3f}" if isinstance(d, (int, float)) else "N/A"
        pds = f"{pd:.3f}" if isinstance(pd, (int, float)) else "N/A"
        note = ""
        if c == 51:
            note = "complet"
        elif c == -1:
            note = "reload échec"
        elif c == 0:
            note = "perte totale"
        else:
            note = f"partiel ({c}/51)"
        print(f"{method:<22} | {ds:>9} | {pds:>17} | {npc:>14} | {c:>12} | {note}")

    # Détail log _persist par méthode (utile pour le rapport)
    print("\n" + "=" * 100)
    print("Détail des appels _persist observés (monkey-patch) :")
    for r in results:
        method = r["method"]
        lines = r.get("persist_log_lines") or []
        if not lines:
            print(f"\n[{method}] aucun appel _persist observé")
        else:
            print(f"\n[{method}] {len(lines)} appel(s) :")
            for ln in lines:
                print(f"  {ln}")
        diag = r.get("persist_diag")
        if diag:
            print(f"  diag forçage manuel : {diag}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: repro_drift.py {driver | runner <palace_path> <method>}")
        sys.exit(2)

    cmd = sys.argv[1]
    if cmd == "driver":
        driver()
    elif cmd == "runner":
        if len(sys.argv) != 4:
            print("usage: repro_drift.py runner <palace_path> <method>")
            sys.exit(2)
        runner(Path(sys.argv[2]), sys.argv[3])
    else:
        print(f"unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()
