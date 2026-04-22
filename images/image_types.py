from dataclasses import dataclass
from typing import Optional

@dataclass
class ImageInput:
    user_id: str
    path: Optional[str] = None
    base64: Optional[str] = None
    source: str = "telegram"


@dataclass
class ImageOutput:
    prompt: str
    path: str
    model: str = "mock"