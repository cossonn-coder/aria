# test/cognition/test_kernel_integration.py

import asyncio
from core.kernel import AriaKernel


class KernelRunner:  # ← plus Test*

    def __init__(self):
        self.kernel = AriaKernel()

    def run_sync(self, msg):
        return asyncio.run(
            self.kernel.handle_message(msg, metadata={"source": "test"})
        )


def test_unknown_message():
    k = KernelRunner()
    out = k.run_sync("salut")
    assert isinstance(out, str)


def test_planning_flow():
    k = KernelRunner()
    out = k.run_sync("je veux construire une maison")
    assert isinstance(out, str)