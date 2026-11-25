# tests/scripts/test_feedback_report.py
#
# Rapport et ligne d'alerte des retours 👍 / 😢 (sprint 67, tronçon 02) sur des
# fiches factices. La lecture réelle du palace n'est pas exercée ici.

from scripts import feedback_report as report

_ENTRIES = [
    {"id": "tg_42_1", "timestamp": "2026-11-25T10:00:00+00:00", "reaction": "👍",
     "comment": "", "request": "/parties", "text": "Bilan des parties"},
    {"id": "tg_42_2", "timestamp": "2026-11-25T11:00:00+00:00", "reaction": "😢",
     "comment": "trop long", "request": "analyse", "text": "Un très long pavé"},
    {"id": "tg_42_3", "timestamp": "2026-11-25T12:00:00+00:00", "reaction": "",
     "comment": "", "request": "salut", "text": "Bonjour Nico"},
]


def test_build_report_counts_and_lists_sad_first():
    text = report.build_report(_ENTRIES, "2026-11-24", now="2026-11-25T13:00:00+00:00")
    lines = text.splitlines()
    assert lines[0] == "Jusqu'au : 2026-11-25T13:00:00+00:00"
    assert "Messages notés : 3 — 👍 1 · 😢 1 · autres réactions 0 · sans réaction 1" in text
    assert "Commentaire : trop long" in text
    assert text.index("tg_42_2") < text.index("tg_42_1")
    assert "tg_42_3" not in text


def test_alert_line_counts_reactions():
    assert report.alert_line(_ENTRIES, "2026-11-24T08:00:00+00:00") == (
        "ARIA : 2 nouveaux retours dont 1 😢 depuis le 2026-11-24 → lance /amelioration")


def test_alert_line_empty_without_reaction():
    assert report.alert_line([_ENTRIES[2]], None) == ""
