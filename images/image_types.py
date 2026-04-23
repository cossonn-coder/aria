# aria/images/image_types.py
from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime, timezone

@dataclass
class ImageArtifact:
    source: str

    path: Optional[str] = None
    caption: Optional[str] = None
    prompt: Optional[str] = None
    intent_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ImageInput:
    path: Optional[str] = None
    base64: Optional[str] = None
    source: str = "telegram"