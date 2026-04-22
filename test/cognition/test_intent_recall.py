from intent.intent_recall_engine import IntentRecallEngine


class FakeEmbedder:
    def encode(self, texts):
        return [[float(len(t))] for t in texts]


class FakeIntent:
    def __init__(self, id):
        self.id = id
        self.status = "active"
        self.embedding = [10.0]


def test_recall_create_when_empty():
    engine = IntentRecallEngine(FakeEmbedder(), threshold=0.9)

    decision, scored = engine.resolve(
        "hello world",
        intents=[],
        memory_context=None
    )

    assert decision.action == "create"


def test_recall_attach_when_strong_match():
    engine = IntentRecallEngine(FakeEmbedder(), threshold=0.1)

    intents = [FakeIntent("A")]

    decision, scored = engine.resolve(
        "build house",
        intents=intents
    )

    assert decision.action in {"attach", "create", "split"}