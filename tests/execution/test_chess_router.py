# tests/execution/test_chess_router.py
#
# Tests du ChessExecutionRouter (sprint 26, tronçon 02) — analyse et rendu
# monkeypatchés : pas de Stockfish, pas de Pillow.

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import chess
import pytest

import execution.routers.chess_router as chess_router_mod
from chess_coach.analysis import CriticalPosition, GameAnalysis, PlyAnalysis
from chess_coach.explosive import ExplosiveMove
from chess_coach.player_model import GameDelta, Profile, Rating, Trial
from chess_coach.render import (ALT_ARROW, CURVE_BEST, CURVE_CORRECT, CURVE_NEUTRAL, PLAYED_ARROW, TRAP_ARROW, error_arrow)
from execution.routers.chess_router import ChessExecutionRouter, _caption, _intent_line, _move_facts, _rank_line, _variant_line


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


_REAL_PLAYED_FACTS = chess_router_mod._played_facts


@pytest.fixture(autouse=True)
def no_played_facts(monkeypatch):
    # Coups joués factices (17...Ng4+ illégal dans le FEN de _ply) : la ligne « suite
    # jouée » ne rejoue rien ; les tests qui la vérifient remettent _REAL_PLAYED_FACTS.
    monkeypatch.setattr(chess_router_mod, "_played_facts", lambda analysis, p: p.san)


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
    # Sprint 52 : précisions des fiches (ancienne 50 %, courante 41 %) pour la ligne 🏅.
    bridge.load_chess_games.return_value = [{**_season_game("chess_game_old"), "accuracy": 50.0},
                                            {**_season_game(current), "accuracy": 41.0}]

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "[White \"Ami\"] 1. e4", "metadata": {"chat_id": 42}}
    )

    delegated = llm_exec.execute.call_args.args[0]
    # Ligne déterministe (tronçon 08) entre le texte LLM et le bloc Progression.
    assert result["text"].startswith(
        "explication\n➖ Issue inconnue : creux 30 % au coup 19, pic 50 % au coup 17. "
        "Tournants : coups 17...Ng4+ (−20 pts) et 19...a6 (−20 pts).\n\n🎯 Précision : toi 41 % (1307)\n"
        "Meilleurs coups : toi 0/2 · adversaire 0/0\nErreurs : toi 2 erreurs · adversaire aucune\n"
        "Pire coup 17...Ng4+ (50 % → 30 %)\n"
        "🔵 meilleur 0 / 0 · ⚪ correct 0 / 0 · 🩷 imprécision 0 / 0 · 🔴 erreur 2 / 0 · ⚫ gaffe 0 / 0 · "
        "🟠 explosif / brillant 0 · 🩵 piège 0 · 🟢 meilleur coup du moteur\n\n"
        "🎮 Progression — saison 1, partie 2")
    # Sprint 52 : le rang de la précision est la dernière ligne du message.
    assert result["text"].endswith("\n\n🏅 Précision 41 % : 2e sur 2")
    assert "précision Nico : 41 %" in delegated["content"]
    assert "Historique (données) : 2 parties saison 1, classement global" in delegated["content"]
    assert len(result["images"]) == 3
    assert result["images"][-1]["caption"] == "Courbe de la partie : % de gain de Nico"
    assert result["images"][0]["caption"].startswith("Position 1 — coup 17 (noirs) : joué 🔴 17...Ng4+")
    assert delegated["op_type"] == "reasoning"
    assert "skip_intent" not in delegated["metadata"]
    assert "Position 1" in delegated["content"]
    assert delegated["metadata"]["forced_intent_name"] == "jeux echecs"
    assert delegated["content"].startswith("Partie contre Ami\n[Analyse Stockfish")
    assert "1re ligne exacte « Partie contre Ami »" in delegated["content"]
    assert "Niveau (données)" in delegated["content"]
    assert "une ligne « Bilan : » de 3 à 5 phrases" in delegated["content"]
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
        "Position 1 — coup 4 (noirs) : joué 🔴 4...Nf6, explosif 🟠 4...Qh4!? (meilleur 🟢 4...Nc6)\n"
        "Variante : 4...Qh4 attaque pion e4 ; 5.Nxh4 prend Qh4, décloue pion f2 ; 5...e5.\n"
        "Variante du meilleur coup : 4...Nc6 ; 5.Bb5."
    )
    assert render.call_args.kwargs["alt_uci"] == "d8h4"
    assert render.call_args.kwargs["played_uci"] == ply.uci
    assert "Position 1 (occasion explosive)" in content
    assert "offre la dame (9) ; forçant : menace" in content
    assert "réponse humaine la plus probable : Nxh4 (62 %)" in content
    assert "espérance face à un humain : Nico 58 % (meilleur coup : 46 %)" in content
    assert "variante : 5.Nxh4 e5 (avance de développement)" in content
    assert "faits : 5.Nxh4 (prend Qh4, décloue pion f2) 5...e5" in content
    assert "fin de variante : matériel : Nico Q de moins, % de gain Nico 75 %" in content
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
        "Position 1 — coup 8 (blancs) : tournant après 🔴 7...h6?, joué 🔵 8.e5 (meilleur 🟢 8.e5)\n"
        "Variante : 8.e5 ; 8...d5 ; 9.exd6 prend pion d5."
    )
    assert "Position 1 (tournant (erreur adverse punie))" in content
    assert "erreur adverse 7...h6 : perte 18 pts (meilleur 7...Be7)" in content
    assert "variante : 8.e5 d5 9.exd6 (gain matériel)" in content
    assert "montre la variante qui la punit" in content
    # Conversion de la notation française résiduelle en sortie ; bridge en échec → pas de bloc.
    assert result["text"].startswith("2.Qh5 Nxe5 Rae1 Be7, Cela\n➖ Issue inconnue ")
    assert "\n\n🎯 Précision" in result["text"]
    assert "Historique (données) :" not in content


