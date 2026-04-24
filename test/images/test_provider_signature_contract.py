def test_provider_signature_contract():
    from inspect import signature

    class P:
        def generate(self, input): pass
        def describe(self, image): pass

    p = P()

    assert "input" in signature(p.generate).parameters
    assert "image" in signature(p.describe).parameters