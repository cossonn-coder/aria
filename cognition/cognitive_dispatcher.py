#aria/cognition/cognitive_dispatcher.py


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
            return type("CognitiveResult", (), {
                "short_circuit": False,
                "result": None
            })

        result = handler(message, metadata)

        return type("CognitiveResult", (), {
            "short_circuit": True,
            "result": result
        })