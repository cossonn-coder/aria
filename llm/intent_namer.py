from llm.llm_router import LLMRouter
from llm.llm_role import LLMRole

NAMER_PROMPT = """
Tu décides si le message de l'utilisateur relève d'un projet à retenir.

- Si le message prolonge un des projets actifs listés (directement ou via le
  message précédent), réponds EXACTEMENT le nom de ce projet.
- Si c'est un nouveau projet ou objectif durable de l'utilisateur (quelque
  chose qu'il compte faire, apprendre, suivre), réponds son sujet en 2 à 5 mots.
- Sinon (question ponctuelle, relance sans projet, remarque, bavardage),
  réponds : aucun

Réponds UNIQUEMENT avec le nom, sans ponctuation, sans majuscule, sans explication.

Exemples :
- "je veux partir en normandie en train" → vacances normandie train
- "aide moi à apprendre docker" → apprentissage docker
- "il fait beau aujourd'hui" → aucun
- "évalue la position" (précédent : photo d'un échiquier) → aucun
- "combien de pieds pour la surface ?" (précédent : tomates cerises sur le
  balcon, projet actif : plantation tomates balcon est) → plantation tomates balcon est

PROJETS ACTIFS : {active_intents}
MESSAGE PRÉCÉDENT : {previous_message}
MESSAGE : {message}
"""


def extract_intent_name(
    message: str,
    llm_router: LLMRouter,
    previous_message: str | None = None,
    active_intent_names=(),
) -> str | None:
    """
    Nom canonique de l'intent, ou None si le namer juge que le message
    ne mérite aucun intent (réponse « aucun », #59).
    """
    try:
        response = llm_router.complete(
            prompt=NAMER_PROMPT.format(
                active_intents=", ".join(active_intent_names) or "(aucun)",
                previous_message=previous_message or "(aucun)",
                message=message,
            ),
            role=LLMRole.CHAT,
            temperature=0.1,
            max_tokens=20,
        )
        name = response.content.strip().lower()[:60]
        if name == "aucun":
            return None
        return name if name else message[:60]
    except Exception:
        return message[:60]
