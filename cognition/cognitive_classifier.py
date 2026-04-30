# aria/cognition/cognitive_classifier.py
#
# Classificateur cognitif d'ARIA.
#
# Responsabilité unique : mapper un message entrant vers une CognitiveOperation.
#
# Pipeline de classification (ordre de priorité décroissant) :
#   1. Metadata image (Telegram envoie une photo)   → IMAGE_INPUT
#   2. Heuristique texte image generation           → IMAGE_GENERATION
#   3. Message court → CONFIRMATION                 ← anti-intents parasites
#   4. Ingestion (message long > 150 chars)          → INGESTION
#   5. Cache MemPalace (pattern déjà vu)             → opération mise en cache
#   6. Classifieur LLM                               → opération LLM
#   7. Fallback                                      → UNKNOWN
#
# Fonctions exportées :
#   classify_operation()              — mapping message → CognitiveOperation
#   detect_image_generation_intent()  — heuristique génération image (texte pur)
#   detect_generation_intent_from_caption() — génération depuis caption photo
#   is_interrogative_caption()        — caption = question sur le contenu de l'image

import json
from cognition.cognitive_context import CognitiveOperation
from memory.mempalace_store import search
from memory.mempalace_writer import store_interaction


# =========================================================
# SEUILS
# =========================================================

# Messages plus courts que ce seuil sont traités comme CONFIRMATION.
# Évite la création d'intents parasites sur les salutations et
# les réponses brèves ("Ok", "Merci", "Les deux", "Salut").
MIN_MESSAGE_LENGTH = 10


# =========================================================
# HEURISTIQUES IMAGE
# =========================================================

# Mots-clés déclenchant IMAGE_GENERATION pour un message texte pur.
_TEXT_GENERATION_KEYWORDS = [
    # Verbes de création directe
    "génère", "generé", "genere",
    "dessine", "illustre",
    "crée une image", "cree une image",
    "génère une image", "genere une image",
    "fais une image", "fais moi une image",
    "produis une image",
    # Formats spécifiques — très peu ambigus
    "meme", "mème",
    "illustration",
    "infographie",
    "logo",
    "affiche",
    "bannière",
    # Visualisation explicite
    "visualise", "montre moi",
    # Anglais
    "generate image", "draw", "make an image",
    "create image", "render",
]

# Mots-clés indiquant une demande de génération dans une caption photo.
_CAPTION_GENERATION_KEYWORDS = [
    "génère", "generé", "genere",
    "dessine", "crée", "cree",
    "transforme", "refais", "fais",
    "produis", "render", "generate",
    "draw", "create", "make",
    "version", "style", "comme ça mais",
]

# Marqueurs signalant que la caption est une question sur le contenu de l'image.
# Une caption interrogative déclenche le pipeline enrichi (vision → LLM cognitif)
# plutôt que la description vision brute.
#
# Exemples positifs : "c'est quoi ?", "tu reconnais ?", "qu'est-ce que c'est ?"
# Exemples négatifs : "substrats de shiitakes usés", "jardin 2024", "photo du verger"
_INTERROGATIVE_MARKERS = [
    "?",
    "c'est quoi", "c est quoi", "c'est quoi ça", "c'est koi",
    "kesako", "kezako",
    "qu'est-ce", "qu est ce", "qu'est ce",
    "qu'est-ce que c'est", "qu'est ce que c'est",
    "c'est quoi ce", "c'est quoi ces",
    "tu reconnais", "tu sais ce que c'est", "tu vois quoi",
    "what is", "what's", "what are", "what do you see",
    "c'est quoi là", "ça ressemble à quoi",
    "tu peux identifier", "tu identifies",
    "comment ça s'appelle",
]


def detect_image_generation_intent(message: str) -> bool:
    """
    Retourne True si un message texte pur exprime une demande de génération image.

    Utilisé par classify_operation() avant le call LLM pour court-circuiter
    les cas les plus évidents sans consommer de tokens.

    Exemples positifs : "génère une image de mon jardin", "fais moi un meme"
    Exemples négatifs : "planifie mon jardin", "comment dessiner ?"
    """
    lower = message.lower()
    return any(k in lower for k in _TEXT_GENERATION_KEYWORDS)


def detect_generation_intent_from_caption(caption: str | None) -> bool:
    """
    Retourne True si la caption d'une photo exprime une demande de génération.

    Utilisé par CognitiveEngine.classify() pour les events IMAGE :
    une photo envoyée avec une caption de transformation → IMAGE_GENERATION.
    Une photo envoyée avec une description neutre       → IMAGE_INPUT.
    """
    if not caption:
        return False
    lower = caption.lower()
    return any(k in lower for k in _CAPTION_GENERATION_KEYWORDS)


def is_interrogative_caption(caption: str | None) -> bool:
    """
    Retourne True si la caption d'une photo est une question sur son contenu.

    Distinction critique avec detect_generation_intent_from_caption() :
      - génération   : "transforme-la en aquarelle", "refais dans le style Monet"
      - interrogative: "c'est quoi ?", "tu reconnais ça ?", "qu'est-ce que c'est ?"

    Quand True, ImageExecutionRouter._handle_input() bascule vers le pipeline
    enrichi : description vision → LLMExecutionRouter (mémoire + intents).
    Quand False, retour direct de la description vision brute.

    Exemples positifs  : "c'est quoi ?", "qu'est-ce que c'est ?", "tu reconnais ?"
    Exemples négatifs  : "substrats de shiitakes usés", "jardin 2024", None
    """
    if not caption:
        return False
    lower = caption.lower().strip()
    return any(marker in lower for marker in _INTERROGATIVE_MARKERS)


