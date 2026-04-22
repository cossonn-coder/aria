#aria/test/images/test_image_router.py
from llm.image_router import ImageRouter
from images.image_types import ImageInput


def test_image_input():
    router = ImageRouter()

    img = ImageInput(user_id="u1", path="/tmp/test.png")

    res = router.handle_input(img)

    assert res["status"] == "received"
    assert res["has_path"] is True


def test_image_generation():
    router = ImageRouter()

    out = router.generate("un jardin cyberpunk")

    assert out.path.endswith(".png")
    assert out.prompt == "un jardin cyberpunk"