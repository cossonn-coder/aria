"""
repro_drift.py — Reproduction contrôlée du drift sqlite/HNSW (dette #20).

Cible : isoler quelle méthode de fermeture du palace MemPalace flushe
réellement le HNSW sur disque et laquelle laisse le drift en place.

Métrique : delta entre mtime de `chroma.sqlite3` et mtime de
`data_level0.bin` du segment vecteur. C'est exactement la métrique
utilisée par `mempalace.backends.chroma.quarantine_stale_hnsw` au load.

Usage :
    # Orchestrateur — lance toutes les méthodes et imprime le tableau
    python docs/sprint9/repro_drift.py driver

    # Worker — appelé par le driver, ne pas lancer à la main sauf debug
    python docs/sprint9/repro_drift.py runner <palace_path> <method>

Le script crée un palace neuf par méthode dans /tmp/aria_drift_repro/<method>,
écrit 50 documents (largement sous le sync_threshold de 50 000 du fork),
applique la méthode de fermeture, recharge le palace, mesure le drift.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Mesure du drift
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

    drift_seconds = sqlite_mtime - hnsw_mtime, positif quand SQLite est
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


# ---------------------------------------------------------------------------
# Runner — exécuté dans le subprocess enfant
# ---------------------------------------------------------------------------


def _write_50_docs(col) -> None:
    docs = [f"document de test numéro {i} — contenu varié" for i in range(50)]
    ids = [f"id_{i:03d}" for i in range(50)]
    col.add(documents=docs, ids=ids)


def _force_persist_via_internal(client) -> None:
    """Tente d'appeler _persist() sur le segment HNSW via l'API interne.

    L'API interne change entre versions de chromadb. On itère sur les
    composants du System et on appelle _persist sur tout segment qui
    l'expose. Best-effort : si la structure change, on log et continue.
    """
    try:
        system = client._system
    except AttributeError:
        print("  [persist] client._system inaccessible — abort", file=sys.stderr)
        return

    persisted = 0
    for component in system.components():
        if hasattr(component, "_persist"):
            try:
                component._persist()
                persisted += 1
            except Exception as exc:
                print(f"  [persist] {type(component).__name__}._persist() failed: {exc}", file=sys.stderr)

    if persisted == 0:
        print("  [persist] aucun composant n'expose _persist()", file=sys.stderr)
    else:
        print(f"  [persist] _persist appelé sur {persisted} composant(s)", file=sys.stderr)


def runner(palace_path: Path, method: str) -> None:
    """Worker : ouvre le palace, écrit 50 docs, applique la méthode demandée."""
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
        client.close()
        return

    if method == "client-context-mgr":
        with chromadb.PersistentClient(path=str(palace_path)) as client:
            col = client.get_or_create_collection("test_col")
            _write_50_docs(col)
            time.sleep(2)
            col.add(documents=["sentinel-tail"], ids=["sentinel"])
        return

    # Tous les autres modes passent par le backend fork
    col = backend.get_or_create_collection(str(palace_path), "test_col")
    _write_50_docs(col)
    time.sleep(2)
    col.add(documents=["sentinel-tail"], ids=["sentinel"])

    if method == "no-close":
        # Sortie naturelle, aucun close. Le GC fera ce qu'il peut.
        return

    if method == "backend-close":
        backend.close()
        return

    if method == "persist-then-close":
        # Récupérer le client sous-jacent depuis le backend pour forcer _persist
        client = backend._clients.get(str(palace_path))
        if client is None:
            print("  [persist] client introuvable dans backend._clients", file=sys.stderr)
        else:
            _force_persist_via_internal(client)
        backend.close()
        return

    if method in ("sigterm", "sigkill"):
        # Le driver va nous tuer. On attend.
        print(f"runner ready (pid={os.getpid()}) — waiting for signal", flush=True)
        # Boucle d'attente compatible SIGTERM (signal.pause() est suffisant)
        while True:
            time.sleep(1)


# ---------------------------------------------------------------------------
# Driver — orchestre tous les modes
# ---------------------------------------------------------------------------


def _reset_palace(palace_path: Path) -> None:
    if palace_path.exists():
        shutil.rmtree(palace_path)
    palace_path.mkdir(parents=True)


def _run_method(base: Path, method: str) -> dict:
    palace_path = base / method
    _reset_palace(palace_path)

    cmd = [sys.executable, __file__, "runner", str(palace_path), method]

    if method in ("sigterm", "sigkill"):
        # Lance en arrière-plan, attend l'écriture, envoie le signal.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Attendre que le runner ait fini d'écrire (il imprime "runner ready").
        # Timeout 60s en sécurité.
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

    # Mesure post-stop, AVANT toute réouverture
    sqlite_mtime, hnsw_mtime, drift_before = measure_drift(palace_path)

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

    return {
        "method": method,
        "sqlite_mtime": sqlite_mtime,
        "hnsw_mtime": hnsw_mtime,
        "drift_before_reload": drift_before,
        "count_after_reload": count_after,
        "reload_stderr_tail": "\n".join(reload_result.stderr.strip().splitlines()[-5:]),
    }


def driver() -> None:
    base = Path("/tmp/aria_drift_repro")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

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
        # Affichage immédiat
        if "drift_before_reload" in r and r["drift_before_reload"] is not None:
            print(f"  drift = {r['drift_before_reload']:.3f}s  | count après reload = {r['count_after_reload']}")
        else:
            print(f"  drift = N/A  | err={r.get('error')}")

    # Tableau récap
    print("\n" + "=" * 70)
    print(f"{'méthode':<22} | {'drift (s)':>10} | {'count reload':>12} | note")
    print("-" * 70)
    for r in results:
        method = r["method"]
        d = r.get("drift_before_reload")
        c = r.get("count_after_reload", -1)
        ds = f"{d:.3f}" if isinstance(d, (int, float)) else "N/A"
        # 51 = 50 docs + 1 sentinel
        note = ""
        if c == 51:
            note = "complet"
        elif c == -1:
            note = "reload échec"
        elif c == 0:
            note = "perte totale"
        else:
            note = f"partiel ({c}/51)"
        print(f"{method:<22} | {ds:>10} | {c:>12} | {note}")


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
