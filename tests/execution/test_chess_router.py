# tests/execution/test_chess_router.py
#
# Tests du ChessExecutionRouter (sprint 26, tronçon 02) — analyse et rendu
# monkeypatchés : pas de Stockfish, pas de Pillow.

import hashlib
import json
from unittest.mock import MagicMock

import execution.routers.chess_router as chess_router_mod
from chess_coach.analysis import CriticalPosition, GameAnalysis, PlyAnalysis
from chess_coach.explosive import ExplosiveMove
from chess_coach.player_model import GameDelta, Profile, Rating, Trial
from execution.routers.chess_router import ChessExecutionRouter


def _ply(ply, move_number, san, best_san, best_uci):
    return PlyAnalysis(
        ply=ply, move_number=move_number, color="black", san=san, uci="a7a6",
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        win_before=50.0, win_after=30.0, loss=20.0, best_san=best_san, best_uci=best_uci,
        pv_san=[best_san, "Nf3"], second_gap=None, quality="mistake",
        phase="middlegame", tags=["check"], clock=None, eval_before_cp=0, eval_after_cp=80,
    )


def _season_game(doc_id):
    """Fiche saison 1 minimale (clé difficulty, 20 demi-coups)."""
    plies = [{"color": "black", "move_number": 20, "san": "Nf6", "loss": 0.0, "win_before": 50.0,
              "second_gap": 20.0, "difficulty": 1500.0, "tags": [], "best_san": "Nf6",
              "phase": "middlegame"}]
    return {"id": doc_id, "n_plies": 20, "plies_json": json.dumps(plies), "nico_color": "black",
            "elo_nico": 1307, "elo_opponent": 1300, "outcome": "win", "opening": "Scotch-Game"}


def test_execute_returns_text_and_images_and_delegates_reasoning(monkeypatch, tmp_path):
    plies = [_ply(1, 17, "Ng4+", "Bd7", "c8d7"), _ply(3, 19, "a6", "Nf6", "g8f6")]
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
    assert result["text"].startswith("explication\n\n🎮 Progression — saison 1, partie 2")
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
    assert "axes de travail" not in delegated["content"]
    # Faits calculés depuis le FEN (après 1.e4) : matériel égal, rien d'attaqué.
    assert "  matériel : égal\n  attaquées : aucune" in delegated["content"]
    assert "idées classiques de cette ouverture" not in delegated["content"]
    write_game.assert_called_once()
    assert write_game.call_args.kwargs["extra"]["nico_color"] == "black"


def test_explosive_position_caption_arrow_and_enriched(monkeypatch, tmp_path):
    # Sorte d construite à la main : 4...Nf6 joué, 4...Qh4!? explosif.
    ply = _ply(7, 4, "Nf6", "Nc6", "b8c6")
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
        "Position 1 — coup 4 (noirs) : joué 4...Nf6, explosif 4...Qh4!? (meilleur 4...Nc6)"
    )
    assert render.call_args.kwargs["alt_uci"] == "d8h4"
    assert "Position 1 (occasion explosive)" in content
    assert "offre la dame (9) ; forçant : menace" in content
    assert "réponse humaine la plus probable : Nxh4 (62 %)" in content
    assert "espérance face à un humain : Nico 58 % (meilleur coup : 46 %)" in content
    assert "variante : 5.Nxh4 e5 (avance de développement)" in content
    assert "fin de variante : matériel : Nico −9, % de gain Nico 75 %" in content
    assert "coût" not in content.split("[Consigne")[0]
    assert "si Nxh4 (62 %) : 5.Nxh4, 62 % pour Nico" in content
    assert "si d3 (20 %) : 5.d3 Nc6, 47 % pour Nico" in content
    assert ("pièces : blancs Ke1 Qd1 Ra1 Rh1 Bc1 Bf1 Nb1 Ng1, pions a2 b2 c2 d2 f2 g2 h2 e4 ; "
            "noirs Ke8 Qd8") in content
    assert "Notation anglaise : N, B, R, Q, K" in content
    assert "ouverture jouée : Scotch Gambit." in content
    assert "volatilité" not in content
    assert "ne le présente jamais comme le meilleur coup" in content


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
        "Position 1 — coup 8 (blancs) : tournant après 7...h6?, joué 8.e5 (meilleur 8.e5)"
    )
    assert "Position 1 (tournant (erreur adverse punie))" in content
    assert "erreur adverse 7...h6 : perte 18 pts (meilleur 7...Be7)" in content
    assert "variante : 8.e5 d5 9.exd6 (gain matériel)" in content
    assert "montre la variante qui la punit" in content
    # Conversion de la notation française résiduelle en sortie ; bridge en échec → pas de bloc.
    assert result["text"] == "2.Qh5 Nxe5 Rae1 Be7, Cela"
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
    plies = [_ply(1, 17, "Ng4+", "Bd7", "c8d7"), _ply(3, 19, "a6", "Nf6", "g8f6")]
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
    assert result["text"].startswith("Partie contre Ami\n\nNiveau : solide. Peu d'erreurs.\n\n🎮 Progression")


def test_missing_entry_keeps_current_behavior(monkeypatch, tmp_path):
    llm = "Partie contre Ami\n\nPosition 1 — Le fou devait parer l'échec.\n\nNiveau : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    assert result["text"].startswith(llm + "\n\n🎮 Progression")
    assert "\n" not in result["images"][0]["caption"]
    assert "\n" not in result["images"][1]["caption"]


def test_long_entry_cut_at_last_sentence(monkeypatch, tmp_path):
    long_entry = "Une phrase d'explication assez longue pour remplir. " * 30  # ~1500 car.
    llm = f"Partie contre Ami\nPosition 1 — {long_entry}\nPosition 2 — Court.\nNiveau : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    caption = result["images"][0]["caption"]
    assert len(caption) <= 1024
    assert caption.endswith("remplir. …")
