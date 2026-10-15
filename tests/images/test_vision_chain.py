# Chaîne vision (sprint 19, tronçon 01) : DeepSeek d'abord, raisonnement coupé,
# puis groq ×3 en secours.

from llm.image_router import VISION_ROUTING_TABLE


def test_vision_chain_starts_with_deepseek_then_three_groq():
    providers = [entry["provider"] for entry in VISION_ROUTING_TABLE]
    assert providers == ["deepseek", "groq1", "groq2", "groq3"]
    assert VISION_ROUTING_TABLE[0]["extra"] == {"thinking": {"type": "disabled"}}
