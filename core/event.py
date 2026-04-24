# aria/core/event.py

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum
import uuid


class EventType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    FILE = "file"
    SYSTEM = "system"


@dataclass
class Event:
    id: str
    type: EventType
    user_id: str
    content: Any
    metadata: Dict[str, Any]
    conversation_id: Optional[str] = None

    @staticmethod
    def create(event_type: EventType, user_id: str, content: Any, metadata: dict):
        return Event(
            id=str(uuid.uuid4()),
            type=event_type,
            user_id=user_id,
            content=content,
            metadata=metadata or {},
        )