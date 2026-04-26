# test/images/test_image_generation.py

from media.image_service import ImageService
from media.image_models import ImageMemory


class FakeResult:
    def __init__(self):
        self.path = "/tmp/test.png"
        self.caption = "un jardin pixelisé"


class FakeImageRouter:
    def generate(self, message):
        return FakeResult()


def test_image_generation_store(monkeypatch):
    service = ImageService()

    router = FakeImageRouter()

    monkeypatch.setattr(
        "aria.llm.image_router.ImageRouter",
        lambda: router
    )

    img = router.generate("draw a garden")

    service.store_generated(
        ImageMemory(
            path=img.path,
            caption=img.caption,
            prompt="draw a garden",
            intent_id="test_intent",
            metadata={}
        )
    )