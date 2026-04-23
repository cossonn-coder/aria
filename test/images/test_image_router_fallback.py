from llm.image_router import ImageRouter


class FailingClient:
    def __init__(self, **_):
        pass

    def describe(self, *_, **__):
        raise RuntimeError("boom")


class WorkingClient:
    def __init__(self, **_):
        pass

    def describe(self, *_, **__):
        return "success"


def test_fallback_to_next_provider(monkeypatch):
    from llm import image_router

    monkeypatch.setattr(
        image_router,
        "VISION_ROUTING_TABLE",
        [
            {"provider": "fail", "client": FailingClient},
            {"provider": "ok", "client": WorkingClient},
        ],
    )

    router = ImageRouter()

    result = router._run_vision("img", "prompt")

    assert result == "success"