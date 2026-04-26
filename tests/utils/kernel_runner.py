
1#aria/test/utils/kernel_runner.py
from utils.event_factory import make_text_event
import asyncio
from core.kernel import AriaKernel


class KernelRunner:

    def __init__(self):
        self.kernel = AriaKernel()

    def run_sync(self, msg):
        event = make_text_event(msg)
        return asyncio.run(self.kernel.handle_event(event))