def _replayed_plies(sans: list) -> list:
    """Demi-coups réels rejoués depuis la position initiale (FEN exacts), sans perte."""
    board, plies = chess.Board(), []
    for i, san in enumerate(sans):
        move = board.parse_san(san)
        plies.append(PlyAnalysis(
            ply=i, move_number=board.fullmove_number, color="white" if board.turn else "black",
            san=san, uci=move.uci(), fen_before=board.fen(), win_before=50.0, win_after=50.0,
            loss=0.0, best_san=san, best_uci=move.uci(), pv_san=[san], second_gap=None,
            quality="best", phase="opening", tags=[], clock=None, eval_before_cp=0, eval_after_cp=0,
        ))
        board.push(move)
    return plies


def test_enriched_gives_played_reply_opponent_error_and_story_facts(monkeypatch, tmp_path):
    # Sprint 53 : 3...Nd4? (erreur adverse) puis 4.Nxe5 (tournant, prend sans reprise), 4...Qg5.
    monkeypatch.setattr(chess_router_mod, "_played_facts", _REAL_PLAYED_FACTS)
    plies = _replayed_plies(["e4", "e5", "Nf3", "Nc6", "Bc4", "Nd4", "Nxe5", "Qg5"])
    plies[5].loss, plies[5].quality, plies[5].best_san = 20.0, "mistake", "Nf6"
    # Nxe5 cité par le déroulé comme pire coup de Nico (perte décisive).
    plies[6].loss, plies[6].win_after = 25.0, 25.0
    analysis = GameAnalysis(
        headers={}, nico_color="white", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="e", ply=plies[6], score=20.0,
                                   evidence="material", line_san=["Nxe5", "Qg5"])],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
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
    played = "4.Nxe5 (prend pion e5) 4...Qg5 (attaque pion g2, Ne5)"
    assert f"  suite jouée, faits : {played}\n" in content
    assert "  erreur adverse, faits : 3...Nd4\n" in content
    assert f"Coups du déroulé, faits : {played}\n" in content
    assert "Partout, entrées et Bilan : ne dis qu'une pièce est prise, échangée, reprise" in content


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


