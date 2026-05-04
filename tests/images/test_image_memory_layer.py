# tests/images/test_image_memory_storage.py
#
# Vérifie que ImageExecutionRouter stocke correctement les artefacts
# image en mémoire épisodique après traitement.
#
# Contexte :
#   Avant sprint 1.1, les images étaient analysées ou générées puis
#   envoyées à Telegram — sans aucune trace en mémoire.
#   ARIA ne se souvenait pas avoir vu ou produit une image.
#
# Ce qu'on teste :
#   - store_image_artifact est appelé après IMAGE_INPUT
#   - store_image_artifact est appelé après IMAGE_GENERATION
#   - l'artifact transmis contient les bonnes données
#   - une erreur mémoire n'interrompt pas la réponse à l'utilisateur
#   - l'intent_id est transmis depuis le payload

import pytest
from unittest.mock import MagicMock, patch, call

from execution.routers.image_router import ImageExecutionRouter
from images.image_types import ImageArtifact


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_artifact(source: str, path: str, caption: str = None, prompt: str = None) -> ImageArtifact:
    from datetime import datetime, timezone
    return ImageArtifact(
        source=source,
        path=path,
        caption=caption,
        prompt=prompt,
        intent_id=None,
        timestamp=datetime.now(timezone.utc),
        metadata={"user_caption": ""},
    )


def make_router(input_artifact=None, generated_artifact=None) -> ImageExecutionRouter:
    """
    ImageExecutionRouter avec internal_router mocké.

    input_artifact    : artifact retourné par handle_input()
    generated_artifact: artifact retourné par generate()
    """
    internal = MagicMock()

    internal.handle_input.return_value = input_artifact or make_artifact(
        source="input",
        path="/tmp/received.jpg",
        caption="description vision",
    )
    internal.generate.return_value = generated_artifact or make_artifact(
        source="generated",
        path="/tmp/generated.png",
        prompt="un jardin en été",
    )

    return ImageExecutionRouter(internal_router=internal)


# ── Tests : IMAGE_INPUT — stockage mémoire ────────────────────────────────────

class TestImageInputMemoryStorage:

    @patch("execution.routers.image_router.write_image_artifact")
    def test_store_called_after_image_input(self, mock_store):
        """
        store_image_artifact doit être appelé une fois après analyse d'image.

        C'est la garantie que les images reçues sont mémorisées.
        """
        router = make_router()

        router.execute({
            "op_type": "image_input",
            "content": {"file_path": "/tmp/photo.jpg", "caption": None},
            "metadata": {},
        })

        assert mock_store.call_count == 1

    @patch("execution.routers.image_router.write_image_artifact")
    def test_store_receives_correct_artifact(self, mock_store):
        """
        L'artifact transmis à store_image_artifact doit être celui
        retourné par internal_router.handle_input() — pas une copie modifiée.
        """
        artifact = make_artifact(
            source="input",
            path="/tmp/photo.jpg",
            caption="belle courge verte",
        )
        router = make_router(input_artifact=artifact)

        router.execute({
            "op_type": "image_input",
            "content": {"file_path": "/tmp/photo.jpg", "caption": "ma courge"},
            "metadata": {},
        })

        stored_artifact = mock_store.call_args[0][0]
        assert stored_artifact is artifact

    @patch("execution.routers.image_router.write_image_artifact")
    def test_intent_id_transmitted_to_store(self, mock_store):
        """
        L'intent_id du payload doit être transmis à store_image_artifact
        pour que l'image soit rattachée au bon projet en mémoire.
        """
        router = make_router()

        router.execute({
            "op_type": "image_input",
            "content": {"file_path": "/tmp/photo.jpg", "caption": None},
            "metadata": {"intent_id": "intent-jardin-42"},
        })

        call_kwargs = mock_store.call_args
        intent_id_passed = call_kwargs[1].get("intent_id") or call_kwargs[0][1]
        assert intent_id_passed == "intent-jardin-42"

    @patch("execution.routers.image_router.write_image_artifact")
    def test_memory_error_does_not_crash_response(self, mock_store):
        """
        Si store_image_artifact lève une exception (ChromaDB down),
        la réponse doit quand même être retournée à l'utilisateur.

        La mémoire est best-effort — elle ne doit jamais bloquer l'UX.
        """
        mock_store.side_effect = Exception("ChromaDB unavailable")
        router = make_router()

        result = router.execute({
            "op_type": "image_input",
            "content": {"file_path": "/tmp/photo.jpg", "caption": None},
            "metadata": {},
        })

        # Le résultat doit quand même être présent
        assert "text" in result or "caption" in result

    @patch("execution.routers.image_router.write_image_artifact")
    def test_response_contains_vision_description(self, mock_store):
        """
        La réponse retournée doit contenir la description du modèle vision,
        pas la caption brute de l'utilisateur.
        """
        artifact = make_artifact(
            source="input",
            path="/tmp/photo.jpg",
            caption="analyse détaillée de la courge",
        )
        router = make_router(input_artifact=artifact)

        result = router.execute({
            "op_type": "image_input",
            "content": {"file_path": "/tmp/photo.jpg", "caption": "ma courge"},
            "metadata": {},
        })

        assert "analyse détaillée de la courge" in (result.get("text") or result.get("caption") or "")


# ── Tests : IMAGE_GENERATION — stockage mémoire ───────────────────────────────

class TestImageGenerationMemoryStorage:

    @patch("execution.routers.image_router.write_image_artifact")
    def test_store_called_after_generation(self, mock_store):
        """
        store_image_artifact doit être appelé après chaque génération.

        Les images générées doivent être mémorisées pour être
        retrouvables ("montre-moi les images de mon jardin").
        """
        router = make_router()

        router.execute({
            "op_type": "image_generation",
            "content": "génère un jardin potager",
            "metadata": {},
        })

        assert mock_store.call_count == 1

    @patch("execution.routers.image_router.write_image_artifact")
    def test_generated_artifact_has_correct_source(self, mock_store):
        """L'artifact d'une image générée doit avoir source='generated'."""
        artifact = make_artifact(
            source="generated",
            path="/tmp/generated.png",
            prompt="un jardin en été",
        )
        router = make_router(generated_artifact=artifact)

        router.execute({
            "op_type": "image_generation",
            "content": "un jardin en été",
            "metadata": {},
        })

        stored_artifact = mock_store.call_args[0][0]
        assert stored_artifact.source == "generated"

    @patch("execution.routers.image_router.write_image_artifact")
    def test_generation_memory_error_does_not_crash(self, mock_store):
        """
        Une erreur mémoire pendant la génération ne doit pas crasher.
        L'image générée doit quand même être retournée.
        """
        mock_store.side_effect = Exception("ChromaDB down")
        router = make_router()

        result = router.execute({
            "op_type": "image_generation",
            "content": "un jardin",
            "metadata": {},
        })

        assert "path" in result

    @patch("execution.routers.image_router.write_image_artifact")
    def test_intent_id_transmitted_for_generation(self, mock_store):
        """L'intent_id est transmis pour lier l'image générée à un projet."""
        router = make_router()

        router.execute({
            "op_type": "image_generation",
            "content": "un potager",
            "metadata": {"intent_id": "intent-maison-7"},
        })

        call_kwargs = mock_store.call_args
        intent_id_passed = call_kwargs[1].get("intent_id") or call_kwargs[0][1]
        assert intent_id_passed == "intent-maison-7"