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
        assert state["result"] == "none" and state["pass"] == state["passes"] == 3
        assert state["forced"]["san"] == "w"

        # Sprint 68 : trait au camp du bas (bottom) → analyse_pass, comme avant.
        second = _request(base, "/position", {"fen": _AFTER_E4, "elo_white": 1200, "elo_black": 1800,
                                              "bottom": "black"})
        assert second["id"] == first["id"] + 1
        state = _wait_done(base, second["id"])
        assert state["forced"]["san"] == "b"
        # Maia reçoit l'Elo de l'adversaire du trait.
        assert (chess.STARTING_FEN, 1800) in calls and (_AFTER_E4, 1200) in calls
    finally:
        server.shutdown()
        server.server_close()


def _wait_state(worker, condition):
    for _ in range(200):
        state = worker.state()
        if condition(state):
            return state
        time.sleep(0.01)
    raise AssertionError(state)


def test_head_visible_before_end_of_pass():
    # Sprint 49 : best visible pendant que la passe tourne ; une tête périmée n'écrit rien ailleurs.
    release, stale_written = threading.Event(), threading.Event()
    head = {"best": {"uci": "e2e4", "san": "e4", "pv_san": ["e4"]}, "forced": None}

    def fake_pass(proxy, fen, elo, models_dir):
        if fen == _AFTER_E4:
            threading.Event().wait()
        proxy.on_head(head)
        release.wait(5)
        proxy.on_head({"best": {"uci": "stale", "san": "?", "pv_san": []}, "forced": None})
        stale_written.set()
        return {"result": "none", "explosive": None, **head}

    worker = BoardWorker(lambda: object(), "", run_pass=fake_pass)
    threading.Thread(target=worker.run, daemon=True).start()
    worker.submit(chess.STARTING_FEN, 1200, 1800)
    state = _wait_state(worker, lambda s: s["best"] is not None)
    assert state["result"] == "pending" and state["running"]
    assert state["best"]["uci"] == "e2e4"

    # Nouvelle position pendant que l'ancienne passe tourne : son état reste vierge.
    worker.submit(_AFTER_E4, 1200, 1800, "black")
    release.set()
    assert stale_written.wait(5)
    assert worker.state()["best"] is None