# Déroulé des deux coups factices de _run_with_llm_text (Nico noir, 50 % puis 30 % à chaque coup).
_STORY = "➖ Issue inconnue : creux 30 % au coup 19, pic 50 % au coup 17. Tournants : coups 17...Ng4+ (−20 pts) et 19...a6 (−20 pts)."


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
           "Position 2 — Nf6 développait avec tempo.\n\nBilan : solide. Peu d'erreurs.")
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    caps = [img["caption"] for img in result["images"]]
    assert caps[0].startswith("Position 1 — coup 17 (noirs) : joué 🔴 17...Ng4+")
    assert caps[0].endswith("\nLe fou devait parer l'échec.")
    assert caps[1].endswith("\nNf6 développait avec tempo.")
    assert "Position 1 —" not in result["text"] and "Position 2 —" not in result["text"]
    assert result["text"].startswith(
        f"Partie contre Ami\n{_STORY}\n\nBilan : solide. Peu d'erreurs.\n\n🎯 ")
    assert "\n\n🎮 Progression" in result["text"]


def test_missing_entry_keeps_current_behavior(monkeypatch, tmp_path):
    llm = "Partie contre Ami\n\nPosition 1 — Le fou devait parer l'échec.\n\nBilan : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    assert result["text"].startswith(llm.replace("\n", f"\n{_STORY}\n", 1) + "\n\n🎯 ")
    # Repli : légende = ligne factuelle + ligne « Variante : » du code, rien d'autre.
    assert result["images"][0]["caption"].count("\n") == 1
    assert result["images"][1]["caption"].endswith("\nVariante : 19...Nf6 attaque pion e4 ; 20.Nf3.")


def test_long_entry_cut_at_last_sentence(monkeypatch, tmp_path):
    long_entry = "Une phrase d'explication assez longue pour remplir. " * 30  # ~1500 car.
    llm = f"Partie contre Ami\nPosition 1 — {long_entry}\nPosition 2 — Court.\nBilan : solide."
    result = _run_with_llm_text(monkeypatch, tmp_path, llm)

    caption = result["images"][0]["caption"]
    assert len(caption) <= 1024
    assert caption.endswith("remplir. …")


def test_move_facts_names_unpinned_piece():
    # Partie du run live : le roi quitte la colonne d et libère le fou cloué par la tour.
    fen = "4r3/3k2pp/1ppb1p1n/p7/P1B2PP1/2P4P/1P3K2/2BR4 b - - 0 24"
    assert _move_facts(fen, ["Kc7"], 24, "black") == "24...Kc7 (décloue Bd6)"
    assert "décloue" not in _move_facts(fen, ["g5"], 24, "black")


