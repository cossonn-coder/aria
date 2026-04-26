# aria/cognition/cognitive_classifier.py

import json
from cognition.cognitive_context import CognitiveOperation
from memory.mempalace_store import search
from memory.mempalace_writer import store_interaction

def detect_image_intent(message: str) -> bool:
    keywords = [
        "image", "dessine", "génère une image",
        "draw", "generate image", "photo"
    ]
    return any(k in message.lower() for k in keywords)

def detect_image_input(message: str, metadata: dict) -> bool:
    return metadata.get("image") is not None

CLASSIFIER_PROMPT = """
Tu es un classificateur d'opérations cognitives.

Classe ce message dans UNE des catégories suivantes :
- fact_recall : demande d'un fait précis ("quelles graines n'ont pas germé", "j'ai des carottes ?")
- memory_query : demande de rappel ("rappelle moi ma liste", "qu'est ce que j'avais dit")
- planning : demande de plan, programme, étapes ("crée un programme", "planifie", "comment apprendre")
- reasoning : analyse, comparaison, explication ("analyse mon jardin", "compare", "pourquoi")
- meta_memory : synthèse globale ("quels sujets on a abordé", "résume notre conversation")
- profile_query : question sur soi-même ("est ce que je peux manger ça", "suis-je allergique")
- ingestion : fourniture d'information brute sans question (listes, catalogues, contexte)
- unknown : aucune des catégories ci-dessus

Réponds UNIQUEMENT avec un JSON :
{{"operation": "<catégorie>", "confidence": <0.0 à 1.0>}}

Message : {message}
"""

CONFIDENCE_THRESHOLD = 0.65

# Mots-clés indiquant une demande de génération dans une caption accompagnant une photo
_GENERATION_KEYWORDS = [
    "génère", "generé", "genere",
    "dessine", "crée", "cree",
    "transforme", "refais", "fais",
    "produis", "render", "generate",
    "draw", "create", "make",
    "version", "style", "comme ça mais",
]

def detect_generation_intent_from_caption(caption: str | None) -> bool:
    """
    Retourne True si la caption d'une photo exprime une demande de génération.

    Exemples positifs  : "génère une version estivale", "dessine ça en aquarelle"
    Exemples négatifs  : "c'est ma courge", "qu'est-ce que c'est ?", None
    """
    if not caption:
        return False
    lower = caption.lower()
    return any(k in lower for k in _GENERATION_KEYWORDS)


def classify_operation(message: str, llm_router=None, metadata: dict | None = None) -> CognitiveOperation:

    metadata = metadata or {}

    # 1. image explicite via metadata (Telegram / API)
    if metadata.get("image") is not None:
        return CognitiveOperation.IMAGE_INPUT

    # 2. heuristique texte
    if detect_image_intent(message):
        return CognitiveOperation.IMAGE_GENERATION

    # ingestion sur message long
    if len(message) > 150:
        return CognitiveOperation.INGESTION

    # 1. cherche dans MemPalace si pattern déjà connu
    cached = _search_cache(message)
    if cached:
        return cached

    # 2. si pas de LLM disponible → unknown
    if llm_router is None:
        return CognitiveOperation.UNKNOWN

    # 3. appel LLM classifier
    try:
        from llm.llm_role import LLMRole
        response = llm_router.complete(
            prompt=CLASSIFIER_PROMPT.format(message=message),
            role=LLMRole.CHAT,
            temperature=0.1,
            max_tokens=60,
        )

        raw = response.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw.startswith("{"):
            raw = "{" + raw + "}"
        data = json.loads(raw)

        operation = _parse_operation(data.get("operation", "unknown"))
        confidence = float(data.get("confidence", 0.0))

        # 4. stocke dans MemPalace si confiance suffisante
        if confidence >= CONFIDENCE_THRESHOLD and operation != CognitiveOperation.UNKNOWN:
            _store_cache(message, operation)

        return operation

    except Exception as e:
        print(f"[CLASSIFIER ERROR] {e}")
        return CognitiveOperation.UNKNOWN


def store_confirmed_operation(message: str, operation: CognitiveOperation):
    """Stocke un mapping confirmé par l'utilisateur."""
    _store_cache(message, operation, confirmed=True)


def _search_cache(message: str) -> CognitiveOperation | None:
    try:
        results = search(
            query=message,
            wing="aria_classifier",
            n=1,
        )
        hits = results.get("results", [])
        if not hits:
            return None

        hit = hits[0]
        if hit.get("similarity", 0) < 0.92:
            return None

        text = hit.get("text", "")
        data = json.loads(text)
        return _parse_operation(data.get("operation", "unknown"))

    except Exception:
        return None


def _store_cache(message: str, operation: CognitiveOperation, confirmed: bool = False):
    try:
        store_interaction(
            text=json.dumps({"message": message, "operation": operation.value}),
            intent_id=f"classifier_cache",
            metadata={
                "wing": "aria_classifier",
                "room": "classifier_cache",
                "confirmed": confirmed,
                "type": "classifier_cache",
            },
        )
    except Exception as e:
        print(f"[CLASSIFIER STORE ERROR] {e}")


def _parse_operation(s: str) -> CognitiveOperation:
    try:
        return CognitiveOperation(s.lower())
    except ValueError:
        return CognitiveOperation.UNKNOWN