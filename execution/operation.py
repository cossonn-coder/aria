#aria/execution/operation.py

from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class ExecutionOperation:
    type: str
    payload: Any
    metadata: Dict[str, Any]