# test/images/test_image_memory_structure.py

from media.image_models import ImageMemory


def test_image_memory_structure():
    img = ImageMemory(
        path="x.png",
        caption="test caption",
        prompt="test prompt",
        intent_id="intent_1",
        metadata={"k": "v"}
    )

    assert img.path == "x.png"
    assert img.caption == "test caption"
    assert img.intent_id == "intent_1"
    assert isinstance(img.metadata, dict)