def test_return_to_finished_position_keeps_result():
    # Sprint 49 : retour sur une position terminée : même résultat, aucune passe relancée.
    calls = []

    def fake_pass(proxy, fen, elo, models_dir):
        calls.append(fen)
        return {"result": "none", "explosive": None, "best": {"uci": fen.split()[1], "n": len(calls)}}

    worker = BoardWorker(lambda: object(), "", run_pass=fake_pass)
    threading.Thread(target=worker.run, daemon=True).start()
    first_id = worker.submit(chess.STARTING_FEN, 1200, 1800)
    final = _wait_state(worker, lambda s: s["id"] == first_id and not s["running"])
    other_id = worker.submit(_AFTER_E4, 1200, 1800, "black")
    _wait_state(worker, lambda s: s["id"] == other_id and not s["running"])
    count = len(calls)

    worker.submit(chess.STARTING_FEN, 1200, 1800)
    # L'état reprend le résultat dès le retour, sans passer par « pending ».
    state = worker.state()
    assert state["best"] == final["best"] and state["result"] == "none"
    assert state["pass"] == 3 and not state["running"]
    time.sleep(0.05)
    assert len(calls) == count


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
        # Sprint 37, tronçon 02 : cases des calques piège (cyan) et stratégie (blanc).
        assert "show-trap" in page and "show-strategy" in page
        assert 'strategy: { key: "s", color: "#ffe100"' in page and "#ff5fb0\"></span>" not in page
        # Sprint 50 : flèches d'erreur cochables, bouton + de la barre mobile. Sprint 68 (run
        # live) : toutes les cases décochées par défaut, sauf Anticipation.
        assert 'id="show-errors" type="checkbox">' in page
        assert 'id="show-best" type="checkbox">' in page
        assert page.index('id="menu"') < page.index('id="new-bar"') < page.index('id="flip-bar"')
        assert "function pointColor(" in page and "<circle cx=" in page
        assert "paintMove(span, color)" in page
        # Sprint 38, tronçon 02 : zone PGN et courbe d'évaluation.
        assert 'id="pgn"' in page and 'id="graph"' in page
        # Sprint 39, tronçon 03 : export, envoi à ARIA, « Je joue » ; tronçon 07 : plus de pseudo injecté.
        assert 'id="export"' in page and 'id="send"' in page and 'id="playing"' in page
        assert 'const NICO_NAME = "Nico"' in page and "USERNAME" not in page
        # Sprint 39, tronçon 05 : champs des noms des joueurs.
        assert 'id="name-white"' in page and 'id="name-black"' in page
        # Tronçon 08 : liste des coups sous la courbe.
        assert 'id="moves"' in page and "goToLine(i + 1)" in page
        # Tronçon 10 : ligne de précision sous le coup joué.
        assert 'id="accuracy"' in page
        # Sprint 41, tronçon 01 : page mobile (viewport, Mini App, barre d'éval, onglets, barre du bas).
        assert 'name="viewport"' in page and "telegram-web-app.js" in page
        assert 'id="evalbar"' in page and 'id="tabs"' in page and 'id="bottombar"' in page
        # Sprint 49, tronçon 02 : flèche bleue sans rationnement.
        assert "blueAllowed" not in page
        # Sprint 68, tronçon 05 : case Anticipation, camp du bas envoyé à /position.
        assert 'id="show-anticipation" type="checkbox" checked' in page
        # Sprint 68 (run live) : sur PC, l'analyse est à droite de l'échiquier.
        assert "#analysis { grid-column: 2; grid-row: 1;" in page
        # Encart conservé tant que la partie suit sa ligne, prochain coup fléché.
        assert "function followedLines()" in page and "const next = nextLineMove();" in page
        # Téléphone : défilement porté par body (Mini App Telegram).
        assert "html { height: 100%; overflow: hidden; }" in page
        # Téléphone : onglets sous l'échiquier, courbe ouverte par défaut.
        assert "#tabs { order: 3;" in page and "showTab($(\"tabs\").querySelector('[data-panel=\"graph\"]'))" in page
        assert "bottom: ground.state.orientation" in page
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
            "wins": [60, 45, 70], "mates": [3, None, -1], "best": ["Qh5", "Nf6", None], "history": []}
    finally:
        server.shutdown()
        server.server_close()


def test_game_history_rank_and_opening_performance(monkeypatch):
    # Sprint 52, tronçon 03 : PGN aux en-têtes d'un pseudo de Nico (noirs), fiches lues
    # par un load_games factice → rang de précision et performance dans l'ouverture.
    from types import SimpleNamespace

    import interfaces.board_interface as board_interface

    plies = [SimpleNamespace(color="white", win_before=50, win_after=50, eval_before_cp=0,
                             eval_after_cp=0, best_san="d4", quality="best", loss=0),
             SimpleNamespace(color="black", win_before=50, win_after=50, eval_before_cp=0,
                             eval_after_cp=0, best_san="f5", quality="best", loss=0)]
    monkeypatch.setattr(board_interface, "analyze_game", lambda game, color, path: plies)
    dutch = {"opening": "Dutch-Defense", "opening_group": "Dutch Defense", "nico_color": "black"}
    games = [{**dutch, "outcome": "win", "elo_opponent": 1400, "accuracy": 99.5, "date": "2026.11.01"},
             {**dutch, "outcome": "loss", "elo_opponent": 1400, "accuracy": 70, "date": "2026.11.02"},
             {"opening": "Dutch-Defense", "opening_group": "Dutch Defense", "nico_color": "white",
              "outcome": "win", "elo_opponent": 1000, "accuracy": 80}]
    server = make_server(0, BoardWorker(lambda: object(), ""), load_games=lambda: games)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    pgn = '[White "Bob"]\n[Black "La_Bagouze"]\n\n1. d4 f5'
    try:
        assert _request(base, "/game", {"pgn": pgn, "playing": ""})["history"] == [
            "Précision 100 % : ta meilleure partie sur 3",
            "Dutch Defense (noirs) : performance 1400 [2 parties]"]
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


