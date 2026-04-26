from unittest.mock import MagicMock, patch
from execution.routers.image_router import ImageExecutionRouter, _inject_context
from images.image_types import ImageArtifact


# ── Tests unitaires _inject_context ─────────────────────────────────────────

def test_inject_context_empty_returns_prompt():
    assert _inject_context("mon jardin", "") == "mon jardin"

def test_inject_context_prepends_block():
    result = _inject_context("mon jardin", "Projets actifs :\n- jardin potager")
    assert result.startswith("[Contexte :")
    assert "mon jardin" in result
    assert "jardin potager" in result


# ── Tests intégration ImageExecutionRouter ───────────────────────────────────

def _make_router(intent_names=None, memories=None):
    """Construit un router avec mocks injectés."""
    internal = MagicMock()
    internal.generate.return_value = ImageArtifact(
        path="/tmp/out.png",
        caption="image générée",
        prompt="prompt enrichi",
    )

    intent_engine = None
    if intent_names is not None:
        intent_engine = MagicMock()
        intents = []
        for name in intent_names:
            i = MagicMock()
            i.name = name
            i.salience = 0.8
            intents.append(i)
        intent_engine.list_attention_active.return_value = intents

    bridge = None
    if memories is not None:
        bridge = MagicMock()
        bridge.retrieve_memories.return_value = memories

    return ImageExecutionRouter(
        internal_router=internal,
        intent_engine=intent_engine,
        mempalace_bridge=bridge,
    ), internal


def test_generation_without_context_passes_raw_prompt():
    router, internal = _make_router()
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({"op_type": "image_generation", "content": "dessine mon jardin", "metadata": {}})
    call_prompt = internal.generate.call_args[1]["message"]
    assert call_prompt == "dessine mon jardin"


def test_generation_with_intents_injects_context():
    router, internal = _make_router(intent_names=["jardin potager"])
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({"op_type": "image_generation", "content": "dessine mon jardin", "metadata": {}})
    call_prompt = internal.generate.call_args[1]["message"]
    assert "jardin potager" in call_prompt
    assert "dessine mon jardin" in call_prompt


def test_generation_with_memories_injects_context():
    router, internal = _make_router(memories=["Nico a planté des tomates en mars"])
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({"op_type": "image_generation", "content": "mon potager", "metadata": {}})
    call_prompt = internal.generate.call_args[1]["message"]
    assert "tomates" in call_prompt


def test_generation_memory_error_is_non_blocking():
    router, internal = _make_router(intent_names=["jardin"])
    router.mempalace_bridge = MagicMock()
    router.mempalace_bridge.retrieve_memories.side_effect = Exception("ChromaDB down")
    with patch("execution.routers.image_router.store_image_artifact"):
        # Ne doit pas lever
        result = router.execute({"op_type": "image_generation", "content": "test", "metadata": {}})
    assert result["path"] == "/tmp/out.png"