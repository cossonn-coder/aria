from unittest.mock import MagicMock

from llm.intent_namer import extract_intent_name


def test_aucun_returns_none_and_prompt_has_context():
    """#59 : « Aucun » → None ; le prompt porte intents actifs + message précédent."""
    llm_router = MagicMock()
    llm_router.complete.return_value = MagicMock(content="Aucun")

    name = extract_intent_name(
        "combien de pieds ?",
        llm_router,
        previous_message="tomates cerises sur le balcon",
        active_intent_names=["plantation tomates balcon est"],
    )

    assert name is None
    prompt = llm_router.complete.call_args.kwargs["prompt"]
    assert "plantation tomates balcon est" in prompt
    assert "tomates cerises sur le balcon" in prompt