def test_intent_line_threat_idea_and_self_pin():
    # Partie de référence (sprint 54) : 9.Ba3 chasse Qd6, 9...Qd7 décloue Nc6 mais se met
    # derrière lui sur la diagonale de Bb5 : Nc6 devient cloué sur la dame.
    board = chess.Board()
    plies = []
    for i, san in enumerate("e4 d5 exd5 Qxd5 Nc3 Qd6 Nf3 Nf6 b3 Nc6 Bb5 Bg4 h3 Bh5 O-O e6 Ba3 Qd7".split()):
        color = "white" if i % 2 == 0 else "black"
        plies.append(SimpleNamespace(ply=i, move_number=i // 2 + 1, color=color, san=san, fen_before=board.fen()))
        board.push_san(san)
    p = plies[17]

    line = _intent_line(plies, p)

    assert "9.Ba3 (attaque Qd6)" in line
    assert "met à l'abri Qd6" in line
    assert "décloue Nc6" in line
    assert "défend Nc6" not in line
    assert "Nc6 cloué sur Qd7 (par Bb5)" in line
    assert "temps" not in line
    assert "temps : 3 s" in _intent_line(plies, p, 3.2)



def test_intent_line_broadened_intents_and_maia_trace():
    # Tronçon 01b : intentions élargies sur des coups simples, puis trace Maia après le coup 10.
    def ply(san, move_number=1, played_p=None):
        return SimpleNamespace(ply=0, move_number=move_number, color="white", san=san,
                               fen_before=chess.STARTING_FEN, played_p=played_p)

    assert "développe Nf3" in _intent_line([ply("Nf3")], ply("Nf3"))
    assert "libère Qd1, Bf1" in _intent_line([ply("e4")], ply("e4"))
    # Tronçon 01c : le roque est une intention (run live : 10...O-O-O sans aucun fait).
    castle = SimpleNamespace(ply=0, move_number=4, color="white", san="O-O", played_p=None,
                             fen_before="r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
    assert "ton coup : roque" in _intent_line([castle], castle)

    p = ply("e4", move_number=14, played_p=0.123)
    line = _intent_line([p], p, human_line=["e4", "e5", "Nf3"])
    assert "Maia : coup choisi par 12 % des joueurs de ton niveau" in line
    assert "suite probable : 14...e5 15.Nf3 (attaque pion e5)" in line
    early = ply("e4", move_number=10, played_p=0.123)
    assert "Maia" not in _intent_line([early], early, human_line=["e4", "e5", "Nf3"])

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

    assert [i["caption"][:21] for i in result["images"]] == [
        "Partie 1 — Position 1", "Partie 1 — Courbe de ", "Partie 2 — Position 1", "Partie 2 — Courbe de "]
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
    assert len(result["images"]) == 2


def test_multi_games_known_and_repeated(monkeypatch, tmp_path):
    fiche = {"id": f"chess_game_{_HASH_A}"}
    router, analyze, write_game, _ = _duplicate_router(monkeypatch, tmp_path, [fiche])

    # Partie 1 connue, partie 2 nouvelle, partie 3 = partie 2.
    result = router.execute({"content": f"{_GAME_A}\n\n{_GAME_B}\n\n{_GAME_B}", "metadata": {}})

    assert analyze.call_count == 1
    assert write_game.call_count == 1
    assert result["text"].startswith("Partie 1 — déjà envoyée\n\nPartie 2 — ")
    assert result["text"].endswith("\n\nPartie 3 — déjà envoyée")
    assert [i["caption"][:21] for i in result["images"]] == ["Partie 2 — Position 1", "Partie 2 — Courbe de "]


def test_multi_games_all_known_text_only(monkeypatch, tmp_path):
    fiche = {"id": f"chess_game_{_HASH_A}"}
    router, analyze, _, llm_exec = _duplicate_router(monkeypatch, tmp_path, [fiche])

    result = router.execute({"content": f"{_GAME_A}\n\n{_GAME_A}", "metadata": {}})

    assert result["text"] == "Partie 1 — déjà envoyée\n\nPartie 2 — déjà envoyée"
    assert result["images"] == []
    analyze.assert_not_called()
    llm_exec.execute.assert_not_called()


def test_known_game_without_clock_reanalyzed_when_pgn_has_clock(monkeypatch, tmp_path):
    # Sprint 51 : fiche sans horloge + PGN avec %clk → réanalyse, date d'origine gardée.
    fiche = {"id": f"chess_game_{_HASH_A}", "opponent": "X", "timestamp": "2026-10-31T08:00:00+00:00",
             "plies_json": json.dumps([{"uci": "e2e4", "clock": None}, {"uci": "e7e5"}])}
    router, analyze, write_game, _ = _duplicate_router(monkeypatch, tmp_path, [fiche])

    router.execute({"content": '[White "A"]\n\n1. e4 { [%clk 0:09:58] } e5 { [%clk 0:09:57] } 0-1',
                    "metadata": {}})
    analyze.assert_called_once()
    assert write_game.call_args.kwargs["timestamp"] == "2026-10-31T08:00:00+00:00"

    # Même fiche, PGN sans horloge : toujours un doublon.
    analyze.reset_mock()
    result = router.execute({"content": _GAME_A, "metadata": {}})
    assert result == {"text": "Cette partie contre X a déjà été envoyée le 2026-10-31."}
    analyze.assert_not_called()


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


# Position avant 20.Bd8 (La_Bagouze – Mama_dor_de_pene, 2026-11-05).
_TRAP_FEN = "r1b2k1r/4bppp/p1p1p1q1/B1N2n2/4N3/7P/2P2PP1/R2Q1RK1 w - - 9 20"


def _trap_critical(replies):
    ply = _ply(39, 20, "Nd3", "Bb6", "a5b6")
    ply.color = "white"
    ply.fen_before = _TRAP_FEN
    ply.win_before = 60.0
    ply.pv_san = []
    explosive = ExplosiveMove(
        san="Bd8", uci="a5d8", loss=5.0, win_after=55.0, pv_san=["Bd8"], sacrifice=3, forcing=[],
        trap_reply_san="Bxd8", score=10.0, trap_line_san=["Bxd8", "Qxd8#"], replies=replies,
        evidence="mate", trap_end_fen=_TRAP_FEN, trap_end_win=100.0, expected=70.0, best_expected=60.0,
    )
    return CriticalPosition(kind="d", ply=ply, score=10.0, explosive=explosive)


_BXD8_MATE = {"san": "Bxd8", "p": 0.36, "line_san": ["Bxd8", "Qxd8#"], "win": 100.0}
_KG8_CALM = {"san": "Kg8", "p": 0.30, "line_san": ["Kg8", "Nd3", "e5"], "win": 55.0}


def test_trap_line_with_mate():
    line = _variant_line(_trap_critical([_BXD8_MATE, _KG8_CALM]))
    assert "\nPiège : 20.Bd8!? Si 20...Bxd8 (36 %), 21.Qxd8#. Sinon, pas de mat." in line


def test_trap_line_other_mate_drops_otherwise():
    other = {**_KG8_CALM, "line_san": ["Kg8", "Qd8#"]}
    assert "21.Qxd8#.\n" in _variant_line(_trap_critical([_BXD8_MATE, other])) + "\n"


def test_trap_line_without_mate():
    reply = {"san": "Kg8", "p": 0.40, "line_san": ["Kg8", "Nd3", "e5"], "win": 80.0}
    line = _variant_line(_trap_critical([reply]))
    assert "\nPiège : 20.Bd8!? Si 20...Kg8 (40 %), 21.Nd3 e5, 80 % pour toi." in line


def test_trap_position_is_cyan_and_llm_writes_plan_only(monkeypatch, tmp_path):
    critical = _trap_critical([_BXD8_MATE, _KG8_CALM])
    analysis = GameAnalysis(headers={}, nico_color="white", color_source="header",
                            plies=[critical.ply], critical=[critical])
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

    content = llm_exec.execute.call_args.args[0]["content"]
    assert render.call_args.kwargs["alt_color"] == chess_router_mod.TRAP_ARROW
    assert render.call_args.kwargs["played_color"] == chess_router_mod.PLAYED_ARROW
    assert "Position 1 (piège affiché)" in content
    assert "sans parler du piège ni de mat" in content
    assert "explosif 20.Bd8" not in content
    assert "pour chaque occasion explosive" not in content


def test_error_played_arrow_takes_severity_color(monkeypatch, tmp_path):
    ply = _ply(7, 4, "Nf6", "Nc6", "b8c6")
    ply.loss = 25.0
    analysis = GameAnalysis(headers={}, nico_color="black", color_source="header", plies=[ply],
                            critical=[CriticalPosition(kind="a", ply=ply, score=25.0)])
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

    assert render.call_args.kwargs["played_color"] == (215, 20, 35, 235)


def _run_lost_game(monkeypatch, tmp_path):
    """Une position critique, partie perdue dans une ouverture connue ; renvoie (résultat, appel LLM)."""
    plies = [_ply(1, 17, "Ng4+", "d6", "d7d6")]
    analysis = GameAnalysis(
        headers={"White": "Ami", "Black": "staroflexeur", "Result": "1-0", "Opening": "Dutch Defense"},
        nico_color="black", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="a", ply=plies[0], score=20.0)],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "Partie contre Ami\nPosition 1 — Plan : viser e4.\nBilan : à travailler."}
    bridge = MagicMock()
    current = "chess_game_" + hashlib.sha256(b"a7a6").hexdigest()[:16]
    bridge.load_chess_games.return_value = [_season_game("chess_game_old"), _season_game(current)]
    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "[White \"Ami\"] 1. e4", "metadata": {}}
    )
    return result, llm_exec.execute.call_args[0][0]


