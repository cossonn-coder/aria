from intent.intent_engine import IntentEngine


class FakeEmbedder:
    def encode(self, texts):
        return [[float(len(t))] for t in texts]


class FakeDecision:
    def __init__(self, action, primary_intent_id=None):
        self.action = action
        self.primary_intent_id = primary_intent_id


def test_create_intent():
    engine = IntentEngine(FakeEmbedder())

    decision = FakeDecision("create")

    intent = engine.apply(
        decision=decision,
        message="build house"
    )

    assert intent is not None
    assert intent.status == "active"


def test_attach_existing_intent():
    engine = IntentEngine(FakeEmbedder())

    created = engine.apply(
        FakeDecision("create"),
        message="build house"
    )

    attached = engine.apply(
        FakeDecision("attach", created.id),
        message="roof details"
    )

    assert attached.id == created.id
    assert len(attached.actions) >= 2


def test_split_creates_new_intent():
    engine = IntentEngine(FakeEmbedder())

    i1 = engine.apply(FakeDecision("create"), "project A")
    i2 = engine.apply(FakeDecision("split"), "project B")

    assert i1.id != i2.id