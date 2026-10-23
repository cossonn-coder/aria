# tests/agents/test_controller_pipeline.py
# Sprint 32 (#74, #113) : un message court (CONFIRMATION) passe par l'analyst seul,
# même quand l'intent est en phase « execution ».

from unittest.mock import MagicMock

from agents.base_agent import AgentContext
from agents.controller.controller_agent import AgentController
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_trace import CognitiveTrace
from intent.intent import Intent


def test_confirmation_en_phase_execution_lance_analyst_seul():
    intent = Intent(name="test intent", actions_history=["x"], next_action="y")
    assert intent.infer_phase() == "execution"
    ctx = AgentContext(
        message="salut",
        intent=intent,
        memories={},
        session_memory={},
        trace=CognitiveTrace(),
        extra={"cognitive_operation": CognitiveOperation.CONFIRMATION},
    )

    # Un agent factice par nom, dont run renvoie le ctx tel quel
    agents = {}
    for name in ("analyst", "planner", "executor", "critic"):
        agent = MagicMock()
        agent.run.side_effect = lambda c, llm: c
        agents[name] = agent
    registry = MagicMock()
    registry.get.side_effect = agents.get

    AgentController(registry).run(ctx, llm_router=MagicMock())

    agents["analyst"].run.assert_called_once()
    agents["planner"].run.assert_not_called()
    agents["executor"].run.assert_not_called()
    agents["critic"].run.assert_not_called()
