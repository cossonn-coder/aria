def test_metrics_snapshot():
    from llm.image_router import ImageRouter

    router = ImageRouter(
        vision_table=[],
        generation_table=[],
    )

    assert hasattr(router, "_dispatch")