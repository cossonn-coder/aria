# tests/execution/test_chess_router.py
#
# Tests du ChessExecutionRouter (sprint 26, tronçon 02) — analyse et rendu
# monkeypatchés : pas de Stockfish, pas de Pillow.

import hashlib
import json
from unittest.mock import MagicMock

import chess
import pytest

import execution.routers.chess_router as chess_router_mod
from chess_coach.analysis import CriticalPosition, GameAnalysis, PlyAnalysis
from chess_coach.explosive import ExplosiveMove
from chess_coach.player_model import GameDelta, Profile, Rating, Trial
from execution.routers.chess_router import ChessExecutionRouter, _caption, _move_facts, _variant_line


def _ply(ply, move_number, san, best_san, best_uci):
    return PlyAnalysis(
        ply=ply, move_number=move_number, color="black", san=san, uci="a7a6",
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        win_before=50.0, win_after=30.0, loss=20.0, best_san=best_san, best_uci=best_uci,
        pv_san=[best_san, "Nf3"], second_gap=None, quality="mistake",
        phase="middlegame", tags=["check"], clock=None, eval_before_cp=0, eval_after_cp=80,
    )


@pytest.fixture(autouse=True)
def no_opening_detection(monkeypatch):
    # Coups factices (a7a6 répété), non rejouables depuis la position initiale.
    monkeypatch.setattr("chess_coach.summary.detect_opening", lambda ucis: None)


def _season_game(doc_id):
    """Fiche saison 1 minimale (clé difficulty, 20 demi-coups)."""
    plies = [{"color": "black", "move_number": 20, "san": "Nf6", "loss": 0.0, "win_before": 50.0,
              "second_gap": 20.0, "difficulty": 1500.0, "tags": [], "best_san": "Nf6",
              "phase": "middlegame"}]
    return {"id": doc_id, "n_plies": 20, "plies_json": json.dumps(plies), "nico_color": "black",
            "elo_nico": 1307, "elo_opponent": 1300, "outcome": "win", "opening": "Scotch-Game"}


def test_execute_returns_text_and_images_and_delegates_reasoning(monkeypatch, tmp_path):
    plies = [_ply(1, 17, "Ng4+", "d6", "d7d6"), _ply(3, 19, "a6", "Nf6", "g8f6")]
    analysis = GameAnalysis(
        headers={"White": "Ami", "Black": "staroflexeur", "BlackElo": "1307"},
        nico_color="black", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="a", ply=p, score=p.loss) for p in plies],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    write_game = MagicMock()
    monkeypatch.setattr(chess_router_mod, "write_chess_game", write_game)
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    # Deux fiches saison 1 : une ancienne, puis la partie courante (même doc_id).
    current = "chess_game_" + hashlib.sha256(b"a7a6a7a6").hexdigest()[:16]
    bridge = MagicMock()
    bridge.load_chess_games.return_value = [_season_game("chess_game_old"), _season_game(current)]

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "[White \"Ami\"] 1. e4", "metadata": {"chat_id": 42}}
    )

    delegated = llm_exec.execute.call_args.args[0]
    # Ligne déterministe (tronçon 08) entre le texte LLM et le bloc Progression.
    assert result["text"].startswith(
        "explication\n\n🎯 Précision 41 % · pire coup 17...Ng4+ (50 % → 30 %)\n\n"
        "🎮 Progression — saison 1, partie 2")
    assert "précision Nico : 41 %" in delegated["content"]
    assert "Historique (données) : 2 parties saison 1, classement global" in delegated["content"]
    assert len(result["images"]) == 2
    assert result["images"][0]["caption"].startswith("Position 1 — coup 17 (noirs) : joué 17...Ng4+")
    assert delegated["op_type"] == "reasoning"
    assert "skip_intent" not in delegated["metadata"]
    assert "Position 1" in delegated["content"]
    assert delegated["metadata"]["forced_intent_name"] == "jeux echecs"
    assert delegated["content"].startswith("Partie contre Ami\n[Analyse Stockfish")
    assert "1re ligne exacte « Partie contre Ami »" in delegated["content"]
    assert "Niveau" in delegated["content"]
    # Sprint 46 : l'entrée est un plan, nombre exact d'entrées, sans historique.
    assert "commence par « Plan : »" in delegated["content"]
    assert "  structure : " in delegated["content"]
    assert "1 à 3 phrases" in delegated["content"]
    assert "de Position 1 à Position 2, aucune omise" in delegated["content"]
    assert delegated["metadata"]["skip_history"] is True
    assert result["images"][0]["caption"].endswith("\nVariante : 17...d6 ; 18.Nf3.")
    assert "axes de travail" not in delegated["content"]
    # Faits calculés depuis le FEN (après 1.e4) : matériel égal, rien d'attaqué.
    assert "  matériel : égal\n  attaquées : aucune" in delegated["content"]
    # Tronçon 13 : faits coup par coup du meilleur coup et état de la position.
    assert "  faits : 17...d6 18.Nf3" in delegated["content"]
    assert "  évaluation : équilibre (50 %)" in delegated["content"]
    assert "matériel / attaquées / structure / faits. Ne recopie ni ne paraphrase" in delegated["content"]
    assert "idées classiques de cette ouverture" not in delegated["content"]
    write_game.assert_called_once()
    assert write_game.call_args.kwargs["extra"]["nico_color"] == "black"


