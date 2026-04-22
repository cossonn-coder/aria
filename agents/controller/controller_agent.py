# aria/agents/controller/controller_agent.py

from agents.base_agent import AgentContext
from cognition.cognitive_context import CognitiveOperation


class AgentController:

    def __init__(self, registry):
        self.registry = registry

    def run(self, ctx: AgentContext, llm_router):

        operation = ctx.extra.get(
            "cognitive_operation",
            CognitiveOperation.UNKNOWN
        )

        # =====================================================
        # 1 — ROUTING LOGIC (inchangé)
        # =====================================================
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
            phase = ctx.intent.infer_phase() if ctx.intent else "creation"

            if phase == "creation":
                pipeline = ["analyst"]
            elif phase == "planning":
                pipeline = ["analyst", "planner"]
            elif phase == "execution":
                pipeline = ["executor", "critic"]
            else:
                pipeline = ["analyst"]

        # =====================================================
        # 2 — EXECUTION ENGINE (nouvelle couche explicite)
        # =====================================================
        for agent_name in pipeline:

            agent = self.registry.get(agent_name)
            if not agent:
                continue

            # START TRACE
            ctx.trace.start(agent_name)

            before_state = ctx.result

            ctx = agent.run(ctx, llm_router)

            after_state = ctx.result

            # END TRACE
            ctx.trace.end(
                output_snapshot=str(after_state)
            )

            if ctx.halted:
                break

        return ctx