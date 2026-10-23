# Tests du serveur de l'échiquier ARIA (sprint 35, tronçon 01) : passe factice, port éphémère.

import json
import threading
import time
import urllib.request

import chess

from interfaces.board_interface import BoardWorker, make_server

_AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def _request(base, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request(base + path, data=data)) as response:
        return json.loads(response.read())


def _wait_done(base, position_id):
    for _ in range(200):
        state = _request(base, "/state")
        if state["id"] == position_id and not state["running"]:
            return state
        time.sleep(0.01)
    raise AssertionError(state)


def test_position_then_state_replaces_previous():
    calls = []

    def fake_pass(proxy, fen, elo, models_dir):
        calls.append((fen, elo))
        return {"result": "none", "explosive": None, "forced": {"uci": "x", "san": fen.split()[1]}}

    worker = BoardWorker(lambda: object(), "", run_pass=fake_pass)
    server = make_server(0, worker)
    threading.Thread(target=worker.run, daemon=True).start()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        first = _request(base, "/position", {"fen": chess.STARTING_FEN, "elo_white": 1200, "elo_black": 1800})
        state = _wait_done(base, first["id"])
        assert state["result"] == "none" and state["pass"] == state["passes"] == 4
        assert state["forced"]["san"] == "w"

        second = _request(base, "/position", {"fen": _AFTER_E4, "elo_white": 1200, "elo_black": 1800})
        assert second["id"] == first["id"] + 1
        state = _wait_done(base, second["id"])
        assert state["forced"]["san"] == "b"
        # Maia reçoit l'Elo de l'adversaire du trait.
        assert (chess.STARTING_FEN, 1800) in calls and (_AFTER_E4, 1200) in calls
    finally:
        server.shutdown()
        server.server_close()
