# Chaîne vision (sprint 19, tronçon 01 ; ordre revu le 2026-11-25) : groq ×3 d'abord,
# DeepSeek en dernier (crédit épuisé), raisonnement coupé.

from llm.image_router import VISION_ROUTING_TABLE


def test_vision_chain_three_groq_then_deepseek():
    providers = [entry["provider"] for entry in VISION_ROUTING_TABLE]
    assert providers == ["groq1", "groq2", "groq3", "deepseek"]
    assert VISION_ROUTING_TABLE[-1]["extra"] == {"thinking": {"type": "disabled"}}
