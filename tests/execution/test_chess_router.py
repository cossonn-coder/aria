# tests/execution/test_chess_router.py
#
# Tests du ChessExecutionRouter (sprint 26, tronçon 02) — analyse et rendu
# monkeypatchés : pas de Stockfish, pas de Pillow.

from unittest.mock import MagicMock

import execution.routers.chess_router as chess_router_mod
from chess_coach.analysis import CriticalPosition, GameAnalysis, PlyAnalysis
from chess_coach.explosive import ExplosiveMove
from execution.routers.chess_router import ChessExecutionRouter


def _ply(ply, move_number, san, best_san, best_uci):
    return PlyAnalysis(
        ply=ply, move_number=move_number, color="black", san=san, uci="a7a6",
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        win_before=50.0, win_after=30.0, loss=20.0, best_san=best_san, best_uci=best_uci,
        pv_san=[best_san, "Nf3"], second_gap=None, quality="mistake",
        phase="middlegame", tags=["check"], clock=None, eval_before_cp=0, eval_after_cp=80,
    )


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

    result = ChessExecutionRouter(llm_execution_router=llm_exec).execute(
        {"op_type": "chess_analysis", "content": "[White \"Ami\"] 1. e4", "metadata": {"chat_id": 42}}
    )

    delegated = llm_exec.execute.call_args.args[0]
    assert result["text"] == "explication"
    assert len(result["images"]) == 2
    assert result["images"][0]["caption"].startswith("Position 1 — coup 17 (noirs) : joué 17...Cg4+")
    assert delegated["op_type"] == "reasoning"
    assert "skip_intent" not in delegated["metadata"]
    assert "Position 1" in delegated["content"]
    assert delegated["metadata"]["forced_intent_name"] == "jeux echecs"
    assert delegated["content"].startswith("Partie contre Ami\n[Analyse Stockfish")
    assert "Commence ta réponse par la ligne exacte « Partie contre Ami »" in delegated["content"]
    write_game.assert_called_once()
    assert write_game.call_args.kwargs["extra"]["nico_color"] == "black"


def test_explosive_position_caption_arrow_and_enriched(monkeypatch, tmp_path):
    # Sorte d construite à la main : 4...Cf6 joué, 4...Dh4!? explosif.
    ply = _ply(7, 4, "Nf6", "Nc6", "b8c6")
    explosive = ExplosiveMove(
        san="Qh4", uci="d8h4", loss=4.0, win_after=46.0, pv_san=["Qh4", "Nxh4"],
        sacrifice=9, forcing=["threat"], trap=12.0, trap_reply_san="Nxh4",
        volatility=0.0, score=12.0,
    )
    analysis = GameAnalysis(
        headers={}, nico_color="black", color_source="header", plies=[ply],
        critical=[CriticalPosition(kind="d", ply=ply, score=12.0, explosive=explosive)],
    )
    render = MagicMock(side_effect=lambda *a, **k: a[3])
    monkeypatch.setattr(chess_router_mod, "analyze", lambda *a: analysis)
    monkeypatch.setattr(chess_router_mod, "render_position", render)
    monkeypatch.setattr(chess_router_mod.config, "image_output_dir", str(tmp_path))
    monkeypatch.setattr(chess_router_mod, "write_chess_game", MagicMock())
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "explication"}

    result = ChessExecutionRouter(llm_execution_router=llm_exec).execute(
        {"op_type": "chess_analysis", "content": "1. e4", "metadata": {}}
    )

    content = llm_exec.execute.call_args.args[0]["content"]
    assert result["images"][0]["caption"] == (
        "Position 1 — coup 4 (noirs) : joué 4...Cf6, explosif 4...Dh4!? (meilleur 4...Cc6)"
    )
    assert render.call_args.kwargs["alt_uci"] == "d8h4"
    assert "Position 1 (occasion explosive)" in content
    assert "explosif 4...Dh4!? : coût 4 pts de % de gain (50 % → 46 %), ligne : 4...Dh4 5.Cxh4" in content
    assert "sacrifice : 9 pion(s) ; forçant : menace ; piège : si l'adversaire joue Cxh4, il perd 12 pts" in content
    assert "volatilité" not in content
    assert "ne le présente jamais comme le meilleur coup" in content


def test_normalize_images_result_is_images_text():
    from core.kernel import AriaKernel
    # _normalize n'utilise pas l'état du kernel : pas de construction complète.
    kernel = AriaKernel.__new__(AriaKernel)
    images = [{"path": "/tmp/p1.png", "caption": "Position 1"}]

    out = kernel._normalize({"status": "success", "data": {"text": "t", "images": images}})

    assert out == {"type": "images_text", "images": images, "text": "t"}
