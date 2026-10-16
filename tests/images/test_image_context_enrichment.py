# tests/images/test_image_context_enrichment.py
#
# Tests de la génération image côté ImageExecutionRouter.
#
# Depuis le sprint 24, le prompt de génération est le message brut :
# aucun bloc de contexte (intents, souvenirs) n'y est injecté.

from unittest.mock import MagicMock, patch
from execution.routers.image_router import ImageExecutionRouter
from images.image_types import ImageArtifact


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_router(intent_names=None, memories=None):
    """
    Construit un ImageExecutionRouter avec dépendances mockées.

    Args:
        intent_names : liste de noms d'intents à simuler (None = pas d'intent engine)
        memories     : liste de strings de souvenirs à retourner par le bridge.
                       Le bridge mock retourne le format dict standard
                       {"hits": [{"text": ...}], "count": N}.
    """
    # Artifact factice retourné par internal_router.generate()
    internal = MagicMock()
    internal.generate.return_value = ImageArtifact(
        source="generated",
        path="/tmp/out.png",
        caption="image générée",
        prompt="prompt enrichi",
        intent_id=None,
        timestamp=None,
        metadata={},
    )

    # Intent engine mock
    intent_engine = None
    if intent_names is not None:
        intent_engine = MagicMock()
        intents = []
        for name in intent_names:
            i = MagicMock()
            i.name     = name
            i.salience = 0.8
            intents.append(i)
        intent_engine.list_attention_active.return_value = intents

    # Bridge mock — retourne le format dict standard {"hits": [...], "count": N}
    bridge = None
    if memories is not None:
        bridge = MagicMock()
        bridge.retrieve_memories.return_value = {
            "hits"  : [{"text": m} for m in memories],
            "count" : len(memories),
        }

    return ImageExecutionRouter(
        internal_router=internal,
        intent_engine=intent_engine,
        mempalace_bridge=bridge,
    ), internal


# ── Tests intégration ImageExecutionRouter ────────────────────────────────────

def test_generation_without_context_passes_raw_prompt():
    """
    Sans intent engine ni bridge, le prompt brut doit être passé sans modification.
    """
    router, internal = _make_router()
    with patch("execution.routers.image_router.write_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "dessine mon jardin",
            "metadata" : {},
        })
    call_prompt = internal.generate.call_args[1]["message"]
    assert call_prompt == "dessine mon jardin"


def test_generation_with_intents_and_memories_passes_raw_prompt():
    """
    Avec intents actifs et souvenirs disponibles, le prompt passé à
    generate reste exactement le message brut (pas de bloc contexte).
    """
    router, internal = _make_router(
        intent_names=["jardin potager"],
        memories=["Nico a planté des tomates en mars"],
    )
    with patch("execution.routers.image_router.write_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "dessine mon jardin",
            "metadata" : {},
        })
    assert internal.generate.call_args[1]["message"] == "dessine mon jardin"


def test_generation_result_contains_path_and_caption():
    """
    Le résultat de _handle_generation doit contenir path et caption
    pour que _normalize() du kernel route correctement vers send_photo().
    """
    router, internal = _make_router()
    with patch("execution.routers.image_router.write_image_artifact"):
        result = router.execute({
            "op_type"  : "image_generation",
            "content"  : "test",
            "metadata" : {},
        })
    assert "path"    in result
    assert "caption" in result
    assert result["path"].endswith(".png")