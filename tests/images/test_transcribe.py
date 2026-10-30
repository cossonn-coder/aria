# tests/images/test_transcribe.py
#
# Sprint 42, tronçon 03 : ImageRouter.transcribe (OCR par la chaîne vision).

from llm.image_router import ImageRouter


def _router(answer):
    class FakeVision:
        def describe(self, image, prompt):
            return answer

    return ImageRouter(vision_table=[{"provider": "fake", "client": lambda **kw: FakeVision()}])


def test_transcribe_returns_text():
    assert _router("Ligne 1\nLigne 2").transcribe("img.png") == "Ligne 1\nLigne 2"


def test_transcribe_no_text_returns_empty():
    assert _router("AUCUN TEXTE").transcribe("img.png") == ""
