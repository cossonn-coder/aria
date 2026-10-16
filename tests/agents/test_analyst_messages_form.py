# tests/agents/test_analyst_messages_form.py
#
# AnalystAgent appelle le LLM en forme messages native (sprint 17, tronçon 02) :
# [system, historique..., user courant].

from unittest.mock import MagicMock

from agents.analyst_agent import AnalystAgent
from agents.base_agent import AgentContext
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_trace import CognitiveTrace


def _run(history=None):
    intent = MagicMock()
    intent.name = "projet_terrarium"
    extra = {
        "cognitive_operation": CognitiveOperation.REASONING,
        "context_block": "bloc de contexte injecté",
    }
    if history is not None:
        extra["conversation_history"] = history
    ctx = AgentContext(
        message="message courant",
        intent=intent,
        memories={},
        session_memory={},
        trace=CognitiveTrace(),
        extra=extra,
    )
    llm_router = MagicMock()
    llm_router.complete.return_value.content = "réponse"
    AnalystAgent().run(ctx, llm_router)
    return llm_router.complete.call_args.kwargs


def test_empty_history_gives_system_and_user():
    messages = _run([])["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[1]["content"] == "message courant"


def test_history_inserted_in_order_without_timestamp():
    history = [
        {"role": "user", "content": "u1", "timestamp": "2026-10-15T10:00:00"},
        {"role": "assistant", "content": "a1", "timestamp": "2026-10-15T10:00:01"},
    ]
    messages = _run(history)["messages"]
    assert messages[1:] == [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "message courant"},
    ]


def test_system_prompt_contains_profile_context_and_intent(monkeypatch):
    import llm.llm_router as llm_router_module
    monkeypatch.setattr(llm_router_module, "_USER", "Nico, profil de test")
    system = _run()["messages"][0]["content"]
    assert "PROFIL UTILISATEUR" in system
    assert "bloc de contexte injecté" in system
    assert "projet_terrarium" in system


def test_reasoning_answer_budget_is_1500_tokens():
    # Sprint 23 tronçon 04 : 800 tronquait les réponses longues (run live D).
    assert _run()["max_tokens"] == 1500