def test_explosive_position_caption_arrow_and_enriched(monkeypatch, tmp_path):
    # Sorte d construite à la main : 4...Nf6 joué, 4...Qh4!? explosif.
    ply = _ply(7, 4, "Nf6", "Nc6", "b8c6")
    # Position où 4...Qh4 et 5.Nxh4 sont légaux (les faits rejouent la ligne).
    ply.fen_before = "rnbqkbnr/pppp1ppp/4p3/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    ply.pv_san = ["Nc6", "Bb5"]
    explosive = ExplosiveMove(
        san="Qh4", uci="d8h4", loss=4.0, win_after=46.0, pv_san=["Qh4", "Nxh4"],
        sacrifice=9, forcing=["threat"], trap_reply_san="Nxh4",
        score=12.0, offered=9, trap_line_san=["Nxh4", "e5"],
        replies=[{"san": "Nxh4", "p": 0.62, "line_san": ["Nxh4"], "win": 62.0},
                 {"san": "d3", "p": 0.2, "line_san": ["d3", "Nc6"], "win": 47.0}],
        trap_end_fen="rnb1kbnr/pppp1ppp/8/4p3/4P2N/8/PPPP1PPP/RNBQKB1R w KQkq - 0 6",
        trap_end_win=75.0, evidence="development", expected=58.0, best_expected=46.0,
    )
    analysis = GameAnalysis(
        headers={"Opening": "Scotch Gambit"}, nico_color="black", color_source="header", plies=[ply],
        critical=[CriticalPosition(kind="d", ply=ply, score=12.0, explosive=explosive)],
    )
    render = MagicMock(side_effect=lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", render)
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}}
    )

    content = llm_exec.execute.call_args.args[0]["content"]
    assert result["images"][0]["caption"] == (
        "Position 1 — coup 4 (noirs) : joué 4...Nf6, explosif 4...Qh4!? (meilleur 4...Nc6)\n"
        "Variante : 4...Qh4 attaque pion e4 ; 5.Nxh4 prend Qh4 ; 5...e5.\n"
        "Variante du meilleur coup : 4...Nc6 ; 5.Bb5."
    )
    assert render.call_args.kwargs["alt_uci"] == "d8h4"
    assert render.call_args.kwargs["played_uci"] == ply.uci
    assert "Position 1 (occasion explosive)" in content
    assert "offre la dame (9) ; forçant : menace" in content
    assert "réponse humaine la plus probable : Nxh4 (62 %)" in content
    assert "espérance face à un humain : Nico 58 % (meilleur coup : 46 %)" in content
    assert "variante : 5.Nxh4 e5 (avance de développement)" in content
    assert "faits : 5.Nxh4 (prend Qh4) 5...e5" in content
    assert "fin de variante : matériel : Nico −9, % de gain Nico 75 %" in content
    assert "coût" not in content.split("[Consigne")[0]
    assert "si Nxh4 (62 %) : 5.Nxh4, 62 % pour Nico" in content
    assert "si d3 (20 %) : 5.d3 Nc6, 47 % pour Nico" in content
    assert ("pièces : blancs Ke1 Qd1 Ra1 Rh1 Bc1 Bf1 Nb1 Nf3, pions a2 b2 c2 d2 f2 g2 h2 e4 ; "
            "noirs Ke8 Qd8") in content
    assert "Notation anglaise : N, B, R, Q, K" in content
    assert "ouverture jouée : Scotch Gambit." in content
    assert "volatilité" not in content
    assert "ne le présente jamais comme le meilleur coup" in content


