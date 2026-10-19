# Sprint 23 tronçon 01 : la chaîne DIGEST exclut Groq.

from llm.llm_role import LLMRole
from llm.llm_router import ROUTING_TABLE


def test_digest_chain_has_no_groq():
    providers = [e["provider"] for e in ROUTING_TABLE[LLMRole.DIGEST]]
    assert providers == ["deepseek", "anthropic"]


def test_reasoning_chain_has_no_groq():
    # Sprint 28 tronçon 05 : l'analyse d'échecs dépasse le quota Groq gratuit.
    providers = [e["provider"] for e in ROUTING_TABLE[LLMRole.REASONING]]
    assert not any(p.startswith("groq") for p in providers)