# =========================================================
# CLASSIFIER LLM
# =========================================================

CLASSIFIER_PROMPT = """
Tu es un classificateur d'opérations cognitives pour un assistant personnel.

Classe ce message dans UNE des catégories suivantes :

- image_generation : demande de création, génération ou dessin d'une image, d'une illustration, d'un meme, d'un logo, d'une affiche ("génère une image", "fais moi un meme", "dessine mon jardin", "crée une illustration")
- fact_recall      : demande d'un fait précis ("quelles graines n'ont pas germé", "j'ai des carottes ?")
- memory_query     : demande de rappel ("rappelle moi ma liste", "qu'est ce que j'avais dit")
- planning         : demande de plan, programme, étapes ("crée un programme", "planifie", "comment apprendre")
- reasoning        : analyse, comparaison, explication ("analyse mon jardin", "compare", "pourquoi")
- meta_memory      : synthèse globale ("quels sujets on a abordé", "résume notre conversation")
- profile_query    : question sur soi-même ("est ce que je peux manger ça", "suis-je allergique")
- ingestion        : fourniture d'information brute sans question (listes, catalogues, contexte)
- unknown          : aucune des catégories ci-dessus

Réponds UNIQUEMENT avec un JSON :
{{"operation": "<catégorie>", "confidence": <0.0 à 1.0>}}

Message : {message}
"""

CONFIDENCE_THRESHOLD = 0.65


def classify_operation(
    message: str,
    llm_router=None,
    metadata: dict | None = None,
) -> CognitiveOperation:
    """
    Classe un message entrant dans une CognitiveOperation.

    Pipeline de priorité décroissant — s'arrête dès qu'une règle matche.

    Args:
        message    : texte brut du message utilisateur
        llm_router : LLMRouter (optionnel — sans LLM, retourne UNKNOWN en fallback)
        metadata   : dict de métadonnées Telegram (image, etc.)

    Returns:
        CognitiveOperation correspondant au message
    """
    metadata = metadata or {}

    # ── 1. Image reçue via Telegram ─────────────────────────────────────────
    if metadata.get("image") is not None:
        return CognitiveOperation.IMAGE_INPUT

    # ── 2. Heuristique génération image ─────────────────────────────────────
    if detect_image_generation_intent(message):
        return CognitiveOperation.IMAGE_GENERATION

    # ── 3. Message court → CONFIRMATION ────────────────────────────────────
    # Les salutations ("Salut", "Ok"), réponses brèves ("Les deux", "Oui"),
    # et continuations contextuelles ne doivent pas créer d'intent.
    # CONFIRMATION est routé vers llm_router mais n'implique pas de création
    # d'intent dans LLMExecutionRouter (recall_decision.action != "create").
    if len(message.strip()) <= MIN_MESSAGE_LENGTH:
        return CognitiveOperation.CONFIRMATION

    # ── 4. Ingestion (message long) ──────────────────────────────────────────
    if len(message) > 150:
        return CognitiveOperation.INGESTION

    # ── 5. Cache MemPalace ───────────────────────────────────────────────────
    cached = _search_cache(message)
    if cached:
        return cached

    # ── 6. Classifieur LLM ───────────────────────────────────────────────────
    if llm_router is None:
        return CognitiveOperation.UNKNOWN

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

        operation  = _parse_operation(data.get("operation", "unknown"))
        confidence = float(data.get("confidence", 0.0))

        if confidence >= CONFIDENCE_THRESHOLD and operation != CognitiveOperation.UNKNOWN:
            _store_cache(message, operation)

        return operation

    except Exception as e:
        print(f"[CLASSIFIER ERROR] {e}")
        return CognitiveOperation.UNKNOWN


# =========================================================
# CACHE
# =========================================================

def store_confirmed_operation(message: str, operation: CognitiveOperation):
    """Stocke un mapping confirmé explicitement par l'utilisateur."""
    _store_cache(message, operation, confirmed=True)


def _search_cache(message: str) -> CognitiveOperation | None:
    """
    Recherche un pattern similaire dans le cache classifier de MemPalace.

    Seuil strict (0.92) pour éviter les faux positifs.
    """
    try:
        results = search(query=message, wing="aria_classifier", n=1)
        hits    = results.get("results", [])
        if not hits:
            return None

        hit = hits[0]
        if hit.get("similarity", 0) < 0.92:
            return None

        data = json.loads(hit.get("text", ""))
        return _parse_operation(data.get("operation", "unknown"))

    except Exception:
        return None


def _store_cache(message: str, operation: CognitiveOperation, confirmed: bool = False):
    """Stocke un mapping message → operation dans le cache classifier."""
    try:
        store_interaction(
            text=json.dumps({"message": message, "operation": operation.value}),
            intent_id="classifier_cache",
            metadata={
                "wing"      : "aria_classifier",
                "room"      : "classifier_cache",
                "confirmed" : confirmed,
                "type"      : "classifier_cache",
            },
        )
    except Exception as e:
        print(f"[CLASSIFIER STORE ERROR] {e}")


# =========================================================
# HELPERS
# =========================================================

def _parse_operation(s: str) -> CognitiveOperation:
    """Convertit une string en CognitiveOperation, UNKNOWN si invalide."""
    try:
        return CognitiveOperation(s.lower())
    except ValueError:
        return CognitiveOperation.UNKNOWN