def test_explosive_without_clear_advantage_renders(monkeypatch, tmp_path):
    # Sprint 36 : explosif admis par sacrifice accepté avec échec, sans avantage clair.
    ply = _ply(7, 4, "Nf6", "Nc6", "b8c6")
    ply.fen_before = "rnbqkbnr/pppp1ppp/4p3/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    ply.pv_san = ["Nc6", "Bb5"]
    explosive = ExplosiveMove(
        san="Qh4", uci="d8h4", loss=4.0, win_after=46.0, pv_san=["Qh4", "Nxh4"],
        sacrifice=0, forcing=["threat"], trap_reply_san="Nxh4", score=0.0, accepted=2,
        replies=[{"san": "Nxh4", "p": 0.62, "line_san": ["Nxh4"], "win": 62.0}],
        trap_end_win=50.0, expected=46.0, best_expected=46.0,
    )
    analysis = GameAnalysis(
        headers={}, nico_color="black", color_source="header", plies=[ply],
        critical=[CriticalPosition(kind="d", ply=ply, score=0.0, explosive=explosive)],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", MagicMock(side_effect=lambda *a, **k: a[3]))
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}}
    )

    content = llm_exec.execute.call_args.args[0]["content"]
    assert "sacrifie 2 pion(s) sur la ligne" in content
    assert "  variante :" not in content.split("[Consigne")[0]


def test_turning_point_caption_and_enriched(monkeypatch, tmp_path):
    # Sorte e : 7...h6? (erreur adverse) puni par 8.e5 (Nico blancs).
    error = PlyAnalysis(
        ply=0, move_number=7, color="black", san="h6", uci="h7h6",
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        win_before=50.0, win_after=32.0, loss=18.0, best_san="Be7", best_uci="f8e7",
        pv_san=["Be7"], second_gap=None, quality="mistake", phase="opening", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0,
    )
    punish = PlyAnalysis(
        ply=1, move_number=8, color="white", san="e5", uci="e4e5",
        fen_before="rnbqkbnr/ppppppp1/7p/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        win_before=68.0, win_after=68.0, loss=0.0, best_san="e5", best_uci="e4e5",
        pv_san=["e5", "d5"], second_gap=None, quality="best", phase="opening", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0,
    )
    analysis = GameAnalysis(
        headers={}, nico_color="white", color_source="header", plies=[error, punish],
        critical=[CriticalPosition(kind="e", ply=punish, score=18.0,
                                   evidence="material", line_san=["e5", "d5", "exd6"])],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "2.Dh5 Cxe5 Tae1 Fe7, Cela"}
    bridge = MagicMock()
    bridge.load_chess_games.side_effect = RuntimeError("palace indisponible")

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}}
    )

    content = llm_exec.execute.call_args.args[0]["content"]
    assert result["images"][0]["caption"] == (
        "Position 1 — coup 8 (blancs) : tournant après 7...h6?, joué 8.e5 (meilleur 8.e5)\n"
        "Variante : 8.e5 ; 8...d5 ; 9.exd6 prend pion d5."
    )
    assert "Position 1 (tournant (erreur adverse punie))" in content
    assert "erreur adverse 7...h6 : perte 18 pts (meilleur 7...Be7)" in content
    assert "variante : 8.e5 d5 9.exd6 (gain matériel)" in content
    assert "montre la variante qui la punit" in content
    # Conversion de la notation française résiduelle en sortie ; bridge en échec → pas de bloc.
    assert result["text"].startswith("2.Qh5 Nxe5 Rae1 Be7, Cela\n\n🎯 Précision")
    assert "Historique (données) :" not in content


