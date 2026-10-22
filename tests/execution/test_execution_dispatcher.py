# tests/execution/test_execution_dispatcher.py
#
# Sprint 29 : une exception de router laisse une trace dans le journal et
# son type reste visible dans l'erreur, même quand str(e) est vide.

import logging

from execution.execution_dispatcher import ExecutionDispatcher
from execution.operation import ExecutionOperation
from execution.routing_table import RoutingTable


class _TimeoutRouter:
    def execute(self, payload):
        raise TimeoutError()


def test_router_exception_is_logged_with_type(caplog):
    dispatcher = ExecutionDispatcher(
        registry={"slow_router": _TimeoutRouter()},
        routing_table=RoutingTable({"reasoning": "slow_router"}),
    )

    with caplog.at_level(logging.ERROR):
        result = dispatcher.dispatch(ExecutionOperation(type="reasoning", payload={}, metadata={}))

    assert result["status"] == "failed"
    assert "TimeoutError" in result["error"]
    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)
