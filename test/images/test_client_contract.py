import httpx
from llm.vision.groq_vision import GroqVisionClient


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "choices": [{"message": {"content": "desc"}}]
        }


def test_groq_vision_call(monkeypatch):

    def fake_post(*_, **__):
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = GroqVisionClient(
        base_url="http://test",
        api_key="x",
        model="m",
    )

    result = client.describe("image.png", "prompt")

    assert result == "desc"