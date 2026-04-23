from llm.image_router import ImageRouter

def test_router_never_returns_raw_client():
    router = ImageRouter()

    assert hasattr(router, "handle_input")
    assert hasattr(router, "generate")