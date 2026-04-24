# aria/execution/execution_dispatcher.py

from execution.operation import ExecutionOperation
from execution.routing_table import RoutingTable


class ExecutionDispatcher:

    def __init__(self, registry: dict, routing_table: RoutingTable):
        self.registry = registry
        self.routing_table = routing_table

    def dispatch(self, op: ExecutionOperation):

        router_name = self.routing_table.resolve(op.type)

        if router_name is None:
            return {
                "status": "failed",
                "error": f"No route for {op.type}",
            }

        router = self.registry.get(router_name)

        if router is None:
            return {
                "status": "failed",
                "error": f"No router: {router_name}",
            }

        try:
            result = router.execute(op.payload)

            return {
                "status": "success",
                "router": router_name,
                "data": result,
            }

        except Exception as e:
            return {
                "status": "failed",
                "router": router_name,
                "error": str(e),
            }