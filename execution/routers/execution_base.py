#aria/execution/execution_base.py

from abc import ABC, abstractmethod


class BaseRouter(ABC):

    @abstractmethod
    def execute(self, payload: dict):
        pass