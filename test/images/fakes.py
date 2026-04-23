class DummyVision:
    """
    Fake vision client used for deterministic unit tests.

    Does not perform any IO or network calls.
    """

    def __init__(self, **_):
        pass

    def describe(self, image, prompt):
        return "caption ok"