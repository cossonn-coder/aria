# aria/cognition/dispatcher_types.py

from typing import TypedDict, Any

class DispatchResult(TypedDict, total=False):
    handled: bool
    result: Any
    short_circuit: bool