def test_progression_block_level_up_and_new_badge():
    before = Profile(n_games=3, ratings={k: Rating(1290.0) for k in chess_router_mod.LABELS},
                     badges={"Série": "x"})
    after = Profile(
        n_games=4, ratings={**{k: Rating(1290.0) for k in chess_router_mod.LABELS},
                            "punish": Rating(1315.0)},
        last_game={**{k: GameDelta() for k in chess_router_mod.LABELS},
                   "punish": GameDelta(25.0, Trial("17.Qb3", 1950.0, 1.0, 25.0))},
        badges={"Série": "x", "Tueur de géant": "y"},
    )
    summary = {"elo_opponent": 1452, "elo_nico": 1345, "opening": "", "nico_color": "white"}

    block = chess_router_mod._progression_block(before, after, summary)

    assert block.startswith("🎮 Progression — saison 1, partie 4\nGlobal 1290 (+0) · niveau 12")
    assert ("⬆️ Punir les erreurs 1315 (+25) · niveau 13 atteint : "
            "17.Qb3 trouvé (difficulté ≈1950)") in block
    assert "🏆 Badge débloqué : Tueur de géant — victoire contre un adversaire à 1452 (+107)" in block
    assert "Série" not in block


def test_progression_block_phases_fixed_line_not_merged():
    keys = chess_router_mod.LABELS
    before = Profile(n_games=3, ratings={k: Rating(1400.0) for k in keys})
    after = Profile(
        n_games=4, ratings={**{k: Rating(1400.0) for k in keys}, "opening": Rating(1652.0),
                            "middlegame": Rating(1412.0), "endgame": Rating(1380.0)},
        last_game={**{k: GameDelta() for k in keys},
                   "opening": GameDelta(5.0, Trial("coups 1-10", 1400.0, 1.0, 5.0)),
                   "middlegame": GameDelta(-3.0, Trial("19.Bg5", 1240.0, 0.0, -3.0))},
    )

    block = chess_router_mod._progression_block(before, after, {"opening": "", "nico_color": "white"})

    lines = block.splitlines()
    assert lines[2] == "Ouverture 1652 (+5) · Milieu de jeu 1412 (−3) · Finale 1380 (+0)"
    assert "19.Bg5" not in block and "coups 1-10" not in block
    assert sum("Ouverture" in line for line in lines) == 1


def test_game_written_in_opening_room(monkeypatch, tmp_path):
    p = _ply(1, 17, "Ng4+", "d6", "d7d6")
    analysis = GameAnalysis(headers={"White": "Ami", "Black": "staroflexeur"}, nico_color="black",
                            color_source="header", plies=[p],
                            critical=[CriticalPosition(kind="a", ply=p, score=p.loss)])
    monkeypatch.setattr("chess_coach.summary.detect_opening",
                        lambda ucis: ("C44", "Scotch Game: Göring Gambit"))
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    write_game = MagicMock()
    monkeypatch.setattr(chess_router_mod, "write_chess_game", write_game)
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {"chat_id": 42}}
    )

    assert write_game.call_args.kwargs["room"] == "chess_goring-gambit"
    assert write_game.call_args.kwargs["extra"]["opening_group"] == "Göring Gambit"


def test_progression_block_merges_themes_on_same_move():
    keys = chess_router_mod.LABELS
    before = Profile(n_games=3, ratings={k: Rating(1335.0) for k in keys})
    after = Profile(
        n_games=4, ratings={**{k: Rating(1335.0) for k in keys},
                            "hanging": Rating(1325.0), "convert": Rating(1348.0)},
        last_game={**{k: GameDelta() for k in keys},
                   "hanging": GameDelta(-10.0, Trial("19.Bg5", 1240.0, 0.0, -10.0)),
                   "convert": GameDelta(-11.0, Trial("19.Bg5", 1240.0, 0.0, -11.0))},
    )
    summary = {"opening": "", "nico_color": "white"}

    block = chess_router_mod._progression_block(before, after, summary)

    assert ("\nGain de matériel 1325 (−10) · Convertir l'avantage 1348 (−11) : "
            "19.Bg5 raté (difficulté ≈1240)") in block
    assert block.count("19.Bg5") == 1


