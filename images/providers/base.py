#aria/images/providers/base.py

from typing import Protocol


class VisionProviderProtocol(Protocol):
    def generate(self, input):
        ...

    def describe(self, image):
        ...