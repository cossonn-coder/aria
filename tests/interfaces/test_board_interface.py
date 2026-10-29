# Tests du serveur de l'échiquier ARIA (sprint 35, tronçon 01) : passe factice, port éphémère.

import json
import threading
import time
import urllib.error
import urllib.request

import chess
import pytest

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


def test_index_serves_chessboard_page(monkeypatch):
    # Sprint 35, tronçon 02 : la page servie importe chessground (Maia non chargé en test).
    monkeypatch.setattr("interfaces.board_interface._load_maia_in_background", lambda: None)
    server = make_server(0, BoardWorker(lambda: object(), ""))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        with urllib.request.urlopen(url) as response:
            page = response.read().decode()
        assert "https://cdn.jsdelivr.net/npm/chessground@9.2.1/+esm" in page
        # Sprint 37, tronçon 02 : cases des calques piège (cyan) et stratégie (rose).
        assert "show-trap" in page and "show-strategy" in page
        # Sprint 38, tronçon 02 : zone PGN et courbe d'évaluation.
        assert 'id="pgn"' in page and 'id="graph"' in page
        # Sprint 39, tronçon 03 : export, envoi à ARIA, « Je joue » ; tronçon 07 : plus de pseudo injecté.
        assert 'id="export"' in page and 'id="send"' in page and 'id="playing"' in page
        assert 'const NICO_NAME = "Nico"' in page and "USERNAME" not in page
        # Sprint 39, tronçon 05 : champs des noms des joueurs.
        assert 'id="name-white"' in page and 'id="name-black"' in page
        # Tronçon 08 : liste des coups sous la courbe.
        assert 'id="moves"' in page
    finally:
        server.shutdown()
        server.server_close()


def test_game_returns_white_win_curve(monkeypatch):
    # Sprint 38, tronçon 01 : % de gain des blancs par position, PGN sans en-tête accepté.
    # Sprint 39, tronçon 01 : mat forcé côté blancs et meilleur coup par position.
    from types import SimpleNamespace

    import interfaces.board_interface as board_interface

    plies = [SimpleNamespace(color="white", win_before=60, win_after=45, eval_before_cp=99997,
                             eval_after_cp=-40, best_san="Qh5"),
             SimpleNamespace(color="black", win_before=55, win_after=30, eval_before_cp=-40,
                             eval_after_cp=-99999, best_san="Nf6")]
    monkeypatch.setattr(board_interface, "analyze_game", lambda game, color, path: plies)
    server = make_server(0, BoardWorker(lambda: object(), ""))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert _request(base, "/game", {"pgn": "1. e4 e5"}) == {
            "wins": [60, 45, 70], "mates": [3, None, -1], "best": ["Qh5", "Nf6", None]}
    finally:
        server.shutdown()
        server.server_close()


def test_eval_returns_position_eval(monkeypatch):
    # Sprint 39, tronçon 01 : une position seule (jeu libre), évaluation factice.
    import interfaces.board_interface as board_interface

    monkeypatch.setattr(board_interface, "position_eval",
                        lambda fen: {"win": 52.3, "mate": None, "best": fen.split()[1]})
    server = make_server(0, BoardWorker(lambda: object(), ""))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert _request(base, "/eval", {"fen": _AFTER_E4}) == {"win": 52.3, "mate": None, "best": "b"}
    finally:
        server.shutdown()
        server.server_close()


def test_position_eval_checkmated_skips_engine():
    # Sprint 39, tronçon 01 : position matée → pas de Stockfish, blancs matés = 0 %.
    from interfaces.board_interface import position_eval

    fools_mate = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
    assert position_eval(fools_mate) == {"win": 0, "mate": None, "best": None}


def test_send_hands_pgn_to_aria_or_503():
    # Sprint 39, tronçon 02 : /send remet le PGN à la fonction d'envoi injectée.
    received = []
    server = make_server(0, BoardWorker(lambda: object(), ""), submit_text=lambda t: received.append(t) or True)
    bare = make_server(0, BoardWorker(lambda: object(), ""))
    for s in (server, bare):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        assert _request(f"http://127.0.0.1:{server.server_address[1]}", "/send", {"pgn": "1. e4 *"}) == {"sent": True}
        assert received == ["1. e4 *"]
        with pytest.raises(urllib.error.HTTPError) as err:
            _request(f"http://127.0.0.1:{bare.server_address[1]}", "/send", {"pgn": "1. e4 *"})
        assert err.value.code == 503
    finally:
        for s in (server, bare):
            s.shutdown()
            s.server_close()
