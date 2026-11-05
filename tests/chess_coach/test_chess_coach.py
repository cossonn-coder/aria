# tests/chess_coach/test_chess_coach.py
#
# Cas nominaux du paquet chess_coach (sprint 26, tronçon 01).

import math
from pathlib import Path

import chess
import pytest
from PIL import Image

from chess_coach.analysis import (CriticalPosition, PlyAnalysis, analyze, detect_color, first_shown_move,
                                  parse_pgn, select_critical)
from chess_coach.analysis import split_pgn
from chess_coach.analysis import clear_advantage
from chess_coach.explosive import ExplosiveMove, _accepted_deficit, _admissible, _expectation, _line_sacrifice
from chess_coach.render import (ARROW_HEAD, CURVE_LINE, CURVE_MARGIN, CURVE_SIZE, SIZE, _square_center, error_arrow,
                                render_curve, render_position)

STOCKFISH = "/usr/games/stockfish"

SCHOLAR_PGN = """je joue les noirs
[White "Ami"]
[Black "staroflexeur"]
1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


def test_detect_color():
    # Nico reconnu par son nom ou un pseudo (sprint 46), insensible à la casse.
    assert detect_color({"White": "Ami", "Black": "Nico"}, "") == ("black", "header")
    assert detect_color({"White": "Ami", "Black": "Moi"}, "je joue les noirs") == ("black", "message")
    assert detect_color({"White": "Ami", "Black": "staroflexeur"}, "") == ("black", "header")
    assert detect_color({"White": "Ami", "Black": "la_bagouze"}, "") == ("black", "header")
    assert detect_color({"White": "TardoScoped", "Black": "Ami"}, "") == ("white", "header")
    assert detect_color({"White": "Ami", "Black": "Inconnu"}, "") == ("white", "default")


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_analyze_detects_blunder():
    game = analyze(SCHOLAR_PGN, SCHOLAR_PGN, STOCKFISH)
    assert game.nico_color == "black"
    blunder = game.plies[5]
    assert blunder.san == "Nf6"
    assert blunder.quality == "blunder"


@pytest.mark.parametrize("loss, sacrifice, gain, retained", [
    (4.0, 3, 0.0, True),    # ancienne règle sprint 28 : sacrifice dans la fenêtre 5
    (12.0, 0, 6.0, True),   # règle Maia : gain d'espérance ≥ 5, fenêtre 15
    (4.0, 0, 3.0, False),   # ni sacrifice, ni piège, gain < 5
])
def test_explosive_admissible_hybrid(loss, sacrifice, gain, retained):
    # Sprint 29, tronçon 07 : ancienne règle OU gain Maia ≥ 5.
    candidate = ExplosiveMove(
        san="Nd5", uci="c3d5", loss=loss, win_after=43.0, pv_san=[], sacrifice=sacrifice, forcing=[],
        trap_reply_san="exd5", score=0.0, evidence="material", expected=50.0 + gain,
    )
    assert _admissible(candidate, 50.0) is retained


def test_accepted_deficit_gambit():
    # Sprint 36 : Göring 4.c3 dxc3 5.Nxc3 = offre acceptée (1 pion) ; 4.Be2 Nf6 sans prise → 0.
    board = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "d4", "exd4"]:
        board.push_san(san)
    goring = [chess.Move.from_uci(u) for u in ("c2c3", "d4c3", "b1c3")]
    quiet = [chess.Move.from_uci(u) for u in ("f1e2", "g8f6", "f3d4")]
    assert _accepted_deficit(board, goring, 0) == 1
    assert _accepted_deficit(board, quiet, 0) == 0


@pytest.mark.parametrize("forcing, loss, retained", [
    (["check", "capture"], 0.0, True),   # sacrifice accepté avec échec, sans avantage clair
    ([], 4.0, False),                    # bruit 3...a6 : ni échec ni avantage clair
])
def test_explosive_admissible_accepted_sacrifice(forcing, loss, retained):
    candidate = ExplosiveMove(
        san="Bxf7+", uci="c4f7", loss=loss, win_after=50.0, pv_san=[], sacrifice=0, forcing=forcing,
        trap_reply_san="Kxf7", score=0.0, evidence=None, expected=50.0, accepted=2,
    )
    assert _admissible(candidate, 50.0) is retained


def test_expectation_renormalized():
    # Probabilités gardées (somme 0,8) renormalisées : (0,6 × 70 + 0,2 × 30) / 0,8 = 60.
    assert _expectation([{"p": 0.6, "win": 70.0}, {"p": 0.2, "win": 30.0}]) == pytest.approx(60.0)


def test_line_sacrifice_waits_end_of_exchange():
    # Tronçon 05 : 1...d6 2.d4 e5 3.dxe5 dxe5 4.Dxd8+ Rxd8 — la dame est reprise, sacrifice 0.
    board = chess.Board()
    board.push_san("e4")
    line = []
    replay = board.copy()
    for san in ["d6", "d4", "e5", "dxe5", "dxe5", "Qxd8+", "Kxd8"]:
        line.append(replay.push_san(san))
    assert _line_sacrifice(board, line) == (0, 7)


def _ply(ply, loss, second_gap=None, move_number=None, fen_before=chess.STARTING_FEN, win_before=50.0, pv_uci=()):
    return PlyAnalysis(
        ply=ply, move_number=move_number or ply // 2 + 1, color="white" if ply % 2 == 0 else "black", san="e4", uci="e2e4",
        fen_before=fen_before, win_before=win_before, win_after=win_before - loss, loss=loss,
        best_san="e4", best_uci="e2e4", pv_san=["e4"], second_gap=second_gap,
        quality="best" if loss == 0 else "inaccuracy", phase="opening", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0, pv_uci=list(pv_uci),
    )


# Cavalier noir égaré en d4 : 1.e3 a6 2.exd4 gagne une pièce (avantage clair en 3 demi-coups).
HANGING_FEN = "r1bqkbnr/pppppppp/8/8/3n4/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
HANGING_PV = ["e2e3", "a7a6", "e3d4"]


def _line(fen, sans):
    board = chess.Board(fen)
    return [board.push_san(san) for san in sans]


def test_clear_advantage_material():
    board = chess.Board(HANGING_FEN)
    n, criterion = clear_advantage(board, _line(HANGING_FEN, ["e3", "a6", "exd4"]), 50.0, False)
    assert n <= 4 and criterion == "material"


def test_clear_advantage_announced_mate_goes_to_mate():
    # Sprint 50 : le critère de développement répondait (2, …) avant 21.Qxd8#.
    fen = "r1b2k1r/4bppp/p1p1p1q1/B1N2n2/4N3/7P/2P2PP1/R2Q1RK1 w - - 9 20"
    line = _line(fen, ["Bd8", "Bxd8", "Qxd8"])
    assert clear_advantage(chess.Board(fen), line, 60.0, True) == (3, "mate")


def test_error_arrow_scale():
    assert error_arrow(10) == (255, 190, 205, 235)
    assert error_arrow(25) == (215, 20, 35, 235)
    assert error_arrow(60) == (0, 0, 0, 235)
    assert error_arrow(3) == error_arrow(10)


def test_clear_advantage_quiet_line_none():
    sans = ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d3", "d6"]
    assert clear_advantage(chess.Board(), _line(chess.STARTING_FEN, sans), 50.0, False) is None


def test_clear_advantage_after_cap_on_quiet_moves_none():
    # L'avance de développement (Nf3 + Nc3) n'arrive qu'au 11e demi-coup, calme.
    sans = ["a3", "a6", "h3", "h6", "b3", "b6", "g3", "g6", "Nf3", "a5", "Nc3"]
    assert clear_advantage(chess.Board(), _line(chess.STARTING_FEN, sans), 50.0, False) is None


def test_parse_pgn_indented_headers():
    # Collage Telegram : lignes 2+ indentées (run live 03, partie Dame précoce).
    game = parse_pgn('[White "Test"]\n  [Black "staroflexeur"]\n  1. e4 e5 2. Nf3 *\n')
    assert game.headers["Black"] == "staroflexeur"


def test_select_critical_errors_fill_budget():
    # 5 erreurs + 1 explosif + 1 coup unique : les 4 plus grosses pertes, en ordre chronologique.
    plies = [_ply(i, 0) for i in range(41)]
    for i, loss in ((22, 12), (24, 30), (26, 15), (28, 25), (30, 20)):
        plies[i] = _ply(i, loss)
    plies[32] = _ply(32, 2)
    plies[34] = _ply(34, 0, second_gap=40, fen_before=HANGING_FEN, pv_uci=HANGING_PV)
    explosive = [CriticalPosition(kind="d", ply=plies[32], score=50.0)]
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.ply) for c in selected] == [("a", 24), ("a", 26), ("a", 28), ("a", 30)]


def test_select_critical_completes_with_other_kinds():
    # 1 erreur + 1 explosif + 1 tournant + 1 coup unique : les 4, en ordre chronologique.
    plies = [_ply(i, 0) for i in range(41)]
    plies[22] = _ply(22, 0, second_gap=40, fen_before=HANGING_FEN, pv_uci=HANGING_PV)
    plies[25] = _ply(25, 20)
    plies[26] = _ply(26, 3, fen_before=HANGING_FEN, pv_uci=HANGING_PV)
    plies[30] = _ply(30, 15)
    plies[32] = _ply(32, 2)
    explosive = [CriticalPosition(kind="d", ply=plies[32], score=12.0)]
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.ply) for c in selected] == [("c", 22), ("e", 26), ("a", 30), ("d", 32)]


def test_select_critical_skips_taken_position():
    # Une position explosive déjà retenue comme erreur n'occupe pas une 2e place.
    plies = [_ply(i, 0) for i in range(41)]
    plies[22] = _ply(22, 15)
    explosive = [CriticalPosition(kind="d", ply=plies[22], score=12.0)]
    assert [(c.kind, c.ply.ply) for c in select_critical(plies, "white", explosive)] == [("a", 22)]


def test_select_critical_starts_at_move_4():
    # Erreur et explosif du coup 3 écartés, erreur du coup 4 retenue.
    plies = [_ply(i, 0) for i in range(9)]
    plies[4], plies[6] = _ply(4, 30), _ply(6, 30)
    plies[2] = _ply(2, 2, move_number=3)
    explosive = [CriticalPosition(kind="d", ply=plies[2], score=20.0)]
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.move_number) for c in selected] == [("a", 4)]


def _line_plies(sans: str) -> list:
    # Demi-coups d'une suite SAN, pour first_shown_move (seuls ply, couleur, numéro et uci comptent).
    board, plies = chess.Board(), []
    for i, san in enumerate(sans.split()):
        move = board.parse_san(san)
        plies.append(_ply(i, 0))
        plies[-1].uci = move.uci()
        board.push(move)
    return plies


GORING = "e4 e5 Nf3 Nc6 d4 exd4 c3 dxc3 Bc4 Nf6 Nxc3 Bb4 O-O O-O"
ITALIAN = "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O"


def _ucis(sans: str) -> list:
    return [p.uci for p in _line_plies(sans)]


def test_first_shown_move_goring_floor_without_history():
    # Sans historique, le Göring des blancs ne montre rien avant le coup 7.
    assert first_shown_move(_line_plies(GORING), "white") == 7
    assert first_shown_move(_line_plies(GORING), "white", standard_start=False) == 4
    assert first_shown_move(_line_plies(ITALIAN), "white") == 4


def test_first_shown_move_repertoire_until_novelty():
    plies = _line_plies(ITALIAN)
    ucis = [p.uci for p in plies]
    # 2 autres parties partagent les 8 premiers demi-coups : le coup 5 (d3) est le 1er non connu.
    other = _ucis("e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d4 exd4")
    assert first_shown_move(plies, "white", [("white", other)] * 2) == 5
    # Une seule partie précédente, ou l'autre couleur, ne fait pas une habitude.
    assert first_shown_move(plies, "white", [("white", other)]) == 4
    assert first_shown_move(plies, "white", [("black", other)] * 2) == 4
    # Le renvoi de la même partie ne compte pas ; tout connu → aucune miniature.
    assert first_shown_move(plies, "white", [("white", ucis)] * 2) == 4
    assert first_shown_move(plies, "white", [("white", ucis + ["a2a3"])] * 2) == 7


def test_select_critical_respects_first_move():
    # Le budget libéré par les coups d'habitude profite aux positions d'après.
    plies = [_ply(i, 0) for i in range(21)]
    plies[6], plies[12], plies[14] = _ply(6, 30), _ply(12, 30), _ply(14, 30)
    selected = select_critical(plies, "white", first_move=7)
    assert [c.ply.ply for c in selected] == [12, 14]


def test_select_critical_empty_without_fallback():
    # Tronçon 08 : plus de repli « pire coup ».
    plies = [_ply(i, 5 if i % 2 == 0 else 0) for i in range(10)]
    assert select_critical(plies, "white") == []


@pytest.mark.parametrize("win_before_error, retained", [(50.0, True), (5.0, False)])
def test_select_critical_turning_point(win_before_error, retained):
    # Erreur adverse ≥ 15 puis coup de Nico à perte < 10 → tournant, sauf partie déjà décidée.
    plies = [_ply(0, 0), _ply(1, 20, win_before=win_before_error),
             _ply(2, 3, move_number=20, fen_before=HANGING_FEN, pv_uci=HANGING_PV)]
    selected = select_critical(plies, "white")
    assert [(c.kind, c.ply.ply) for c in selected] == ([("e", 2)] if retained else [])
    if retained:
        assert selected[0].evidence == "material" and selected[0].line_san == ["e3", "a6", "exd4"]


def test_select_critical_unique_threshold_15():
    plies = [_ply(0, 0, second_gap=16, move_number=20, fen_before=HANGING_FEN, pv_uci=HANGING_PV)]
    assert [(c.kind, c.ply.ply) for c in select_critical(plies, "white")] == [("c", 0)]


@pytest.mark.parametrize("loss, move_number, retained", [(12, 5, False), (12, 15, True), (25, 5, True)])
def test_select_critical_opening_threshold(loss, move_number, retained):
    # Ouverture assumée : perte ≥ 20 exigée jusqu'au coup 10, ≥ 10 ensuite.
    # Une 2e erreur nette (ply 2) garde la sélection non vide dans les deux cas.
    plies = [_ply(0, loss, move_number=move_number), _ply(1, 0), _ply(2, 30, move_number=20)]
    selected = select_critical(plies, "white")
    assert [(c.kind, c.ply.ply) for c in selected] == ([("a", 0)] if retained else []) + [("a", 2)]


def test_render_position(tmp_path):
    out = tmp_path / "pos.png"
    fen = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
    assert render_position(fen, "black", "g8f6", str(out)) == str(out)
    with Image.open(out) as image:
        assert image.size == (SIZE, SIZE)


def test_render_position_with_explosive_arrow(tmp_path):
    out = tmp_path / "pos.png"
    fen = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
    render_position(fen, "black", "g8f6", str(out), alt_uci="g7g6")
    with Image.open(out) as image:
        assert image.size == (SIZE, SIZE)


def _arrow_pixel(path, square):
    with Image.open(path) as image:
        return image.getpixel(tuple(int(v) for v in _square_center(square, False)))


def _is_blue(pixel):
    return pixel[2] > pixel[0] + 50 and pixel[2] > pixel[1] + 50


def _is_green(pixel):
    return pixel[1] > pixel[0] + 20 and pixel[1] > pixel[2] + 20


def test_render_position_played_arrow(tmp_path):
    # Trajets sur cases vides : e3 pour le coup joué e2e4, d3 pour le meilleur coup d2d4.
    out = tmp_path / "pos.png"
    render_position(chess.STARTING_FEN, "white", "d2d4", str(out), played_uci="e2e4")
    assert _is_blue(_arrow_pixel(out, chess.E3))
    assert _is_green(_arrow_pixel(out, chess.D3))

    # Coup joué = meilleur coup : seule la bleue reste, aucun pixel vert sur l'image.
    render_position(chess.STARTING_FEN, "white", "e2e4", str(out), played_uci="e2e4")
    assert _is_blue(_arrow_pixel(out, chess.E3))
    with Image.open(out) as image:
        assert not any(_is_green(pixel) for pixel in image.get_flattened_data())


def _badge_pixel(path, from_square, to_square):
    """Centre de la pastille : à la base de la pointe de la flèche."""
    x1, y1 = _square_center(from_square, False)
    x2, y2 = _square_center(to_square, False)
    length = math.hypot(x2 - x1, y2 - y1)
    t = ARROW_HEAD / length
    # Décalé de 6 px vers le haut-gauche, hors du chiffre, dans le disque.
    with Image.open(path) as image:
        return image.getpixel((int(x2 - t * (x2 - x1)) - 6, int(y2 - t * (y2 - y1)) - 6))


def test_render_position_best_line_numbered(tmp_path):
    # Variante 1.e4 e5 2.Nf3 : flèches vertes sur e3, e6 ; pastilles au-dessus des pièces.
    out = tmp_path / "pos.png"
    line = ["e2e4", "e7e5", "g1f3"]
    render_position(chess.STARTING_FEN, "white", "e2e4", str(out), best_line_uci=line)
    assert _is_green(_arrow_pixel(out, chess.E3))
    assert _is_green(_arrow_pixel(out, chess.E6))
    assert _is_green(_badge_pixel(out, chess.G1, chess.F3))

    # Coup joué = meilleur coup : la bleue porte le n° 1, les vertes suivent.
    render_position(chess.STARTING_FEN, "white", "e2e4", str(out), played_uci="e2e4", best_line_uci=line)
    assert _is_blue(_arrow_pixel(out, chess.E3))
    assert _is_blue(_badge_pixel(out, chess.E2, chess.E4))
    assert _is_green(_arrow_pixel(out, chess.E6))
    assert _is_green(_badge_pixel(out, chess.E7, chess.E5))


def test_split_pgn_two_games_keeps_preface():
    text = ('je joue les noirs\n[Event "A"]\n[White "X"]\n\n1. e4 e5 *\n\n'
            '[Event "B"]\n  [White "Y"]\n\n  1. d4 d5 *\n')
    games = split_pgn(text)
    assert len(games) == 2
    assert all(g.startswith("je joue les noirs\n\n[Event") for g in games)
    assert [parse_pgn(g).headers["White"] for g in games] == ["X", "Y"]


def test_analysis_engines_use_long_timeout(monkeypatch):
    """Les deux moteurs de l'analyse d'une partie laissent 60 s de marge à Stockfish."""
    import chess.engine
    import chess.pgn

    from chess_coach.analysis import analyze_game
    from chess_coach.explosive import find_explosive

    class Opened(Exception):
        pass

    timeouts = []

    def fake_popen(path, timeout=None):
        timeouts.append(timeout)
        raise Opened

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", fake_popen)
    # Maia est chargé avant le moteur : sans ce bouchon, le test téléchargerait le modèle.
    monkeypatch.setattr("chess_coach.explosive._load", lambda models_dir: None)
    # Ouverture parallèle : chaque appel peut tenter plusieurs moteurs, tous à 60 s.
    with pytest.raises(Opened):
        analyze_game(chess.pgn.Game(), "white", "stockfish")
    assert timeouts and set(timeouts) == {60}
    timeouts.clear()
    with pytest.raises(Opened):
        find_explosive([_ply(0, 0)], "white", "stockfish", 1500, "maia")
    assert timeouts and set(timeouts) == {60}


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_analyze_game_reproducible():
    """Nœuds fixes (sprint 49) : la même partie analysée deux fois donne le même résultat."""
    from chess_coach.analysis import analyze_game

    def measures():
        plies = analyze_game(parse_pgn(SCHOLAR_PGN), "black", STOCKFISH)
        return [(p.best_uci, p.win_before, p.quality) for p in plies]

    assert measures() == measures()


def test_run_on_engines_closes_all_on_failure(monkeypatch):
    """Une exception pendant le travail ne laisse aucun des 8 moteurs ouvert."""
    import chess.engine

    from chess_coach.analysis import run_on_engines

    class FakeEngine:
        closed = False

        def configure(self, options):
            pass

        def close(self):
            self.closed = True

    opened = []

    def fake_popen(path, timeout=None):
        opened.append(FakeEngine())
        return opened[-1]

    def fail(engine, item):
        raise ValueError

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", fake_popen)
    with pytest.raises(ValueError):
        run_on_engines("stockfish", fail, [1, 2])
    assert len(opened) == 8 and all(e.closed for e in opened)


def test_fixed_nodes_engine_converts_time_and_keeps_cap():
    """Le temps demandé devient des nœuds, avec un plafond de temps et un hash vidé."""
    from chess_coach.analysis import FixedNodesEngine

    class Recorder:
        def analyse(self, board, limit, **kwargs):
            self.limit, self.kwargs = limit, kwargs

    recorder = Recorder()
    FixedNodesEngine(recorder).analyse(chess.Board(), chess.engine.Limit(time=0.5), multipv=5)
    assert (recorder.limit.nodes, recorder.limit.time) == (295000, 60)
    assert recorder.kwargs["multipv"] == 5 and "game" in recorder.kwargs


def _analyze_with_errors(monkeypatch, error_count):
    """analyze sur une partie simulée à error_count erreurs ; rend les first_move passés à find_explosive."""
    plies = [_ply(i, 15 if i % 2 == 1 and 23 <= i < 23 + 2 * error_count else 0) for i in range(41)]
    calls = []

    def fake_find(plies, color, path, elo, models_dir, first_move):
        calls.append(first_move)
        return []

    monkeypatch.setattr("chess_coach.analysis.analyze_game", lambda game, color, path: plies)
    monkeypatch.setattr("chess_coach.analysis.assign_motifs", lambda plies, color: None)
    monkeypatch.setattr("chess_coach.explosive.find_explosive", fake_find)
    analyze('[White "Ami"]\n[Black "Nico"]\n1. e4 *\n', "", "stockfish")
    return calls


def test_analyze_skips_explosive_when_errors_fill_budget(monkeypatch):
    assert _analyze_with_errors(monkeypatch, 4) == []
    assert len(_analyze_with_errors(monkeypatch, 3)) == 1


def test_find_explosive_starts_at_first_move(monkeypatch):
    """Aucune recherche avant first_move (#160)."""
    from chess_coach import explosive

    plies = [_ply(2 * i, 0) for i in range(6)]
    searched = []
    monkeypatch.setattr(explosive, "_load", lambda models_dir: None)
    monkeypatch.setattr(explosive, "run_on_engines",
                        lambda path, work, items: searched.extend(p.move_number for p in items) or [None] * len(items))
    explosive.find_explosive(plies, "white", "stockfish", 1500, "maia", first_move=4)
    assert searched == [4, 5, 6]


def test_render_curve(tmp_path):
    """La courbe suit le % de gain : haut au début, bas à la fin."""
    out = tmp_path / "curve.png"
    render_curve([100, 100, 0], [10, 10], str(out))
    image = Image.open(out).convert("RGB")
    assert image.size == CURVE_SIZE
    width, height = CURVE_SIZE
    top, bottom = CURVE_MARGIN // 2, height - CURVE_MARGIN
    assert image.getpixel((CURVE_MARGIN + 10, top)) == CURVE_LINE
    assert image.getpixel((width - CURVE_MARGIN // 2 - 1, bottom)) == CURVE_LINE
    # Un point par position : plus épais que le segment qui le relie (sprint 50).
    assert image.getpixel((CURVE_MARGIN, top + 2)) == CURVE_LINE
