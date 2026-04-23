# aria/test/images/test_image_router.py

from llm.image_router import ImageRouter
from images.image_types import ImageInput


def test_image_input():
    router = ImageRouter()

    # user_id supprimé — ARIA est mono-utilisateur (décision architecture Sprint 2)
    img = ImageInput(path="/tmp/test.png")

    artifact = router.handle_input(img)

    assert artifact.source == "input"
    assert artifact.path == "/tmp/test.png"
    assert isinstance(artifact.caption, str)


def test_image_generation():
    router = ImageRouter()

    artifact = router.generate("un jardin cyberpunk")

    assert artifact.source == "generated"
    assert artifact.path.endswith(".png")
    assert artifact.prompt == "un jardin cyberpunk"
    assert artifact.intent_id is None