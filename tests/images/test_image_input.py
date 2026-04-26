# test/images/test_image_input.py

from media.image_service import ImageService


class FakeCaptionModel:
    def describe(self, path):
        return "une maison dans les arbres"


def test_image_input_store(monkeypatch):
    service = ImageService()

    service.caption_model = FakeCaptionModel()

    service.store_input(
        img_path="/tmp/img.png",
        caption="une maison dans les arbres",
        metadata={"source": "test"}
    )