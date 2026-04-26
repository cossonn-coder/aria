# test/images/test_image_generation_kernel.py
#
# 🔷 ARCHITECTURE UPDATE (ARIA CORE REFACTOR)
# ------------------------------------------------------------
# Le Kernel n’expose plus handle_message().
# Le point d’entrée unique est désormais :
#
#   AriaKernel.handle_event(Event)
#
# Le système est event-driven et multimodal :
#   TEXT → Event(type=TEXT)
#   IMAGE → Event(type=IMAGE)
#
# Ce test vérifie uniquement la chaîne IMAGE GENERATION
# via un Event TEXT contenant une requête de génération.

import asyncio

from core.kernel import AriaKernel
from tests.utils.event_factory import make_text_event


# ---------------------------------------------------------------------
# Image generation integration test
# ---------------------------------------------------------------------
# Objectif :
# - vérifier que la requête texte déclenche un pipeline image
# - valider que le résultat final est un fichier image
# - garantir que le router image est correctement branché
#
# Attention :
# - ce test ne valide PAS le contenu de l’image
# - il valide uniquement le contrat de sortie (path image)

def test_image_generation_kernel():

    k = AriaKernel()

    event = make_text_event("dessine un robot dans un jardin")

    res = asyncio.run(
        k.handle_event(event)
    )

    # -----------------------------------------------------------------
    # Normalisation attendue :
    # - soit string (fallback texte)
    # - soit dict image {"type": "image", "path": ...}
    # -----------------------------------------------------------------

    assert isinstance(res, (str, dict))

    if isinstance(res, dict):
        assert res.get("type") == "image"
        assert res.get("path", "").endswith(".png")
    else:
        # fallback sécurité si pipeline ne déclenche pas l’image
        assert res.endswith(".png")