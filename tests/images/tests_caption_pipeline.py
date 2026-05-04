# tests/images/test_caption_pipeline.py
#
# Vérifie que la caption utilisateur traverse correctement le pipeline
# depuis ImageInput jusqu'au prompt soumis au modèle de vision.
#
# Régression couverte :
#   Avant le fix, la caption était extraite dans ImageExecutionRouter
#   mais jamais transmise à ImageInput ni au modèle de vision.
#   Le modèle produisait une description générique sans contexte.
#
# Ce qu'on teste ici :
#   - ImageInput accepte et conserve une caption
#   - ImageRouter construit un prompt contextualisé si caption présente
#   - ImageRouter construit un prompt générique si caption absente
#   - ImageExecutionRouter transmet la caption à ImageInput
#   - La caption utilisateur n'écrase pas la description vision dans la réponse

import pytest
from unittest.mock import MagicMock, patch, call

from images.image_types import ImageInput, ImageArtifact
from llm.image_router import ImageRouter
from execution.routers.image_router import ImageExecutionRouter


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_fake_vision_client(description: str = "description vision"):
    """
    Client vision factice — retourne une description fixe sans appel réseau.
    Permet d'inspecter le prompt reçu.
    """
    client = MagicMock()
    client.describe.return_value = description
    return client


def make_vision_table(client) -> list:
    """Routing table vision minimaliste avec un seul provider fake."""
    return [{
        "provider": "fake_vision",
        "client": lambda **_: client,
    }]


def make_image_router(vision_client) -> ImageRouter:
    """ImageRouter câblé sur un client vision fake, pas de génération."""
    return ImageRouter(
        vision_table=make_vision_table(vision_client),
        generation_table=[],
    )


# ── Tests : ImageInput ────────────────────────────────────────────────────────

class TestImageInput:

    def test_caption_field_exists_and_defaults_to_none(self):
        """
        ImageInput doit avoir un champ caption initialisé à None.

        Garantit la rétrocompatibilité : tout code qui crée un ImageInput
        sans caption continue de fonctionner.
        """
        img = ImageInput(path="/tmp/photo.jpg")
        assert img.caption is None

    def test_caption_stored_correctly(self):
        """
        La caption passée à ImageInput doit être accessible en lecture.
        """
        img = ImageInput(path="/tmp/photo.jpg", caption="c'est ma courge de mars")
        assert img.caption == "c'est ma courge de mars"

    def test_all_fields_coexist(self):
        """ImageInput peut porter path, source et caption simultanément."""
        img = ImageInput(
            path="/tmp/photo.jpg",
            source="input",
            caption="contexte utilisateur",
        )
        assert img.path == "/tmp/photo.jpg"
        assert img.source == "input"
        assert img.caption == "contexte utilisateur"


# ── Tests : ImageRouter — construction du prompt ──────────────────────────────