def test_story_goes_to_llm_and_above_the_bilan(monkeypatch, tmp_path):
    result, delegated = _run_lost_game(monkeypatch, tmp_path)

    assert "Déroulé (données) : 📉 Défaite : " in delegated["content"]
    # Ordre : titre, déroulé, bilan, 🎯, Progression.
    text = result["text"]
    assert text.startswith("Partie contre Ami\n📉 Défaite : ")
    assert text.index("Bilan :") < text.index("🎯") < text.index("🎮 Progression")


def test_material_line_names_pieces_and_pawns():
    # Position du coup 35 de la partie du run live : tour contre cavalier, 3 pions contre 4.
    fen = "5r1k/1P4pp/8/2Pp4/8/6P1/5q1P/3Q1N1K b - - 1 35"
    assert chess_router_mod._material_line(fen, "black") == "matériel : Nico R contre N, 3 pions contre 4"
    assert chess_router_mod._material_line(fen, "white") == "matériel : Nico N contre R, 4 pions contre 3"
    # Une pièce sans contrepartie ; pions égaux : rien à leur sujet.
    fen = "4k3/8/8/8/8/8/8/3QK3 w - - 0 1"
    assert chess_router_mod._material_line(fen, "white") == "matériel : Nico Q de plus"
    assert chess_router_mod._material_line(fen, "black") == "matériel : Nico Q de moins"


