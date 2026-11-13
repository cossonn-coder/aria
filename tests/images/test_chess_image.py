# tests/images/test_chess_image.py
#
# Sprint 59, tronçon 03 : image d'échiquier → lecture → Stockfish → réponse + diagramme.

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cognition.cognitive_classifier import is_chess_image
from cognition.cognitive_context import CognitiveOperation
from config import config
from execution.routers import image_router as image_module
from execution.routers.image_router import ImageExecutionRouter

STOCKFISH = Path(config.stockfish_path)
REF_GRID = (Path(__file__).parents[2] / "docs/sprint59/ref/chesscom_vert.txt").read_text().split()


@dataclass
class FakeArtifact:
    path: str = "/tmp/test.jpg"
    caption: str = ""
    prompt: str = ""


def _router(description: str, grid):
    internal = MagicMock()
    internal.handle_input.return_value = FakeArtifact(caption=description)
    internal.read_board.return_value = grid
    llm = MagicMock()
    llm.execute.return_value = {"text": "réponse enrichie"}
    return ImageExecutionRouter(internal_router=internal, llm_execution_router=llm), internal, llm


def _payload(caption):
    return {
        "op_type": CognitiveOperation.IMAGE_INPUT.value,
        "content": {"file_path": "/tmp/test.jpg", "caption": caption},
        "metadata": {"chat_id": 1},
    }


@pytest.fixture(autouse=True)
def _no_memory(monkeypatch, tmp_path):
    monkeypatch.setattr(image_module, "write_image_artifact", MagicMock())
    monkeypatch.setattr(image_module, "write_conversation_turn", MagicMock())
    monkeypatch.setattr(config, "image_output_dir", str(tmp_path))


@pytest.mark.skipif(not STOCKFISH.exists(), reason="Stockfish absent")
def test_chess_image_solved_with_diagram():
    router, _, llm = _router("Un échiquier vu de dessus.", REF_GRID)
    result = router.execute(_payload("trait aux noirs"))
    assert "1...dxc4" in result["text"]
    assert Path(result["images"][0]["path"]).exists()
    llm.execute.assert_not_called()
    assert image_module.write_conversation_turn.call_count == 2


def test_local_reader_used_when_gemini_fails(monkeypatch):
    local = MagicMock(return_value=None)
    monkeypatch.setattr(image_module.board_local, "read_board", local)
    router, _, _ = _router("Un échiquier.", None)
    result = router.execute(_payload(None))
    local.assert_called_once_with("/tmp/test.jpg")
    assert result["text"].startswith("Je n'arrive pas à lire l'échiquier")


def test_non_chess_image_keeps_enriched_mode():
    router, internal, llm = _router("Un jardin avec des tomates.", None)
    result = router.execute(_payload("c'est quoi ?"))
    assert result == {"text": "réponse enrichie"}
    internal.read_board.assert_not_called()


def test_is_chess_image():
    assert is_chess_image("Capture d'un échiquier en ligne", None)
    assert is_chess_image("Une image sombre", "Résous la position")
    assert not is_chess_image("Un jardin le matin", "c'est quoi ?")
    assert is_chess_image("Une capture d'écran sombre", "les blancs jouent, que faire ?")
