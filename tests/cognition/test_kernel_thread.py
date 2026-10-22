# tests/cognition/test_kernel_thread.py
#
# Sprint 30 (#103) : handle_event exécute classify et dispatch hors de la
# boucle asyncio, pour que l'interface puisse envoyer pendant le traitement.

import asyncio
import threading
from unittest.mock import MagicMock

from core.event import Event, EventType
from core.kernel import AriaKernel


def test_dispatch_runs_outside_event_loop_thread():
    seen = {}

    def dispatch(exec_op):
        seen["thread"] = threading.get_ident()
        return {"status": "success", "data": {"text": "réponse"}}

    # Kernel construit sans auto-wire : seules les deux dépendances utiles.
    kernel = AriaKernel.__new__(AriaKernel)
    kernel.cognitive_engine = MagicMock()
    kernel.cognitive_engine.classify.return_value = MagicMock(
        short_circuit=False, type="unknown", interrogative=False,
    )
    kernel.execution_dispatcher = MagicMock()
    kernel.execution_dispatcher.dispatch.side_effect = dispatch

    event = Event.create(event_type=EventType.TEXT, user_id="1", content="salut", metadata={})
    result = asyncio.run(kernel.handle_event(event))

    assert seen["thread"] != threading.get_ident()
    assert result == "réponse"
