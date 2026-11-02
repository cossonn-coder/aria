# tests/scripts/test_migrate_chess_rooms.py
#
# Plan de migration des fiches de parties (sprint 46, tronçon 04) sur des fiches
# factices. L'exécution réelle est vérifiée sur une copie du palace, pas ici.

import json
from unittest.mock import MagicMock

from scripts import migrate_chess_rooms as migration

_GORING = ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "c2c3"]


def _game(doc_id, opponent, ucis=_GORING, **extra):
    return {"id": doc_id, "opponent": opponent, "room": "chess", "eco": "",
            "plies_json": json.dumps([{"uci": uci} for uci in ucis]), **extra}


def test_plan_deletes_own_usernames_case_insensitive():
    plan = migration.build_plan([_game("a", "la_bagouze"), _game("b", "NICO"), _game("c", "Bob42")])
    assert [game["id"] for game in plan.deletions] == ["a", "b"]


def test_plan_moves_goring_to_its_room():
    plan = migration.build_plan([_game("a", "Bob42")])
    update = plan.updates[0]
    assert update["doc_id"] == "a"
    assert update["room"] == "chess_goring-gambit"
    assert update["opening_group"] == "Göring Gambit"
    assert update["eco"] == "C44"


def test_plan_keeps_eco_of_the_game():
    plan = migration.build_plan([_game("a", "Bob42", eco="C45")])
    assert plan.updates[0]["eco"] == "C45"


def test_plan_reports_unrecognized_without_update():
    plan = migration.build_plan([_game("a", "Bob42", ucis=[])])
    assert [game["id"] for game in plan.unrecognized] == ["a"]
    assert plan.updates == []


def test_plan_is_empty_once_migrated():
    update = migration.build_plan([_game("a", "Bob42")]).updates[0]
    migrated = _game("a", "Bob42", **{k: v for k, v in update.items() if k != "doc_id"})
    assert migration.build_plan([migrated]).updates == []


def test_dry_run_writes_nothing(monkeypatch):
    monkeypatch.setattr(migration, "load_games", lambda: [_game("a", "La_Bagouze"), _game("b", "Bob42")])
    delete, update = MagicMock(), MagicMock()
    monkeypatch.setattr(migration, "delete_chess_games", delete)
    monkeypatch.setattr(migration, "update_chess_game_opening", update)
    assert migration.main([]) == 0
    delete.assert_not_called()
    update.assert_not_called()


def test_apply_refused_when_service_active_on_config_palace(monkeypatch):
    monkeypatch.setattr(migration.subprocess, "run", lambda *a, **k: MagicMock(stdout="active\n"))
    assert migration.service_blocks("/p/palace", "/p/palace") is True
    assert migration.service_blocks("/copy/palace", "/p/palace") is False
