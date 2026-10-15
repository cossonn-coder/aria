# Chaîne vision (sprint 18, tronçon 02) : groq ×3 puis DeepSeek en dernier recours.

from llm.image_router import VISION_ROUTING_TABLE


def test_vision_chain_ends_with_deepseek_after_three_groq():
    providers = [entry["provider"] for entry in VISION_ROUTING_TABLE]
    assert providers == ["groq1", "groq2", "groq3", "deepseek"]
