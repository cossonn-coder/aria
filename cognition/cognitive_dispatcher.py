#aria/cognition/cognitive_dispatcher.py
from typing import Callable, Any
from cognition.cognitive_context import CognitiveOperation


class CognitiveDispatcher:
    def __init__(self):
        self._handlers = {}

    def register(self, op):
        def wrapper(fn):
            self._handlers[op] = fn
            return fn
        return wrapper

    def dispatch(self, op, message, metadata):
        handler = self._handlers.get(op)

        if not handler:
            return {
                "handled": False,
                "result": None,
                "short_circuit": False
            }

        result = handler(message, metadata)

        return {
            "handled": True,
            "result": result,
            "short_circuit": True
        }