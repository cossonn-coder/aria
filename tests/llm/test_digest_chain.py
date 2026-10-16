# Sprint 23 tronçon 01 : la chaîne DIGEST exclut Groq.

from llm.llm_role import LLMRole
from llm.llm_router import ROUTING_TABLE


def test_digest_chain_has_no_groq():
    providers = [e["provider"] for e in ROUTING_TABLE[LLMRole.DIGEST]]
    assert providers == ["deepseek", "anthropic"]
