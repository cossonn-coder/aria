# tests/images/test_interrogative_vision_pipeline.py
#
# Tests du pipeline vision enrichi (sprint 0.1).
#
# Ce fichier couvre trois périmètres :
#
#   A. is_interrogative_caption() — heuristique classification caption
#      Vérifie que les vraies questions sont détectées et que les
#      captions descriptives ne déclenchent pas le mode enrichi.
#
#   B. CognitiveEngine.classify() — flag interrogative dans CognitiveResult
#      Vérifie que le flag est positionné correctement selon la caption.
#
#   C. ImageExecutionRouter — routing selon le mode détecté
#      Vérifie que :
#        - caption interrogative + llm_execution_router → pipeline enrichi appelé
#        - caption descriptive                          → description vision brute
#        - caption interrogative + pas de llm_router    → dégradation gracieuse
#
# Conventions mock :
#   - internal_router fake : retourne un artifact avec caption fixe
#   - llm_execution_router fake : retourne {"text": "réponse enrichie"}
#   - store_image_artifact patché pour ne pas toucher ChromaDB

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional

# ── Helpers locaux ────────────────────────────────────────────────────────────

@dataclass
class FakeArtifact:
    """ImageArtifact minimal pour les tests."""
    path: str = "/tmp/test.jpg"
    caption: str = "Des blocs de substrat brun foncé en fin de cycle."
    prompt: str = ""


def make_internal_router(caption: str = "Des blocs de substrat brun foncé.") -> MagicMock:
    """Fake internal_router (llm.image_router.ImageRouter)."""
    router = MagicMock()
    router.handle_input.return_value = FakeArtifact(caption=caption)
    router.generate.return_value = FakeArtifact(
        path="/tmp/generated.png",
        caption="generated",
    )
    return router


def make_llm_execution_router(response: str = "Réponse enrichie par la mémoire.") -> MagicMock:
    """Fake LLMExecutionRouter."""
    router = MagicMock()
    router.execute.return_value = {"text": response}
    return router


# ── A. is_interrogative_caption() ────────────────────────────────────────────

class TestIsInterrogativeCaption:

    def _call(self, caption):
        from cognition.cognitive_classifier import is_interrogative_caption
        return is_interrogative_caption(caption)

    # Positifs évidents
    def test_point_dinterrogation(self):
        assert self._call("c'est quoi ?") is True

    def test_quest_ce_que_cest(self):
        assert self._call("qu'est-ce que c'est ?") is True

    def test_tu_reconnais(self):
        assert self._call("tu reconnais ?") is True

    def test_kesako(self):
        assert self._call("kesako") is True

    def test_what_is(self):
        assert self._call("what is this?") is True

    def test_point_dinterrogation_seul(self):
        assert self._call("?") is True

    def test_cest_quoi_ca(self):
        assert self._call("c'est quoi ça") is True

    def test_tu_sais_ce_que_cest(self):
        assert self._call("tu sais ce que c'est ?") is True

    # Négatifs — captions descriptives
    def test_none(self):
        assert self._call(None) is False

    def test_chaine_vide(self):
        assert self._call("") is False

    def test_caption_descriptive(self):
        assert self._call("substrats de shiitakes usés") is False

    def test_caption_jardin(self):
        assert self._call("jardin 2024") is False

    def test_caption_photo(self):
        assert self._call("photo du verger") is False

    def test_caption_longue_descriptive(self):
        assert self._call("les blocs de mycélium après la troisième récolte") is False

    # Ambiguïtés
    def test_phrase_avec_point_dinterrogation_integre(self):
        # "tu vois quoi ?" → interrogative
        assert self._call("tu vois quoi ?") is True

    def test_caption_generation_pas_interrogative(self):
        # "transforme en aquarelle" → génération, pas interrogatif
        assert self._call("transforme en aquarelle") is False

    def test_casse_insensible(self):
        assert self._call("C'EST QUOI ?") is True


# ── B. CognitiveEngine.classify() ─────────────────────────────────────────────

class TestCognitiveEngineInterrogativeFlag:

    def _engine(self):
        from cognition.cognitive_engine import CognitiveEngine
        return CognitiveEngine(llm_router=None)

    def _image_event(self, caption: Optional[str]):
        from core.event import Event, EventType
        return Event.create(
            event_type=EventType.IMAGE,
            user_id="test",
            content={"file_path": "/tmp/img.jpg", "caption": caption},
            metadata={},
        )

    def test_caption_interrogative_flag_true(self):
        engine = self._engine()
        result = engine.classify(self._image_event("c'est quoi ?"))
        assert result.interrogative is True

    def test_caption_descriptive_flag_false(self):
        engine = self._engine()
        result = engine.classify(self._image_event("substrats de shiitakes usés"))
        assert result.interrogative is False

    def test_caption_none_flag_false(self):
        engine = self._engine()
        result = engine.classify(self._image_event(None))
        assert result.interrogative is False

    def test_operation_toujours_image_input(self):
        from cognition.cognitive_context import CognitiveOperation
        engine = self._engine()
        result = engine.classify(self._image_event("c'est quoi ?"))
        assert result.operation == CognitiveOperation.IMAGE_INPUT

    def test_caption_generation_reste_image_generation(self):
        from cognition.cognitive_context import CognitiveOperation
        engine = self._engine()
        result = engine.classify(self._image_event("transforme en aquarelle"))
        assert result.operation == CognitiveOperation.IMAGE_GENERATION
        assert result.interrogative is False


