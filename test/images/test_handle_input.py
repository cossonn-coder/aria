def test_handle_input():
    from llm.image_router import ImageRouter

    class FakeVision:
        def describe(self, image, prompt=None):
            return "image-caption"

    router = ImageRouter(
        vision_table=[
            {"provider": "fake", "client": lambda **kw: FakeVision()},
        ],
        generation_table=[],
    )

    class Input:
        source = "file"
        path = "/tmp/img.png"
        base64 = None

    result = router.handle_input(Input())

    assert result.caption == "image-caption"
    assert result.path == "/tmp/img.png"