# aria/media/image_models.py

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ImageMemory:
    path: str
    caption: str
    prompt: Optional[str]
    intent_id: Optional[str]
    metadata: Dict[str, Any]