# ── C. ImageExecutionRouter — routing selon le mode ───────────────────────────

class TestImageRouterEnrichedMode:
    """
    Tests du routing IMAGE_INPUT selon la caption.

    store_image_artifact est patché globalement pour éviter ChromaDB.
    """

    VISION_DESCRIPTION = "Des blocs de substrat brun foncé en fin de cycle."
    ENRICHED_RESPONSE  = "Ces substrats usés sont des blocs de mycélium shiitaké épuisés."

    def _router(self, with_llm_router: bool = True, vision_caption: str = None):
        from execution.routers.image_router import ImageExecutionRouter
        internal  = make_internal_router(caption=vision_caption or self.VISION_DESCRIPTION)
        llm_exec  = make_llm_execution_router(self.ENRICHED_RESPONSE) if with_llm_router else None
        return ImageExecutionRouter(
            internal_router=internal,
            llm_execution_router=llm_exec,
        ), internal, llm_exec

    def _payload(self, caption: Optional[str]) -> dict:
        return {
            "op_type" : "image_input",
            "content" : {"file_path": "/tmp/img.jpg", "caption": caption},
            "metadata": {},
        }

    # Mode enrichi activé
    @patch("execution.routers.image_router.write_image_artifact")
    def test_caption_interrogative_appelle_llm_router(self, mock_store):
        router, internal, llm_exec = self._router(with_llm_router=True)
        result = router.execute(self._payload("c'est quoi ?"))

        assert llm_exec is not None
        llm_exec.execute.assert_called_once()
        call_payload = llm_exec.execute.call_args[0][0]
        assert call_payload["op_type"] == "reasoning"
        assert self.VISION_DESCRIPTION in call_payload["content"]
        assert "c'est quoi ?" in call_payload["content"]

    @patch("execution.routers.image_router.write_image_artifact")
    def test_caption_interrogative_retourne_reponse_enrichie(self, mock_store):
        router, _, _ = self._router(with_llm_router=True)
        result = router.execute(self._payload("c'est quoi ?"))
        assert result == {"text": self.ENRICHED_RESPONSE}

    # Mode standard — caption descriptive
    @patch("execution.routers.image_router.write_image_artifact")
    def test_caption_descriptive_retourne_vision_brute(self, mock_store):
        router, internal, llm_exec = self._router(with_llm_router=True)
        result = router.execute(self._payload("substrats de shiitakes usés"))

        assert result == {"text": self.VISION_DESCRIPTION}
        # LLM router ne doit PAS être appelé
        assert llm_exec is not None
        llm_exec.execute.assert_not_called()

    # Mode standard — caption absente
    @patch("execution.routers.image_router.write_image_artifact")
    def test_caption_none_retourne_vision_brute(self, mock_store):
        router, _, llm_exec = self._router(with_llm_router=True)
        result = router.execute(self._payload(None))

        assert result == {"text": self.VISION_DESCRIPTION}
        assert llm_exec is not None
        llm_exec.execute.assert_not_called()

    # Dégradation gracieuse — pas de llm_execution_router
    @patch("execution.routers.image_router.write_image_artifact")
    def test_sans_llm_router_retourne_vision_brute(self, mock_store):
        router, _, _ = self._router(with_llm_router=False)
        result = router.execute(self._payload("c'est quoi ?"))
        assert result == {"text": self.VISION_DESCRIPTION}

    # Dégradation gracieuse — vision retourne une description vide
    @patch("execution.routers.image_router.write_image_artifact")
    def test_vision_vide_pas_dappel_llm(self, mock_store):
        """Si la description vision est vide, on ne passe pas au pipeline enrichi."""
        from execution.routers.image_router import ImageExecutionRouter
        internal = make_internal_router(caption="")
        llm_exec = make_llm_execution_router()
        router = ImageExecutionRouter(
            internal_router=internal,
            llm_execution_router=llm_exec,
        )
        result = router.execute(self._payload("c'est quoi ?"))
        # Vision vide → pas d'enrichissement possible
        llm_exec.execute.assert_not_called()
        assert result == {"text": ""}

    # Contrat sortie : toujours {"text": str}
    @patch("execution.routers.image_router.write_image_artifact")
    def test_contrat_sortie_text_key(self, mock_store):
        router, _, _ = self._router(with_llm_router=True)
        result_interro  = router.execute(self._payload("c'est quoi ?"))
        result_standard = router.execute(self._payload("photo du jardin"))
        assert "text" in result_interro
        assert "text" in result_standard
        assert "path" not in result_interro
        assert "path" not in result_standard

    # Message enrichi injecté dans LLMExecutionRouter
    @patch("execution.routers.image_router.write_image_artifact")
    def test_message_enrichi_contient_analyse_visuelle(self, mock_store):
        router, _, llm_exec = self._router(with_llm_router=True)
        router.execute(self._payload("qu'est-ce que c'est ?"))

        call_payload = llm_exec.execute.call_args[0][0]
        assert "[Analyse visuelle :" in call_payload["content"]

    # Mémoire toujours écrite
    @patch("execution.routers.image_router.write_image_artifact")
    def test_artifact_stocke_meme_mode_enrichi(self, mock_store):
        router, _, _ = self._router(with_llm_router=True)
        router.execute(self._payload("c'est quoi ?"))
        mock_store.assert_called_once()