from llm.image_router import ImageRouter


class DummyVisionClient:
    def __init__(self, **_):
        pass

    def describe(self, image, prompt):
        return "ok"


class DummyGenClient:
    def __init__(self, **_):
        pass

    def generate(self, prompt):
        class Result:
            path = "/tmp/test.png"
            caption = "generated"
        return Result()


def test_dispatch_vision(monkeypatch):
    from llm import image_router

    monkeypatch.setattr(
        image_router,
        "VISION_ROUTING_TABLE",
        [{"provider": "dummy", "client": DummyVisionClient}],
    )

    router = ImageRouter()

    result = router._run_vision("img", "prompt")

    assert result == "ok"


def test_dispatch_generation(monkeypatch):
    from llm import image_router

    monkeypatch.setattr(
        image_router,
        "GENERATION_ROUTING_TABLE",
        [{"provider": "dummy", "client": DummyGenClient}],
    )

    router = ImageRouter()

    result = router._run_generation("hello")

    assert result.path.endswith(".png")