import pytest
from pathlib import Path
from llm.image_gen.pollinations_client import PollinationsClient


class FakeResponse:
    content = b"fakeimage"
    headers = {"content-type": "image/jpeg"}
    text = ""

    def raise_for_status(self):
        pass


def test_pollinations_writes_file(monkeypatch, tmp_path):

    def fake_get(*_, **__):
        return FakeResponse()

    import httpx
    monkeypatch.setattr(httpx, "get", fake_get)

    client = PollinationsClient(
        base_url="http://test",
        output_dir=tmp_path,
    )

    result = client.generate("cat")

    assert Path(result.path).exists()


def test_pollinations_with_key_calls_authenticated_endpoint(monkeypatch, tmp_path):
    # Mode à clé (sprint 24) : endpoint /image/, modèle en param, header Bearer.
    calls = {}

    def fake_get(url, params=None, headers=None, **__):
        calls.update(url=url, params=params, headers=headers)
        return FakeResponse()

    import httpx
    monkeypatch.setattr(httpx, "get", fake_get)

    client = PollinationsClient(
        base_url="https://gen.pollinations.ai",
        output_dir=tmp_path,
        api_key="sk_test",
        model="tongyi-mai/z-image-turbo",
    )
    result = client.generate("un renard dans la neige")

    assert calls["url"].startswith("https://gen.pollinations.ai/image/un%20renard")
    assert calls["params"]["model"] == "tongyi-mai/z-image-turbo"
    assert calls["headers"]["Authorization"] == "Bearer sk_test"
    assert Path(result.path).exists()


def test_pollinations_non_image_response_raises(monkeypatch, tmp_path):
    # Un 200 non-image (JSON d'erreur) doit lever pour faire jouer le fallback.
    class JsonResponse(FakeResponse):
        headers = {"content-type": "application/json"}
        text = '{"error": "quota"}'

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *_, **__: JsonResponse())

    client = PollinationsClient(base_url="http://test", output_dir=tmp_path)
    with pytest.raises(RuntimeError):
        client.generate("cat")