def test_error_caption_compares_both_lines():
    """Sprint 50 : une erreur montre les deux suites et où chacune mène, écrit par le code."""
    # Position du coup 35 de la partie du run live : la dame prend le cavalier, puis les dames partent.
    ply = _ply(0, 35, "Qxf1+", "Qxc5", "f2c5")
    ply.fen_before = "5r1k/1P4pp/8/2Pp4/8/6P1/5q1P/3Q1N1K b - - 1 35"
    ply.win_before, ply.win_after = 82.0, 11.0
    critical = CriticalPosition(kind="a", ply=ply, score=71.0,
                                best_line_san=["Qxc5", "h4"],
                                played_line_san=["Qxf1+", "Qxf1", "Rxf1+", "Kg2"])
    assert chess_router_mod._variant_line(critical) == (
        "Meilleur coup : 🟢 35...Qxc5 prend pion c5 ; 36.h4.\n"
        "  → matériel : Nico R contre N, 82 % de gain\n"
        "Ton coup : 🔴 35...Qxf1+ prend Nf1, échec, attaque Qd1 ; 36.Qxf1 reprend, attaque Rf8 ; "
        "36...Rxf1+ reprend, échec ; 37.Kg2 attaque Rf1.\n"
        "  → matériel : Nico R de plus, 3 pions contre 4, 11 % de gain"
    )


def _colors_analysis():
    """Erreur, piège, explosif, coup meilleur, coup correct, coup « good »."""
    plies = [_ply(i, 10 + i, "Nf3", "d6", "d7d6") for i in range(6)]
    for p, (loss, quality) in zip(plies, [(30.0, "mistake"), (0.0, "best"), (0.0, "best"),
                                          (0.0, "best"), (1.0, "correct"), (3.0, "good")]):
        p.loss, p.quality, p.win_before = loss, quality, 50.0
    def explosive(replies):
        return ExplosiveMove(san="Bd8", uci="a5d8", loss=5.0, win_after=55.0, pv_san=["Bd8"], sacrifice=3,
                             forcing=[], trap_reply_san="Bxd8", score=1.0, replies=replies)

    trap = explosive([{"san": "Bxd8", "p": 0.5, "line_san": ["Bxd8"], "win": 99.0}])
    analysis = GameAnalysis(headers={}, nico_color="black", color_source="header", plies=plies, explosive=[
        CriticalPosition(kind="d", ply=plies[1], score=1.0, explosive=trap),
        CriticalPosition(kind="d", ply=plies[2], score=1.0, explosive=explosive([])),
    ])
    return analysis


