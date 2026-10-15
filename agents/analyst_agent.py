# aria/agents/analyst_agent.py

from agents.base_agent import BaseAgent, AgentContext
from cognition.cognitive_context import LLM_ROLE_MAP, CognitiveOperation
from llm.llm_router import LLMRouter



# Gabarit de la partie propre à l'agent dans le system prompt
# (PROJET RÉCENT + RÈGLES). Le message utilisateur et l'historique
# conversationnel partent en messages séparés, pas dans ce gabarit.
# Lu par le garde-fou tests/agents/test_analyst_prompt_guard.py.
PROMPT = """PROJET RÉCENT EN MÉMOIRE :
{intent_name}

RÈGLES :
- Réponds toujours à la question posée, quel que soit le sujet
- Si la mémoire contient la réponse → cite-la exactement
- Si c'est une demande de rappel → liste ce qui est en mémoire
- Si c'est une action → décris les étapes
- N'hallucine JAMAIS du contenu absent de la mémoire
- Sois concis
"""


class AnalystAgent(BaseAgent):

    name = "analyst"

    def run(self, ctx: AgentContext, llm_router):

        operation = ctx.extra.get("cognitive_operation", CognitiveOperation.UNKNOWN)
        role = LLM_ROLE_MAP.get(operation)

        # Forme messages native : system, puis l'historique pré-chargé par
        # le router (timestamp retiré), puis le message courant.
        history = ctx.extra.get("conversation_history", [])
        messages = (
            [{"role": "system", "content": self._build_system_prompt(ctx)}]
            + [{"role": h["role"], "content": h["content"]} for h in history]
            + [{"role": "user", "content": ctx.message}]
        )

        response = llm_router.complete(
            messages=messages,
            role=role,
            temperature=0.3,
            max_tokens=800,
        )
        ctx.result = response.content
        return ctx

    def _build_system_prompt(self, ctx: AgentContext) -> str:
        """
        Compose le system prompt : base ARIA (soul + profil), contexte
        cognitif assemblé par le router, puis la partie propre à l'agent.
        """
        context_block = ctx.extra.get("context_block", "Aucun contexte disponible.")
        return (
            LLMRouter.build_base_system_prompt()
            + "\n\nCONTEXTE COGNITIF :\n" + context_block
            + "\n\n" + PROMPT.format(intent_name=ctx.intent.name)
        )