def test_progression_block_mate_with_name():
    keys = chess_router_mod.LABELS
    before = Profile(n_games=3, ratings={k: Rating(1335.0) for k in keys})
    after = Profile(
        n_games=4, ratings={**{k: Rating(1335.0) for k in keys}, "mates": Rating(1355.0)},
        last_game={**{k: GameDelta() for k in keys},
                   "mates": GameDelta(20.0, Trial("31.Qh7#", 1650.0, 1.0, 20.0, "mat d'Anastasia"))},
    )

    block = chess_router_mod._progression_block(before, after, {"opening": "", "nico_color": "white"})

    assert "\nMats 1355 (+20) : 31.Qh7# trouvé (difficulté ≈1650), mat d'Anastasia" in block


def test_normalize_images_result_is_images_text():
    from core.kernel import AriaKernel
    # _normalize n'utilise pas l'état du kernel : pas de construction complète.
    kernel = AriaKernel.__new__(AriaKernel)
    images = [{"path": "/tmp/p1.png", "caption": "Position 1"}]

    out = kernel._normalize({"status": "success", "data": {"text": "t", "images": images}})

    assert out == {"type": "images_text", "images": images, "text": "t"}


def _run_with_llm_text(monkeypatch, tmp_path, llm_text):
    """Deux positions critiques, LLM factice rendant llm_text ; deux fiches → bloc Progression."""
    plies = [_ply(1, 17, "Ng4+", "d6", "d7d6"), _ply(3, 19, "a6", "Nf6", "g8f6")]
    analysis = GameAnalysis(
        headers={"White": "Ami", "Black": "staroflexeur", "BlackElo": "1307"},
        nico_color="black", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="a", ply=p, score=p.loss) for p in plies],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": llm_text}
    bridge = MagicMock()
    current = "chess_game_" + hashlib.sha256(b"a7a6a7a6").hexdigest()[:16]
    bridge.load_chess_games.return_value = [_season_game("chess_game_old"), _season_game(current)]
    return ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "[White \"Ami\"] 1. e4", "metadata": {}}
    )


def test_entries_move_to_captions(monkeypatch, tmp_path):
    llm = ("Partie contre Ami\n\nPosition 1 — Le fou devait parer l'échec.\n\n"
           "Position 2 — Nf6 développait avec tempo.\n\nNiveau : solide. Peu d'erreurs.")
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    caps = [img["caption"] for img in result["images"]]
    assert caps[0].startswith("Position 1 — coup 17 (noirs) : joué 17...Ng4+")
    assert caps[0].endswith("\nLe fou devait parer l'échec.")
    assert caps[1].endswith("\nNf6 développait avec tempo.")
    assert "Position 1 —" not in result["text"] and "Position 2 —" not in result["text"]
    assert result["text"].startswith("Partie contre Ami\n\nNiveau : solide. Peu d'erreurs.\n\n🎯 ")
    assert "\n\n🎮 Progression" in result["text"]


def test_missing_entry_keeps_current_behavior(monkeypatch, tmp_path):
    llm = "Partie contre Ami\n\nPosition 1 — Le fou devait parer l'échec.\n\nNiveau : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    assert result["text"].startswith(llm + "\n\n🎯 ")
    # Repli : légende = ligne factuelle + ligne « Variante : » du code, rien d'autre.
    assert result["images"][0]["caption"].count("\n") == 1
    assert result["images"][1]["caption"].endswith("\nVariante : 19...Nf6 attaque pion e4 ; 20.Nf3.")


def test_long_entry_cut_at_last_sentence(monkeypatch, tmp_path):
    long_entry = "Une phrase d'explication assez longue pour remplir. " * 30  # ~1500 car.
    llm = f"Partie contre Ami\nPosition 1 — {long_entry}\nPosition 2 — Court.\nNiveau : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    caption = result["images"][0]["caption"]
    assert len(caption) <= 1024
    assert caption.endswith("remplir. …")


