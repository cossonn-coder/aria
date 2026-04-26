from core.event import Event, EventType
from cognition.cognitive_engine import CognitiveEngine
from cognition.cognitive_context import CognitiveOperation


def make_image_event(caption):
    return Event.create(
        event_type=EventType.IMAGE,
        user_id="42",
        content={"file_path": "/tmp/test.jpg", "caption": caption},
        metadata={},
    )


def test_photo_no_caption_routes_to_input():
    engine = CognitiveEngine(llm_router=None)
    result = engine.classify(make_image_event(caption=None))
    assert result.operation == CognitiveOperation.IMAGE_INPUT


def test_photo_descriptive_caption_routes_to_input():
    engine = CognitiveEngine(llm_router=None)
    result = engine.classify(make_image_event(caption="c'est ma courge"))
    assert result.operation == CognitiveOperation.IMAGE_INPUT


def test_photo_generation_caption_routes_to_generation():
    engine = CognitiveEngine(llm_router=None)
    result = engine.classify(make_image_event(caption="génère une version estivale"))
    assert result.operation == CognitiveOperation.IMAGE_GENERATION


def test_photo_draw_caption_routes_to_generation():
    engine = CognitiveEngine(llm_router=None)
    result = engine.classify(make_image_event(caption="dessine ça en aquarelle"))
    assert result.operation == CognitiveOperation.IMAGE_GENERATION