def test_point_colors_follow_each_move():
    """Sprint 50 : erreur en dégradé, piège en cyan, explosif en orange ; sprint 51 : meilleur
    coup en bleu (flèche du coup joué), correct en blanc, sinon neutre."""
    assert CURVE_BEST == PLAYED_ARROW[:3] and CURVE_CORRECT == (255, 255, 255)
    assert chess_router_mod._point_colors(_colors_analysis()) == [
        error_arrow(30.0)[:3], TRAP_ARROW[:3], ALT_ARROW[:3], CURVE_BEST, CURVE_CORRECT, CURVE_NEUTRAL,
        CURVE_NEUTRAL,
    ]


def test_marks_key_counts_both_sides():
    """Sprint 51 : clé des pastilles avec comptes toi / adversaire ; explosif et piège pour Nico seul."""
    summary = {"nico_best": 23, "opponent_best": 22, "nico_correct": 31, "opponent_correct": 32,
               "nico_inaccuracy": 1, "opponent_inaccuracy": 0, "nico_mistake": 0, "opponent_mistake": 1,
               "nico_blunder": 0, "opponent_blunder": 0}
    assert chess_router_mod._marks_key(summary, _colors_analysis()) == (
        "🔵 meilleur 23 / 22 · ⚪ correct 31 / 32 · 🩷 imprécision 1 / 0 · 🔴 erreur 0 / 1 · "
        "⚫ gaffe 0 / 0 · 🟠 explosif / brillant 1 · 🩵 piège 1 · 🟢 meilleur coup du moteur")


def test_conversion_line_and_miniature_before_curve(monkeypatch, tmp_path):
    """Sprint 51 : partie perdue après 12 coups à 85 % : ligne Conversion sous le déroulé,
    miniature de l'idée principale juste avant la courbe."""
    from tests.chess_coach.test_conversion import conversion_plies
    plies = conversion_plies()
    analysis = GameAnalysis(headers={"White": "staroflexeur", "Black": "Ami", "Result": "0-1"},
                            nico_color="white", color_source="header", plies=plies, critical=[])
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "Partie contre Ami\nBilan : à travailler."}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}})

    lines = result["text"].split("\n")
    assert lines[1].startswith("📉 Défaite")
    assert lines[2].startswith("🔄 Conversion : 12 coups à 80 % ou plus")
    assert "Conversion (données) : 🔄 Conversion" in llm_exec.execute.call_args.args[0]["content"]
    assert [img["caption"] for img in result["images"]] == [
        "Conversion — coup 3 : idée répétée 🟢 3.Kd2 (activer le roi), proposée 3 fois ; joué ⚪ 3.b3",
        "Courbe de la partie : % de gain de Nico"]


def test_game_without_clock_forbids_time_talk(monkeypatch, tmp_path):
    """Sprint 51 : sans horloge, pas de ligne Temps et consigne interdisant la cause « temps »."""
    result, delegated = _run_lost_game(monkeypatch, tmp_path)

    assert "aucune donnée de pendule : ne parle pas de gestion du temps" in delegated["content"]
    assert "Temps (données)" not in delegated["content"]
    assert "⏱️" not in result["text"]


