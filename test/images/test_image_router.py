# aria/test/images/test_image_router.py

from llm.image_router import ImageRouter
from images.image_types import ImageInput
from fakes import DummyVision


def test_image_input(monkeypatch):
    from llm import image_router

    monkeypatch.setattr(
        image_router,
        "VISION_ROUTING_TABLE",
        [{"provider": "dummy", "client": DummyVision}],
    )

    router = ImageRouter()

    img = ImageInput(path="/tmp/test.png")

    artifact = router.handle_input(img)

    assert artifact.caption == "caption ok"


def test_image_generation():
    router = ImageRouter()

    artifact = router.generate("un jardin cyberpunk")

    assert artifact.source == "generated"
    assert artifact.path.endswith(".png")
    assert artifact.prompt == "un jardin cyberpunk"
    assert artifact.intent_id is None