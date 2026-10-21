# aria/execution/execution_dispatcher.py

from execution.operation import ExecutionOperation
from execution.routing_table import RoutingTable
from logger import get_logger

log = get_logger(__name__)


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
            # Trace complète dans le journal ; le type reste visible dans
            # l'erreur même quand str(e) est vide (ex. TimeoutError()).
            log.exception("router %s failed", router_name)
            return {
                "status": "failed",
                "router": router_name,
                "error": f"{type(e).__name__}: {e}",
            }