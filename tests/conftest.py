# tests/conftest.py
#
# Configuration pytest globale pour la suite de tests ARIA.
#
# Mocks actifs sur tous les tests (sauf @pytest.mark.live) :
#
#   httpx.post
#       → LLMRouter : bloque tous les appels providers texte
#
#   httpx.get
#       → Pollinations : bloque la génération image réseau
#
#   sentence_transformers.SentenceTransformer.__init__
#       → bloque le chargement du modèle (~15s par instanciation)
#         Le modèle all-MiniLM-L6-v2 est chargé depuis le disque
#         à chaque AriaKernel() — sans ce mock, la suite prend 60s+
#
#   embedding.embedder.Embedder.encode
#       → retourne un vecteur factice de dimension 384
#         compatible avec all-MiniLM-L6-v2
#
# Usage :
#   pytest tests/ -q              → tous les tests mockés (~5s)
#   pytest tests/ -m live -q      → tests avec vrais providers

import pytest
import numpy as np
from unittest.mock import MagicMock, patch


# ── Réponses factices ─────────────────────────────────────────────────────────

def _fake_llm_response(content: str = "réponse factice aria") -> MagicMock:
    """
    Réponse httpx compatible avec LLMRouter._call().
        response.json() → {"choices": [{"message": {"content": "..."}}]}
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return mock_response


def _fake_image_response() -> MagicMock:
    """
    Réponse httpx compatible avec Pollinations — PNG 1x1 pixel.
    """
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
    if request.node.get_closest_marker("live"):
        yield
        return

    # Vecteur factice dimension 384 (all-MiniLM-L6-v2)
    fake_vector = np.array([[0.1] * 384])

    with patch("httpx.post", return_value=_fake_llm_response()) as mock_post, \
         patch("httpx.get", return_value=_fake_image_response()) as mock_get, \
         patch("embedding.embedder.Embedder.__init__", return_value=None), \
         patch("embedding.embedder.Embedder.encode", return_value=np.array([[0.1] * 384])):

        yield {
            "post": mock_post,
            "get": mock_get,
        }

# ── Marker live ───────────────────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: marque un test comme nécessitant de vrais providers LLM/réseau",
    )
    config.addinivalue_line("markers", "integration: tests système complets — lents")