# tests/conftest.py
#
# Configuration pytest globale pour la suite de tests ARIA.
#
# Problème résolu :
#   Plusieurs tests instancient AriaKernel() directement, ce qui déclenche
#   de vrais appels httpx vers Groq / Mistral / Cerebras / Pollinations.
#   Sur CI ou offline, ça fait échouer les tests. En local, ça prend 60s+
#   pour des tests qui ne testent pas les providers LLM.
#
# Stratégie :
#   On mocke httpx.post à la racine — le seul point de sortie réseau
#   du LLMRouter. Toute la logique interne (routing table, fallback chain,
#   construction du prompt système, injection soul/user) continue de
#   s'exécuter. Seul l'appel réseau est intercepté.
#
#   httpx.get est également mocké pour couvrir Pollinations (génération image).
#
# Portée :
#   autouse=True → appliqué à TOUS les tests sans annotation explicite.
#   Les tests qui veulent des vrais appels (intégration end-to-end) doivent
#   utiliser le marker @pytest.mark.live et sont exclus via :
#       pytest tests/ -q -m "not live"
#
# Format de la fausse réponse :
#   Compatible avec le parsing de LLMRouter._call() :
#       data["choices"][0]["message"]["content"]

import pytest
import json
from unittest.mock import MagicMock, patch


# ── Réponse HTTP factice ──────────────────────────────────────────────────────

def _fake_llm_response(content: str = "réponse factice aria") -> MagicMock:
    """
    Construit un objet httpx.Response minimal compatible avec LLMRouter._call().

    Structure attendue par le parser :
        response.json() → {"choices": [{"message": {"content": "..."}}]}
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()   # ne lève rien
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    return mock_response


def _fake_image_response() -> MagicMock:
    """
    Réponse factice pour les appels httpx.get vers Pollinations.
    Retourne un PNG minimal (1x1 pixel) encodé en bytes.
    """
    # PNG 1x1 pixel transparent — valide pour les tests de pipeline
    PNG_1X1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    mock_response.content = PNG_1X1
    mock_response.headers = {"content-type": "image/png"}
    return mock_response


# ── Fixture globale ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_network(request):
    """
    Intercepte tous les appels réseau sortants dans la suite de tests.

    Exclure un test du mock :
        @pytest.mark.live
        def test_real_llm_call(): ...

    Puis lancer uniquement les tests live :
        pytest tests/ -m live -q
    """
    # Les tests marqués @pytest.mark.live passent sans mock
    if request.node.get_closest_marker("live"):
        yield
        return

    with patch("httpx.post", return_value=_fake_llm_response()) as mock_post, \
         patch("httpx.get",  return_value=_fake_image_response()) as mock_get:

        # Expose les mocks dans le namespace du test via request
        # Un test peut accéder à mock_post via la fixture mock_network
        yield {
            "post": mock_post,
            "get":  mock_get,
        }


# ── Marker live — déclaration pour éviter les warnings pytest ─────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: marque un test comme nécessitant de vrais providers LLM/réseau",
    )