# aria/execution/routing_table.py

class RoutingTable:

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def resolve(self, operation_type: str) -> str:
        return self.mapping.get(operation_type)