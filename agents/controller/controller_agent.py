# aria/agents/controller/controller_agent.py

from agents.base_agent import AgentContext
from cognition.cognitive_context import CognitiveOperation


class AgentController:

    def __init__(self, registry):
        self.registry = registry

    def run(self, ctx: AgentContext, llm_router):

        operation = ctx.extra.get("cognitive_operation", CognitiveOperation.UNKNOWN)

        # routing par opération cognitive en priorité
        if operation in (
            CognitiveOperation.FACT_RECALL,
            CognitiveOperation.MEMORY_QUERY,
            CognitiveOperation.PROFILE_QUERY,
            CognitiveOperation.META_MEMORY,
        ):
            pipeline = ["analyst"]

        elif operation == CognitiveOperation.PLANNING:
            pipeline = ["analyst", "planner"]

        elif operation == CognitiveOperation.REASONING:
            pipeline = ["analyst"]

        else:
            # fallback : routing par phase d'intent
            phase = ctx.intent.infer_phase() if ctx.intent else "creation"
            if phase == "creation":
                pipeline = ["analyst"]
            elif phase == "planning":
                pipeline = ["analyst", "planner"]
            elif phase == "execution":
                pipeline = ["executor", "critic"]
            else:
                pipeline = ["analyst"]

        for agent_name in pipeline:
            agent = self.registry.get(agent_name)
            if agent:
                ctx = agent.run(ctx, llm_router)

        return ctx