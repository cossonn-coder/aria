# tests/test_kernel_user_id.py

import pytest
from aria.core.kernel import AriaKernel


@pytest.mark.asyncio
async def test_kernel_user_id_fallback():
    kernel = AriaKernel()

    result = await kernel.handle_message(
        "hello test",
        metadata={}
    )

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_kernel_user_id_propagation():
    kernel = AriaKernel()

    result = await kernel.handle_message(
        "hello test",
        metadata={"user_id": "unit_user_1"}
    )

    assert isinstance(result, str)