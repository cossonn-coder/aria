def test_dispatch_generate():
    from llm.image_router import ImageRouter

    class DummyClientFail:
        def generate(self, prompt):
            raise Exception("fail")

    class DummyClientOK:
        def generate(self, prompt):
            class R:
                path = "ok.png"
                caption = "ok"
            return R()

    router = ImageRouter(
        vision_table=[],
        generation_table=[
            {"provider": "a", "client": lambda **kw: DummyClientFail()},
            {"provider": "b", "client": lambda **kw: DummyClientOK()},
        ],
    )

    result = router.generate("test")

    assert result.caption == "ok"
    assert result.path is not None