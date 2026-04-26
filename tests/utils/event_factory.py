#aria/test/utils/event_factory.py
import uuid
from core.event import Event, EventType


def make_text_event(content: str, user_id: str = "test-user"):
    return Event(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=EventType.TEXT,
        content=content,
        metadata={"source": "test"},
    )