def test_long_think_outside_critical_gets_image_and_caption(monkeypatch, tmp_path):
    """Sprint 51 : réflexion de 54 s hors position critique → Position 2 numérotée à la suite,
    légende « en 54 s », entrée LLM « Pour jouer vite : »."""
    plies = [_ply(1, 17, "Ng4+", "d6", "d7d6"), _ply(3, 18, "a6", "Nf6", "g8f6")]
    plies[0].clock, plies[1].clock = 590.0, 536.0
    analysis = GameAnalysis(
        headers={"White": "Ami", "Black": "staroflexeur", "TimeControl": "600"},
        nico_color="black", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="a", ply=plies[0], score=20.0)],
    )
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "Partie contre Ami\nPosition 1 — Plan : viser e4.\n"
                                             "Position 2 — Pour jouer vite : jouer Nf6.\nBilan : ok."}
    bridge = MagicMock()
    bridge.load_chess_games.return_value = []

    result = ChessExecutionRouter(llm_execution_router=llm_exec, mempalace_bridge=bridge).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}})

    content = llm_exec.execute.call_args.args[0]["content"]
    assert "Position 2 (réflexion longue de 54 s) — coup 18 :" in content
    assert "de Position 1 à Position 2, aucune omise" in content
    assert "« Pour jouer vite : »" in content
    assert "Temps (données) : ⏱️ Temps : toi 32,0 s par coup." in content
    captions = [img["caption"] for img in result["images"]]
    assert len(captions) == 3
    assert captions[1].startswith("Position 2 — coup 18 (noirs) : joué 🔴 18...a6 en 54 s, meilleur 🟢 18...Nf6")
    assert captions[1].endswith("Pour jouer vite : jouer Nf6.")
    assert "⏱️ Temps : toi 32,0 s par coup. Réflexions de 20 s ou plus : 18...a6 54 s." in result["text"]


def test_moves_line_shows_both_official_elo():
    """Sprint 52 : Elo officiel de chaque camp entre parenthèses sur la ligne 🎯."""
    summary = {"accuracy": 84.2, "accuracy_opponent": 79.0, "elo_nico": 1354, "elo_opponent": 1332,
               "nico_best": 23, "opponent_best": 22, "nico_correct": 31, "opponent_correct": 32,
               "nico_inaccuracy": 1, "opponent_inaccuracy": 0, "nico_mistake": 0, "opponent_mistake": 1,
               "nico_blunder": 0, "opponent_blunder": 0, "nico_moves": 55, "opponent_moves": 55,
               "brilliant_moves": None, "best_move": None, "worst_move": None}
    line = chess_router_mod._moves_line(summary, _colors_analysis())
    assert line.startswith("🎯 Précision : toi 84 % (1354) · adversaire 79 % (1332)\n")


def test_rank_line_gives_overall_day_and_opening_ranks():
    """Sprint 55 : rang global, du jour et de l'ouverture (groupe + couleur) ; un segment
    jour ou ouverture qui porte sur 1 partie est omis."""
    caro = {"opening": "Caro-Kann Defense", "opening_group": "Caro-Kann Defense", "nico_color": "white"}
    games = [
        {**caro, "accuracy": 95.0, "date": "2026.11.08"},
        {**caro, "accuracy": 80.0, "date": "2026.11.09"},
        {**caro, "accuracy": 85.0, "timestamp": "2026-11-09T10:00:00"},
        {**caro, "nico_color": "black", "accuracy": 99.0, "date": "2026.11.09"},
        {"opening": "Scotch Game", "nico_color": "white", "accuracy": 70.0, "date": "2026.11.07"},
    ]
    summary = {**caro, "accuracy": 85.0, "date": "2026.11.09"}
    assert _rank_line(summary, games) == (
        "🏅 Précision 85 % : 3e sur 5 · 2e sur 3 aujourd'hui · 2e sur 3 en Caro-Kann Defense (blancs)")
    # Seule partie du jour et seule Scotch Game en blancs : les deux segments disparaissent.
    scotch = {"opening": "Scotch Game", "nico_color": "white", "accuracy": 70.0, "date": "2026.11.07"}
    assert _rank_line(scotch, games) == "🏅 Précision 70 % : 5e sur 5"
