# Sprint 19, tronçon 01 : une réponse vision vide est un échec,
# le router passe au fournisseur suivant.

import httpx
import pytest

from images.image_types import ImageInput
from llm.image_router import ImageRouter
from llm.vision.groq_vision import GroqVisionClient


class FakeResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def test_empty_vision_content_raises(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *_, **__: FakeResponse(""))
    client = GroqVisionClient(base_url="http://test", api_key="x", model="m")

    with pytest.raises(ValueError):
        client.describe("image.png", "prompt")


def test_router_falls_back_after_empty_response(monkeypatch):
    # Le premier fournisseur répond vide, le second répond normalement.
    def fake_post(url, **__):
        return FakeResponse("" if url == "http://vide" else "une description")

    monkeypatch.setattr(httpx, "post", fake_post)

    router = ImageRouter(vision_table=[
        {"provider": "vide", "client": GroqVisionClient, "base_url": "http://vide", "model": "m"},
        {"provider": "ok", "client": GroqVisionClient, "base_url": "http://ok", "model": "m"},
    ])

    artifact = router.handle_input(ImageInput(path="/tmp/photo.jpg"))

    assert artifact.caption == "une description"