def test_line_accuracy_per_move_and_per_side():
    # Sprint 39, tronçon 10 : meilleur coup → 100, perte → < 100, camp sans coup → None.
    from interfaces.board_interface import line_accuracy

    result = line_accuracy([50, 50, 80], [True, False], "white")
    assert result["moves"][0] == 100 and result["moves"][1] < 100
    assert result["white"] == [100, 100] and result["black"][0] is None
    assert result["black"][1] == result["moves"][1]


def test_accuracy_route_serves_line_accuracy():
    # Sprint 39, tronçon 10 : /accuracy calcule sans Stockfish, premier coup noir.
    server = make_server(0, BoardWorker(lambda: object(), ""))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        result = _request(base, "/accuracy", {"wins": [50, 50], "best": [True], "first": "black"})
        assert result == {"moves": [100.0], "white": [None], "black": [100.0]}
    finally:
        server.shutdown()
        server.server_close()


def test_index_accepts_telegram_start_param(monkeypatch):
    # Sprint 65, tronçon 01 : Telegram ouvre la Mini App avec des paramètres d'URL.
    monkeypatch.setattr("interfaces.board_interface._load_maia_in_background", lambda: None)
    server = make_server(0, BoardWorker(lambda: object(), ""))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/?tgWebAppStartParam=abc"
        with urllib.request.urlopen(url) as response:
            assert response.status == 200 and "openStored(storedId)" in response.read().decode()
    finally:
        server.shutdown()
        server.server_close()


def test_stored_serves_fiche_without_analysis(monkeypatch):
    # Sprint 65, tronçon 01 (62-7) : partie et courbe lues dans la fiche, aucun moteur.
    import chess.pgn
    import io

    import interfaces.board_interface as board_interface

    def no_analysis(*args):
        raise AssertionError("analyze_game appelé")

    monkeypatch.setattr(board_interface, "analyze_game", no_analysis)
    plies = [
        {"color": "white", "uci": "e2e4", "win_before": 50, "win_after": 52, "loss": 0,
         "quality": "best", "best_san": "e4"},
        {"color": "black", "uci": "e7e5", "win_before": 48, "win_after": 40, "loss": 8,
         "quality": "inaccuracy", "best_san": "c5"},
        {"color": "white", "uci": "g1f3", "win_before": 60, "win_after": 58, "loss": 2,
         "quality": "good", "best_san": "Nf3"},
    ]
    fiche = {"id": "chess_game_0123456789abcdef", "plies_json": json.dumps(plies),
             "nico_color": "black", "opponent": "Bob", "elo_nico": 1500, "elo_opponent": 1450,
             "date": "2026.11.20", "result": "0-1", "time_control": "600"}
    server = make_server(0, BoardWorker(lambda: object(), ""), load_games=lambda: [fiche])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        data = _request(base, "/stored", {"id": "0123456789abcdef"})
        game = chess.pgn.read_game(io.StringIO(data["pgn"]))
        assert [m.uci() for m in game.mainline_moves()] == ["e2e4", "e7e5", "g1f3"]
        assert game.headers["White"] == "Bob" and game.headers["Black"] == "Nico"
        assert game.headers["BlackElo"] == "1500" and game.headers["TimeControl"] == "600"
        # Coup noir : 100 − win_before ramène au point de vue des blancs.
        assert data["wins"] == [50, 52, 60, 58]
        assert data["best"] == ["e4", "c5", "Nf3", None]
        assert data["mates"] == [None] * 4
        assert data["playing"] == "black"
        assert data["history"][0].startswith("Précision")
        # Sprint 66 : fiche d'avant les miniatures, liste vide.
        assert data["minis"] == []

        with pytest.raises(urllib.error.HTTPError) as missing:
            _request(base, "/stored", {"id": "ffffffffffffffff"})
        assert missing.value.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_stored_game_serves_minis():
    # Sprint 66, tronçon 01 : miniatures de la fiche renvoyées telles quelles à la page.
    from interfaces.board_interface import stored_game

    plies = [{"color": "white", "uci": "e2e4", "win_before": 50, "win_after": 52, "loss": 0,
              "quality": "best", "best_san": "e4"}]
    minis = [{"ply": 0, "kind": "a", "best": "e4", "also": [], "caption": "Position 1",
              "lines": [{"label": "Meilleur coup", "sans": ["e4", "e5"]}]}]
    fiche = {"id": "chess_game_x", "plies_json": json.dumps(plies), "nico_color": "white",
             "minis_json": json.dumps(minis)}
    assert stored_game(fiche, [])["minis"] == minis


