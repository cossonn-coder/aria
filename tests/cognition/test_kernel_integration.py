# test/cognition/test_kernel_integration.py
#
# 🔷 ARCHITECTURE NOTE
# ------------------------------------------------------------
# Le Kernel est event-driven :
#   input (str) → Event → AriaKernel.handle_event()
#
# Le helper KernelRunner est centralisé dans :
#   test/utils/kernel_runner.py
#
# Ce fichier ne redéfinit donc pas de runner local afin de :
# - éviter la duplication de logique de test
# - garantir un point d’entrée unique pour les tests Kernel
# - maintenir la cohérence avec le contrat système ARIA

import pytest

from utils.kernel_runner import KernelRunner


# ---------------------------------------------------------------------
# Integration tests - Kernel
# ---------------------------------------------------------------------
# Objectif :
# - valider que le Kernel exécute le pipeline complet sans crash
# - garantir la stabilité de l’orchestrateur
# - ne PAS tester les décisions cognitives (couvert ailleurs)
#
# Ces tests sont des tests de "system integration", pas de logique métier.

@pytest.mark.integration
def test_unknown_message():
    """
    Cas nominal minimal :
    message hors intention explicite.

    Attendu :
    - aucune exception
    - sortie normalisée (str)
    """
    k = KernelRunner()
    out = k.run_sync("salut")

    assert isinstance(out, str)


@pytest.mark.integration
def test_planning_flow():
    """
    Cas multi-intent simple :
    vérifie que le pipeline cognitif + dispatch ne casse pas
    sur une suite de requêtes liées.

    Objectif :
    - stabilité du routing
    - stabilité execution layer
    """
    k = KernelRunner()

    out = k.run_sync("je veux construire une maison")

    assert isinstance(out, str)