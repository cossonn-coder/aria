# tests/images/test_image_context_enrichment.py
#
# Tests du pipeline d'enrichissement contextuel de la génération image.
#
# Ce qu'on vérifie :
#   - _inject_context() : logique d'injection prompt/contexte
#   - _build_generation_context() : assemblage intents + mémoire
#   - ImageExecutionRouter._handle_generation() : pipeline complet
#
# Stratégie de mock :
#   Le bridge est injecté directement dans le router (MagicMock).
#   bridge.retrieve_memories doit retourner le format dict standard :
#     {"hits": [{"text": "..."}], "count": N}
#   et NON une liste brute — _build_generation_context appelle .get("hits").

from unittest.mock import MagicMock, patch
from execution.routers.image_router import ImageExecutionRouter, _inject_context
from images.image_types import ImageArtifact


# ── Tests unitaires _inject_context ─────────────────────────────────────────

def test_inject_context_empty_returns_prompt():
    """Un contexte vide ne doit pas modifier le prompt."""
    assert _inject_context("mon jardin", "") == "mon jardin"


def test_inject_context_prepends_block():
    """Un contexte non vide doit être préfixé au prompt sous forme de bloc."""
    result = _inject_context("mon jardin", "Projets actifs :\n- jardin potager")
    assert result.startswith("[Contexte :")
    assert "mon jardin"     in result
    assert "jardin potager" in result


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
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "dessine mon jardin",
            "metadata" : {},
        })
    call_prompt = internal.generate.call_args[1]["message"]
    assert call_prompt == "dessine mon jardin"


def test_generation_with_intents_injects_context():
    """
    Le nom des intents actifs doit apparaître dans le prompt enrichi.
    """
    router, internal = _make_router(intent_names=["jardin potager"])
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "dessine mon jardin",
            "metadata" : {},
        })
    call_prompt = internal.generate.call_args[1]["message"]
    assert "jardin potager"   in call_prompt
    assert "dessine mon jardin" in call_prompt


def test_generation_with_memories_injects_context():
    """
    Le contenu des souvenirs pertinents doit apparaître dans le prompt enrichi.

    Le bridge retourne {"hits": [{"text": "..."}], "count": N}.
    _build_generation_context lit hits[n]["text"] pour construire le bloc contexte.
    """
    router, internal = _make_router(memories=["Nico a planté des tomates en mars"])
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "mon potager",
            "metadata" : {},
        })
    call_prompt = internal.generate.call_args[1]["message"]
    assert "tomates" in call_prompt


def test_generation_memory_error_is_non_blocking():
    """
    Une erreur du bridge (ex: ChromaDB indisponible) ne doit pas bloquer
    la génération. Le prompt brut est utilisé à la place du prompt enrichi.
    """
    router, internal = _make_router(intent_names=["jardin"])
    router.mempalace_bridge = MagicMock()
    router.mempalace_bridge.retrieve_memories.side_effect = Exception("ChromaDB down")

    with patch("execution.routers.image_router.store_image_artifact"):
        result = router.execute({
            "op_type"  : "image_generation",
            "content"  : "test",
            "metadata" : {},
        })

    assert result["path"] == "/tmp/out.png"


def test_generation_with_empty_memories_passes_raw_prompt():
    """
    Un bridge retournant zéro souvenir ne doit pas injecter de bloc vide.
    Le prompt original doit être transmis intact.
    """
    router, internal = _make_router(memories=[])
    with patch("execution.routers.image_router.store_image_artifact"):
        router.execute({
            "op_type"  : "image_generation",
            "content"  : "dessine une forêt",
            "metadata" : {},
        })
    call_prompt = internal.generate.call_args[1]["message"]
    assert call_prompt == "dessine une forêt"


def test_generation_result_contains_path_and_caption():
    """
    Le résultat de _handle_generation doit contenir path et caption
    pour que _normalize() du kernel route correctement vers send_photo().
    """
    router, internal = _make_router()
    with patch("execution.routers.image_router.store_image_artifact"):
        result = router.execute({
            "op_type"  : "image_generation",
            "content"  : "test",
            "metadata" : {},
        })
    assert "path"    in result
    assert "caption" in result
    assert result["path"].endswith(".png")