class TestImageRouterPrompt:

    def test_prompt_is_generic_without_caption(self):
        """
        Sans caption, le prompt vision doit être générique.

        Le modèle doit décrire librement ce qu'il voit.
        """
        client = make_fake_vision_client()
        router = make_image_router(client)

        router.handle_input(ImageInput(path="/tmp/photo.jpg"))

        call_kwargs = client.describe.call_args
        prompt_used = call_kwargs[1].get("prompt") or call_kwargs[0][1]

        # Vérifie qu'on ne mentionne pas de contexte utilisateur inexistant
        assert "L'utilisateur" not in prompt_used
        assert "message" not in prompt_used.lower()

    def test_prompt_is_contextualized_with_caption(self):
        """
        Avec une caption, le prompt vision doit l'intégrer explicitement.

        Le modèle doit savoir ce que l'utilisateur cherche à montrer
        pour orienter son analyse.
        """
        client = make_fake_vision_client()
        router = make_image_router(client)

        router.handle_input(ImageInput(
            path="/tmp/photo.jpg",
            caption="c'est la courge plantée en mars",
        ))

        call_kwargs = client.describe.call_args
        prompt_used = call_kwargs[1].get("prompt") or call_kwargs[0][1]

        assert "c'est la courge plantée en mars" in prompt_used

    def test_prompt_contains_user_framing_instruction(self):
        """
        Le prompt contextualisé doit demander au modèle de tenir compte
        du message utilisateur — pas juste le citer.
        """
        client = make_fake_vision_client()
        router = make_image_router(client)

        router.handle_input(ImageInput(
            path="/tmp/photo.jpg",
            caption="est-ce que cette plante est en bonne santé ?",
        ))

        call_kwargs = client.describe.call_args
        prompt_used = call_kwargs[1].get("prompt") or call_kwargs[0][1]

        # Le prompt doit demander une analyse orientée, pas une description brute
        assert "contexte" in prompt_used.lower() or "compte" in prompt_used.lower()

    def test_artifact_caption_is_vision_description(self):
        """
        L'artifact retourné doit contenir la description du modèle vision,
        pas la caption utilisateur.

        La caption utilisateur est un input — la description vision est l'output.
        """
        client = make_fake_vision_client("une belle courge bien verte")
        router = make_image_router(client)

        artifact = router.handle_input(ImageInput(
            path="/tmp/photo.jpg",
            caption="c'est ma courge",
        ))

        assert artifact.caption == "une belle courge bien verte"

    def test_user_caption_preserved_in_metadata(self):
        """
        La caption originale de l'utilisateur doit être conservée
        dans les métadonnées de l'artifact — pour le stockage mémoire.
        """
        client = make_fake_vision_client("description vision")
        router = make_image_router(client)

        artifact = router.handle_input(ImageInput(
            path="/tmp/photo.jpg",
            caption="contexte important",
        ))

        assert artifact.metadata.get("user_caption") == "contexte important"


# ── Tests : ImageExecutionRouter — transmission de la caption ─────────────────

class TestImageExecutionRouterCaption:

    def _make_router_with_capture(self):
        """
        Construit un ImageExecutionRouter dont l'internal_router
        capture l'ImageInput reçu pour inspection.
        """
        internal = MagicMock()
        captured = {}

        def capture_input(image_input: ImageInput):
            captured["image_input"] = image_input
            return ImageArtifact(
                source="input",
                path="/tmp/photo.jpg",
                caption="description capturée",
                metadata={"user_caption": image_input.caption or ""},
            )

        internal.handle_input.side_effect = capture_input

        return ImageExecutionRouter(internal_router=internal), captured

    @patch("execution.routers.image_router.write_image_artifact")
    def test_caption_transmitted_to_image_input(self, mock_write):
        """
        ImageExecutionRouter doit transmettre la caption de l'Event
        à ImageInput — pour que ImageRouter puisse contextualiser le prompt.

        C'est le fix principal du bug : avant, caption était perdue ici.
        """
        router, captured = self._make_router_with_capture()

        router.execute({
            "op_type": "image_input",
            "content": {
                "file_path": "/tmp/photo.jpg",
                "caption": "ma courge du jardin",
            },
            "metadata": {},
        })

        assert captured["image_input"].caption == "ma courge du jardin", (
            "La caption utilisateur n'est pas transmise à ImageInput. "
            "Régression du fix caption."
        )

    @patch("execution.routers.image_router.write_image_artifact")
    def test_none_caption_transmitted_as_none(self, mock_write):
        """
        Si l'Event ne contient pas de caption, ImageInput.caption doit être None.
        Pas de chaîne vide, pas de valeur par défaut silencieuse.
        """
        router, captured = self._make_router_with_capture()

        router.execute({
            "op_type": "image_input",
            "content": {
                "file_path": "/tmp/photo.jpg",
                "caption": None,
            },
            "metadata": {},
        })

        assert captured["image_input"].caption is None