from pathlib import Path
from llm.image_gen.pollinations_client import PollinationsClient


class FakeResponse:
    content = b"fakeimage"

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