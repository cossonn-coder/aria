from llm.image_router import ImageRouter
from images.image_types import ImageInput


class DummyVision:
    def __init__(self, **_):
        pass

    def describe(self, image, prompt):
        return "caption ok"


def test_handle_input_returns_artifact():
    router = ImageRouter(
        vision_table=[
            {"provider": "dummy", "client": DummyVision}
        ]
    )

    inp = ImageInput(path="/tmp/x.png")

    artifact = router.handle_input(inp)

    assert artifact.caption == "caption ok"
    assert artifact.source == "input"