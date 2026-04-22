# aria/interfaces/base_interface.py
from abc import ABC, abstractmethod
from agents.base_agent import AgentContext


class BaseInterface(ABC):
    def __init__(self, kernel):
        self.kernel = kernel

    @abstractmethod
    async def start(self):
        raise NotImplementedError