def test_opponent_turn_runs_anticipation(monkeypatch, caplog):
    # Sprint 68, tronçon 04 : trait au camp du haut → anticipation, Elo Maia du camp au trait.
    import logging

    calls = []

    def no_pass(*args):
        raise AssertionError("run_pass appelée")

    def fake_anticipation(proxy, fen, elo, models_dir):
        calls.append(elo)
        return {"result": "anticipation", "anticipated": [{"uci": "e7e5"}], "explosive": None}

    worker = BoardWorker(lambda: object(), "", run_pass=no_pass, run_anticipation=fake_anticipation)
    threading.Thread(target=worker.run, daemon=True).start()
    with caplog.at_level(logging.INFO, logger="interfaces.board_interface"):
        position_id = worker.submit(_AFTER_E4, 1200, 1800, "white")
        state = _wait_state(worker, lambda s: s["id"] == position_id and not s["running"])
    assert state["result"] == "anticipation" and state["anticipated"] == [{"uci": "e7e5"}]
    assert set(calls) == {1800}
    assert "result=anticipation" in caplog.text


def test_game_hash_matches_chess_router():
    # Sprint 68 : formule dupliquée, même hash que chess_router._game_hash.
    from execution.routers.chess_router import _game_hash as router_hash
    from interfaces.board_interface import _game_hash

    ucis = ["e2e4", "e7e5", "g1f3"]
    assert _game_hash(ucis) == router_hash(ucis)


def test_game_with_known_hash_serves_stored(monkeypatch):
    # Sprint 68, tronçon 04 : PGN collé déjà en fiche → réponse de /stored, pas d'analyse.
    import interfaces.board_interface as board_interface

    def no_analysis(*args):
        raise AssertionError("analyze_game appelé")

    monkeypatch.setattr(board_interface, "analyze_game", no_analysis)
    plies = [{"color": "white", "uci": "e2e4", "win_before": 50, "win_after": 52, "loss": 0,
              "quality": "best", "best_san": "e4"},
             {"color": "black", "uci": "e7e5", "win_before": 48, "win_after": 47, "loss": 1,
              "quality": "good", "best_san": "e5"}]
    fiche = {"id": "chess_game_" + board_interface._game_hash(["e2e4", "e7e5"]),
             "plies_json": json.dumps(plies), "nico_color": "white", "opponent": "Bob",
             "minis_json": json.dumps([{"ply": 1}])}
    server = make_server(0, BoardWorker(lambda: object(), ""), load_games=lambda: [fiche])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        data = _request(base, "/game", {"pgn": "1. e4 e5"})
        assert data["playing"] == "white" and data["minis"] == [{"ply": 1}]
        assert data["wins"] == [50, 52, 53]
    finally:
        server.shutdown()
        server.server_close()
