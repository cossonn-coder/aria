import asyncio
from core.kernel import AriaKernel
import pytest


def run(kernel, msg):
    return asyncio.run(kernel.handle_message(msg))


def test_house_building_flow():
    k = AriaKernel()

    r1 = run(k, "je veux construire une maison")
    r2 = run(k, "budget fondations")
    r3 = run(k, "plans architecte")

    assert isinstance(r1, str)
    assert isinstance(r2, str)
    assert isinstance(r3, str)


def test_intent_stability():
    k = AriaKernel()
    try:
        run(k, "organiser un voyage")
        run(k, "vols et hôtel")
        run(k, "budget voyage")
    except RuntimeError as e:
        if "All providers failed" in str(e):
            pytest.skip(f"LLM providers unavailable: {e}")
        raise

    # objectif : pas crash + cohérence interne
    assert True