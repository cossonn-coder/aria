def test_image_router_instantiation():
    from llm.image_router import ImageRouter

    router = ImageRouter(
        vision_table=[],
        generation_table=[],
    )

    assert router is not None