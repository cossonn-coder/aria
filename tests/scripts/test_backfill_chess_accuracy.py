# tests/scripts/test_backfill_chess_accuracy.py
#
# Plan du rattrapage sprint 55 sur des fiches factices. L'exécution réelle est
# vérifiée par le contrôle de relecture du script, pas ici.

import json

from scripts import backfill_chess_accuracy as backfill

_PLY = {"color": "white", "win_before": 50.0, "win_after": 50.0, "loss": 0.0, "quality": "best"}


def _game(doc_id, opponent="Bob42", **extra):
    return {"id": doc_id, "opponent": opponent, "nico_color": "white",
            "plies_json": json.dumps([_PLY]), **extra}


def test_plan_deletes_tests_and_fills_missing_accuracy_only():
    deletions, updates = backfill.build_plan(
        [_game("t", opponent="Test"), _game("a"), _game("b", accuracy=80.0)])
    assert [g["id"] for g in deletions] == ["t"]
    assert updates == [("a", 100.0)]
