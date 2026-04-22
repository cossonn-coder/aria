from llm.llm_router import LLMRouter
from llm.llm_role import LLMRole

NAMER_PROMPT = """
Extrait le sujet principal de ce message en 2 à 5 mots maximum.
Réponds UNIQUEMENT avec le sujet, sans ponctuation, sans majuscule, sans explication.

Exemples :
- "j'ai déjà mis de la bière dans la liste ?" → liste de courses
- "je veux partir en normandie en train" → vacances normandie train
- "aide moi à apprendre docker" → apprentissage docker
- "écrit une liste de courses" → liste de courses

MESSAGE : {message}
"""


def extract_intent_name(message: str, llm_router: LLMRouter) -> str:
    try:
        response = llm_router.complete(
            prompt=NAMER_PROMPT.format(message=message),
            role=LLMRole.CHAT,
            temperature=0.1,
            max_tokens=20,
        )
        name = response.content.strip().lower()[:60]
        return name if name else message[:60]
    except Exception:
        return message[:60]