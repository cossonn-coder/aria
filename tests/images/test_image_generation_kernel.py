# tests/images/test_image_generation_kernel.py
#
# Test d'intégration : génération image via le pipeline kernel complet.
#
# Objectif :
#   Vérifier que le kernel classifie correctement une requête de génération
#   image et produit un résultat normalisé {"type": "image", "path": ...}.
#
# Ce qu'on teste ici :
#   - classify_operation() → IMAGE_GENERATION
#   - routing → image_router
#   - _normalize() → dict {"type": "image", "path": ...}
#
# Ce qu'on NE teste PAS ici :
#   - le contenu de l'image générée
#   - les providers réels (Pollinations, HuggingFace)
#
# Stratégie de mock :
#   On mocke uniquement _handle_generation() — la couche d'appel provider.
#   Le pipeline complet (kernel → classify → dispatch → image_router) reste réel.
#   Cela évite deux problèmes connus :
#     1. Pollinations rejette les URLs contenant des \n (prompt enrichi multi-lignes)
#     2. conftest.py mocke httpx globalement → HuggingFace reçoit un MagicMock
#        à la place de bytes, ce qui lève memoryview: a bytes-like object required.
#
# Note : le bug Pollinations (\n dans l'URL) doit aussi être corrigé dans
# llm/image_gen/pollinations_client.py via urllib.parse.quote(prompt).
# Ce test ne dépend pas de ce fix pour passer.

import asyncio
from unittest.mock import patch, MagicMock

from core.kernel import AriaKernel
from tests.utils.event_factory import make_text_event


# ── Constantes ───────────────────────────────────────────────────────────────

# Résultat factice retourné par _handle_generation mocké.
# path doit se terminer par .png pour que _normalize() détecte un résultat image.
FAKE_GENERATION_RESULT = {
    "path"    : "/tmp/aria_test_robot.png",
    "caption" : "un robot dans un jardin",
}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_image_generation_kernel():
    """
    Le kernel doit classifier "dessine un robot dans un jardin" comme
    IMAGE_GENERATION et retourner un dict {"type": "image", "path": ...}.

    Pipeline réel :
        make_text_event() → AriaKernel.handle_event()
          → CognitiveEngine.classify() → IMAGE_GENERATION
          → ExecutionDispatcher → image_router
          → ImageExecutionRouter._handle_generation()  ← mocké ici
          → _normalize() → {"type": "image", "path": ..., "caption": ...}
    """
    k     = AriaKernel()
    event = make_text_event("dessine un robot dans un jardin")

    # On mocke uniquement la couche d'appel provider, pas le routing.
    # patch.object cible l'instance déjà câblée dans le kernel — pas la classe.
    image_router = k.execution_dispatcher.registry["image_router"]

    with patch.object(
        image_router,
        "_handle_generation",
        return_value=FAKE_GENERATION_RESULT,
    ):
        res = asyncio.run(k.handle_event(event))

    # _normalize() doit détecter le path .png et retourner un dict image
    assert isinstance(res, dict), (
        f"Résultat inattendu : {res!r}. "
        "Le kernel doit retourner un dict image pour IMAGE_GENERATION."
    )
    assert res.get("type") == "image", (
        f"res['type'] = {res.get('type')!r} — attendu 'image'."
    )
    assert res.get("path", "").endswith(".png"), (
        f"res['path'] = {res.get('path')!r} — doit se terminer par .png."
    )


def test_image_generation_kernel_fallback_on_provider_error():
    """
    Si _handle_generation lève une exception (provider indisponible),
    le kernel doit retourner une string d'erreur sans crasher.

    Vérifie la robustesse du pipeline face aux pannes provider.
    """
    k     = AriaKernel()
    event = make_text_event("dessine une forêt en automne")

    image_router = k.execution_dispatcher.registry["image_router"]

    with patch.object(
        image_router,
        "_handle_generation",
        side_effect=Exception("All providers failed"),
    ):
        res = asyncio.run(k.handle_event(event))

    # Le kernel doit absorber l'erreur et retourner une string (message neutre)
    assert isinstance(res, str), (
        f"Le kernel doit retourner une string en cas d'erreur provider, "
        f"got: {res!r}"
    )