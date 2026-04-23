from llm.image_router import ImageRouter
from images.image_types import ImageInput


class DummyVision:
    def __init__(self, **_):
        pass

    def describe(self, *_, **__):
        return "caption ok"


def test_handle_input_returns_artifact(monkeypatch):
    from llm import image_router

    monkeypatch.setattr(
        image_router,
        "VISION_ROUTING_TABLE",
        [{"provider": "dummy", "client": DummyVision}],
    )

    router = ImageRouter()

    inp = ImageInput(path="/tmp/x.png")

    artifact = router.handle_input(inp)

    assert artifact.caption == "caption ok"
    assert artifact.source == "input"