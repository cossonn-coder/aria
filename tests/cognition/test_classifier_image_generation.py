# Tests sprint 24 tronçon 01 : mots-clés de génération image resserrés.

from cognition.cognitive_classifier import classify_operation
from cognition.cognitive_context import CognitiveOperation


def test_afficher_is_not_image_generation():
    result = classify_operation("tu peux afficher la liste des courses ?")
    assert result != CognitiveOperation.IMAGE_GENERATION


def test_dessine_is_image_generation():
    assert classify_operation("dessine un chat") == CognitiveOperation.IMAGE_GENERATION
