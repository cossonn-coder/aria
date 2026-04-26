# aria/test/cognition/test_cognitive_scenarios.py
#
# ⚠️ IMPORTANT ARCHITECTURE CHANGE
# ------------------------------------------------------------
# Le Kernel ne consomme plus de strings directement.
# Il est désormais EVENT-DRIVEN :
#
#   string → Event → AriaKernel.handle_event()
#
# Tous les tests doivent refléter ce contrat.

import asyncio
import pytest

from core.kernel import AriaKernel
from core.event import Event
from core.event import EventType
from utils.event_factory import make_text_event


# ---------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------
# Construit un Event standard TEXT pour simuler une entrée utilisateur.
# C’est le point d’entrée canonique du système ARIA.
#
def run(kernel: AriaKernel, msg: str):
    event = make_text_event(msg)
    return asyncio.run(kernel.handle_event(event))


# ---------------------------------------------------------------------
# Cognitive flow simple
# ---------------------------------------------------------------------
# Vérifie uniquement :
# - absence de crash
# - retour string (interface Telegram compatible)
# - stabilité sur séquence de messages corrélés
#

@pytest.mark.integration
def test_house_building_flow():
    k = AriaKernel()

    r1 = run(k, "je veux construire une maison")
    r2 = run(k, "budget fondations")
    r3 = run(k, "plans architecte")

    assert isinstance(r1, str)
    assert isinstance(r2, str)
    assert isinstance(r3, str)


# ---------------------------------------------------------------------
# Stability test (multi-turn cognition)
# ---------------------------------------------------------------------
# Objectif :
# - vérifier que le pipeline ne casse pas sur enchaînement d’intents
# - vérifier robustesse LLM (fallback possible)
#

@pytest.mark.integration
def test_intent_stability():
    k = AriaKernel()

    try:
        run(k, "organiser un voyage")
        run(k, "vols et hôtel")
        run(k, "budget voyage")

    except RuntimeError as e:
        # Cas attendu en environnement sans providers LLM
        if "All providers failed" in str(e):
            pytest.skip(f"LLM providers unavailable: {e}")
        raise

    # Si aucun crash : succès structurel du pipeline
    assert True