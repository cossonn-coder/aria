#aria/execution/execution_types.py

from typing import TypedDict, Any, Optional
from enum import Enum


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class ExecutionResult(TypedDict, total=False):
    status: ExecutionStatus
    data: Any
    error: Optional[str]
    router: str
