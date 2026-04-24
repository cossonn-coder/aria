#aria/execution/router_registry.py

class RouterRegistry:
    def __init__(self):
        self._routers = {}

    def register(self, name: str, router):
        self._routers[name] = router

    def get(self, name: str):
        return self._routers.get(name)

    def has(self, name: str) -> bool:
        return name in self._routers