#aria/execution/execution_plan_builder.py

from execution.execution_types import ExecutionPlan


class ExecutionPlanBuilder:

    def __init__(self, routing_table):
        self.routing_table = routing_table

    def build(self, op):
        router = self.routing_table.resolve(op.type)

        return {
            "router": router,
            "payload": op.payload,
            "fallback_router": None,
        }