def test_move_facts_capture_and_numbering():
    text = _move_facts(chess.STARTING_FEN, ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Bxc6"], 1, "white")

    assert text.startswith("1.e4")
    assert "4.Bxc6 (prend Nc6)" in text


def test_variant_line_capture_and_check():
    """Tronçon 15 : ligne « Variante : » racontée par le code (sorte a, pv_san)."""
    ply = _ply(7, 4, "Bg4", "Bxf7+", "c4f7")
    ply.color = "white"
    ply.fen_before = "rn1qkbnr/ppp2ppp/3p4/4p3/2B1P1b1/5N2/PPPP1PPP/RNBQK2R w KQkq - 2 4"
    ply.pv_san = ["Bxf7+", "Kxf7", "Ng5+"]

    line = _variant_line(CriticalPosition(kind="a", ply=ply, score=20.0))

    assert line == "Variante : 4.Bxf7+ prend pion f7, échec ; 4...Kxf7 reprend ; 5.Ng5+ échec."


def test_caption_error_shows_eval_drop():
    ply = _ply(7, 4, "Bg4", "Bxf7+", "c4f7")
    ply.win_before, ply.win_after, ply.loss = 62.0, 41.0, 21.0
    caption = _caption(1, CriticalPosition(kind="a", ply=ply, score=21.0), [ply])
    assert caption.endswith("évaluation : 62 % → 41 % (−21 pts)")


def test_caption_only_move_shows_second_best_gap():
    ply = _ply(7, 4, "Bg4", "Bg4", "c8g4")
    ply.win_before, ply.second_gap = 72.0, 24.0
    caption = _caption(1, CriticalPosition(kind="c", ply=ply, score=24.0), [ply])
    assert caption.endswith("2e meilleur coup : 72 % → 48 % (−24 pts)")


def test_render_receives_first_three_pv_moves(monkeypatch, tmp_path):
    ply = _ply(1, 17, "Ng4+", "d6", "d7d6")
    ply.pv_uci = ["d7d6", "g1f3", "b8c6", "f1c4"]
    analysis = GameAnalysis(headers={}, nico_color="black", color_source="header", plies=[ply],
                            critical=[CriticalPosition(kind="a", ply=ply, score=ply.loss)])
    render = MagicMock(side_effect=lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", render)
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}}
    )

    assert render.call_args.kwargs["best_line_uci"] == ["d7d6", "g1f3", "b8c6"]


def test_multi_games_grouped_answer(monkeypatch, tmp_path):
    def _analysis(white, uci):
        p = _ply(1, 17, "Ng4+", "d6", "d7d6")
        p.uci = uci
        return GameAnalysis(headers={"White": white, "Black": "staroflexeur", "Result": "0-1"},
                            nico_color="black", color_source="header", plies=[p],
                            critical=[CriticalPosition(kind="a", ply=p, score=p.loss)])
    by_white = {"A": _analysis("A", "a7a6"), "B": _analysis("B", "b7b6")}
    monkeypatch.setattr(chess_router_mod, "analyze",
                        lambda text, *a: by_white["A" if '"A"' in text else "B"])
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    write_game = MagicMock()
    monkeypatch.setattr(chess_router_mod, "write_chess_game", write_game)
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []
    pgn = '[White "A"]\n\n1. e4 e5 0-1\n\n[White "B"]\n\n1. d4 d5 0-1'

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": pgn, "metadata": {"chat_id": 42}}
    )

    assert [i["caption"][:21] for i in result["images"]] == ["Partie 1 — Position 1", "Partie 2 — Position 1"]
    assert result["text"].startswith("Partie 1 — A – staroflexeur (0-1)\nexplication")
    assert "\n\nPartie 2 — B – staroflexeur (0-1)\nexplication" in result["text"]
    assert write_game.call_count == 2


_GAME_A = '[White "A"]\n\n1. e4 e5 0-1'
_GAME_B = '[White "B"]\n\n1. d4 d5 0-1'
_HASH_A = hashlib.sha256(b"e2e4e7e5").hexdigest()[:16]


