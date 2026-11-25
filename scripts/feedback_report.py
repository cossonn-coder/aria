#!/usr/bin/env python3
# scripts/feedback_report.py
#
# Rapport des retours 👍 / 😢 de Nico sur les messages Telegram d'ARIA (sprint 67).
# Lecture seule du palace via le bridge (règle 2) : aucune écriture, Claude Code ne
# doit jamais écrire dans le palace pendant que le service tourne (décision 5).
#
# Le point de départ est lu sur la première ligne du dernier rapport
# docs/amelioration/*.md (« Jusqu'au : <ISO> ») : ce qui a déjà été traité par
# /amelioration n'est pas recompté.
#
# Sortie par print : script CLI hors service, comme count_memory_by_wing.py.
#
# Usage :
#   python scripts/feedback_report.py                     # rapport complet
#   python scripts/feedback_report.py --since 2026-11-25  # forcer le point de départ
#   python scripts/feedback_report.py --alerte            # une ligne pour le hook SessionStart

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "docs" / "amelioration"
SINCE_PREFIX = "Jusqu'au : "
SAD, THUMB = "😢", "👍"
TEXT_LIMIT = 600


def last_report_since(reports_dir: Path = REPORTS_DIR) -> str | None:
    """Horodatage « Jusqu'au » du rapport le plus récent (tri par nom), None sinon."""
    reports = sorted(reports_dir.glob("*.md")) if reports_dir.is_dir() else []
    if not reports:
        return None
    first_line = reports[-1].read_text(encoding="utf-8").splitlines()[0]
    return first_line.removeprefix(SINCE_PREFIX).strip()


def _reacted(entries: list[dict]) -> list[dict]:
    """Messages réagis, 😢 d'abord, puis 👍, puis les autres réactions (ordre stable)."""
    order = {SAD: 0, THUMB: 1}
    reacted = [e for e in entries if e.get("reaction")]
    return sorted(reacted, key=lambda e: order.get(e["reaction"], 2))


def _since_label(since: str | None) -> str:
    return since[:10] if since else "début"


def build_report(entries: list[dict], since: str | None, now: str | None = None) -> str:
    """Rapport texte : en-tête de compteurs puis chaque message réagi, 😢 d'abord.
    now (ISO UTC) est injectable pour les tests ; par défaut, l'instant présent."""
    now = now or datetime.now(timezone.utc).isoformat()
    reactions = [e.get("reaction", "") for e in entries]
    n_thumb = reactions.count(THUMB)
    n_sad = reactions.count(SAD)
    n_none = reactions.count("")
    n_other = len(reactions) - n_thumb - n_sad - n_none

    lines = [
        f"{SINCE_PREFIX}{now}",
        f"Période : depuis le {_since_label(since)} jusqu'au {now[:10]}",
        f"Messages notés : {len(entries)} — {THUMB} {n_thumb} · {SAD} {n_sad} · "
        f"autres réactions {n_other} · sans réaction {n_none}",
    ]
    for e in _reacted(entries):
        text = e.get("text", "")
        if len(text) > TEXT_LIMIT:
            text = text[:TEXT_LIMIT] + "…"
        lines += [
            "",
            f"--- {e.get('timestamp', '')[:16]} {e['reaction']} (id {e.get('id', '')})",
            f"Commentaire : {e.get('comment') or '(aucun)'}",
            f"Demande : {e.get('request') or '(inconnue)'}",
            f"Message : {text}",
        ]
    return "\n".join(lines)


def alert_line(entries: list[dict], since: str | None) -> str:
    """Une ligne d'alerte s'il y a au moins une réaction nouvelle, chaîne vide sinon."""
    reacted = [e for e in entries if e.get("reaction")]
    if not reacted:
        return ""
    n_sad = sum(1 for e in reacted if e["reaction"] == SAD)
    return (f"ARIA : {len(reacted)} nouveaux retours dont {n_sad} {SAD} "
            f"depuis le {_since_label(since)} → lance /amelioration")


def load_entries(since: str | None) -> list[dict]:
    """Lecture des fiches aria_feedback, même construction du bridge que core/kernel.py."""
    from memory.mempalace_bridge import MempalaceBridge
    from memory.mempalace_store import get_by_metadata as mempalace_get_by_metadata
    from memory.mempalace_store import search as mempalace_search

    bridge = MempalaceBridge(store=mempalace_search, get_by_metadata=mempalace_get_by_metadata)
    return bridge.load_feedback(since)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport des retours 👍 / 😢 sur ARIA.")
    parser.add_argument("--since", help="AAAA-MM-JJ, force le point de départ")
    parser.add_argument("--alerte", action="store_true", help="une ligne pour le hook SessionStart")
    args = parser.parse_args()

    if args.alerte:
        # Seul try/except justifié : le démarrage de Claude Code ne doit jamais être gêné.
        try:
            since = args.since or last_report_since()
            line = alert_line(load_entries(since), since)
            if line:
                print(line)
        except Exception:
            pass
        return 0

    since = args.since or last_report_since()
    print(build_report(load_entries(since), since))
    return 0


if __name__ == "__main__":
    sys.exit(main())
