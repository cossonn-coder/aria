def test_fallback_order():
    from llm.image_router import ImageRouter

    calls = []

    class A:
        def generate(self, prompt):
            calls.append("A")
            raise Exception("fail")

    class B:
        def generate(self, prompt):
            calls.append("B")
            class R:
                path = "b.png"
                caption = "B"
            return R()

    router = ImageRouter(
        vision_table=[],
        generation_table=[
            {"provider": "a", "client": lambda **kw: A()},
            {"provider": "b", "client": lambda **kw: B()},
        ],
    )

    router.generate("x")

    assert "A" in calls
    assert "B" in calls