def _duplicate_router(monkeypatch, tmp_path, games):
    """Router dont le palace contient `games` ; retourne (router, analyze, write, llm)."""
    def _analysis(text, *a):
        p = _ply(1, 17, "Ng4+", "d6", "d7d6")
        return GameAnalysis(headers={"White": "A" if '"A"' in text else "B", "Black": "staroflexeur"},
                            nico_color="black", color_source="header", plies=[p],
                            critical=[CriticalPosition(kind="a", ply=p, score=p.loss)])
    analyze = MagicMock(side_effect=_analysis)
    write_game = MagicMock()
    monkeypatch.setattr(chess_router_mod, "analyze", analyze)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", write_game)
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = games
    router = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge)
    return router, analyze, write_game, llm_exec


def test_known_game_answers_without_analysis(monkeypatch, tmp_path):
    fiche = {"id": f"chess_game_{_HASH_A}", "opponent": "X", "timestamp": "2026-10-31T08:00:00+00:00"}
    router, analyze, write_game, llm_exec = _duplicate_router(monkeypatch, tmp_path, [fiche])

    # En-têtes différents, mêmes coups : même partie.
    result = router.execute({"content": '[White "Autre"]\n\n1. e4 e5 1-0', "metadata": {}})

    assert result == {"text": "Cette partie contre X a déjà été envoyée le 2026-10-31."}
    analyze.assert_not_called()
    write_game.assert_not_called()
    llm_exec.execute.assert_not_called()


def test_new_game_keeps_pipeline(monkeypatch, tmp_path):
    fiche = {"id": "chess_game_autre", "opponent": "X", "timestamp": "2026-10-31T08:00:00+00:00"}
    router, analyze, write_game, llm_exec = _duplicate_router(monkeypatch, tmp_path, [fiche])

    result = router.execute({"content": _GAME_A, "metadata": {}})

    analyze.assert_called_once()
    write_game.assert_called_once()
    assert len(result["images"]) == 1


def test_multi_games_known_and_repeated(monkeypatch, tmp_path):
    fiche = {"id": f"chess_game_{_HASH_A}"}
    router, analyze, write_game, _ = _duplicate_router(monkeypatch, tmp_path, [fiche])

    # Partie 1 connue, partie 2 nouvelle, partie 3 = partie 2.
    result = router.execute({"content": f"{_GAME_A}\n\n{_GAME_B}\n\n{_GAME_B}", "metadata": {}})

    assert analyze.call_count == 1
    assert write_game.call_count == 1
    assert result["text"].startswith("Partie 1 — déjà envoyée\n\nPartie 2 — ")
    assert result["text"].endswith("\n\nPartie 3 — déjà envoyée")
    assert [i["caption"][:21] for i in result["images"]] == ["Partie 2 — Position 1"]


def test_multi_games_all_known_text_only(monkeypatch, tmp_path):
    fiche = {"id": f"chess_game_{_HASH_A}"}
    router, analyze, _, llm_exec = _duplicate_router(monkeypatch, tmp_path, [fiche])

    result = router.execute({"content": f"{_GAME_A}\n\n{_GAME_A}", "metadata": {}})

    assert result["text"] == "Partie 1 — déjà envoyée\n\nPartie 2 — déjà envoyée"
    assert result["images"] == []
    analyze.assert_not_called()
    llm_exec.execute.assert_not_called()


def test_goring_consigne_gives_the_gambit_idea(monkeypatch, tmp_path):
    # Le plan d'un Göring vient de l'idée du gambit, pas de la reprise du pion (Scotch).
    plies = [_ply(1, 17, "Ng4+", "d6", "d7d6")]
    analysis = GameAnalysis(headers={"White": "staroflexeur", "Black": "Ami"}, nico_color="white",
                            color_source="header", plies=plies, critical=[])
    real_summarize = chess_router_mod.summarize
    monkeypatch.setattr(chess_router_mod, "summarize",
                        lambda a: {**real_summarize(a), "opening_group": "Göring Gambit"})
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "[White \"staroflexeur\"] 1. e4", "metadata": {}}
    )

    content = llm_exec.execute.call_args.args[0]["content"]
    assert "colonnes c et d et les diagonales a1-h8 et a2-g8" in content
    assert "c'est la Scotch normale" in content
