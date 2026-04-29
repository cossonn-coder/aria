# aria/cognition/cognitive_classifier.py
#
# Classificateur cognitif d'ARIA.
#
# Responsabilité unique : mapper un message entrant vers une CognitiveOperation.
#
# Pipeline de classification (ordre de priorité décroissant) :
#   1. Metadata image (Telegram envoie une photo)   → IMAGE_INPUT
#   2. Heuristique texte image generation           → IMAGE_GENERATION
#   3. Ingestion (message long > 150 chars)          → INGESTION
#   4. Cache MemPalace (pattern déjà vu)             → opération mise en cache
#   5. Classifieur LLM                               → opération LLM
#   6. Fallback                                      → UNKNOWN
#
# Règle :
#   Ce module ne décide pas de l'exécution — il retourne une CognitiveOperation.
#   Toute logique d'exécution vit dans les routers.

import json
from cognition.cognitive_context import CognitiveOperation
from memory.mempalace_store import search
from memory.mempalace_writer import store_interaction


# =========================================================
# HEURISTIQUES IMAGE
# =========================================================

# Mots-clés déclenchant IMAGE_GENERATION pour un message texte pur.
# Liste conservative — les faux positifs sont plus gênants que les faux négatifs
# (un faux positif génère une image non souhaitée ; un faux négatif donne
# une réponse texte là où on attendait une image, rattrapable par reformulation).
_TEXT_GENERATION_KEYWORDS = [
    # Verbes de création directe
    "génère", "generé", "genere",
    "dessine", "illustre",
    "crée une image", "cree une image", "créé une image",
    "génère une image", "genere une image",
    "fais une image", "fais moi une image", "fait une image",
    "produis une image", "produit une image",
    # Formats spécifiques — très peu ambigus
    "meme", "mème",
    "illustration",
    "infographie",
    "logo",
    "affiche",
    "bannière",
    # Anglais
    "generate image", "draw", "make an image",
    "create image", "render",
]

# Mots-clés indiquant une demande de génération dans une caption accompagnant une photo.
# Plus permissifs que les keywords texte : l'utilisateur a déjà fourni une image
# comme référence visuelle, donc l'intention de transformation est plus probable.
_CAPTION_GENERATION_KEYWORDS = [
    "génère", "generé", "genere",
    "dessine", "crée", "cree",
    "transforme", "refais", "fais",
    "produis", "render", "generate",
    "draw", "create", "make",
    "version", "style", "comme ça mais",
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

    Exemples positifs  : "génère une version estivale", "dessine ça en aquarelle"
    Exemples négatifs  : "c'est ma courge", "qu'est-ce que c'est ?", None
    """
    if not caption:
        return False
    lower = caption.lower()
    return any(k in lower for k in _CAPTION_GENERATION_KEYWORDS)


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
    # Priorité maximale : si une photo est jointe, c'est une entrée image.
    # La distinction INPUT vs GENERATION est faite dans CognitiveEngine
    # via detect_generation_intent_from_caption().
    if metadata.get("image") is not None:
        return CognitiveOperation.IMAGE_INPUT

    # ── 2. Heuristique génération image ─────────────────────────────────────
    # Court-circuite le LLM pour les demandes de génération les plus explicites.
    # Rapide, offline, sans consommation de tokens.
    if detect_image_generation_intent(message):
        return CognitiveOperation.IMAGE_GENERATION

    # ── 3. Ingestion (message long) ──────────────────────────────────────────
    # Un message > 150 chars sans question est traité comme fourniture
    # d'information brute à stocker directement.
    if len(message) > 150:
        return CognitiveOperation.INGESTION

    # ── 4. Cache MemPalace ───────────────────────────────────────────────────
    # Si ce pattern a déjà été vu et classifié avec haute confiance,
    # réutiliser le résultat sans appel LLM.
    cached = _search_cache(message)
    if cached:
        return cached

    # ── 5. Classifieur LLM ───────────────────────────────────────────────────
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

        operation = _parse_operation(data.get("operation", "unknown"))
        confidence = float(data.get("confidence", 0.0))

        # Mise en cache si confiance suffisante et opération non ambiguë
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
    """
    Stocke un mapping confirmé explicitement par l'utilisateur.

    Utilisé pour renforcer le cache sur des patterns récurrents
    après validation humaine (feedback loop).
    """
    _store_cache(message, operation, confirmed=True)


def _search_cache(message: str) -> CognitiveOperation | None:
    """
    Recherche un pattern similaire dans le cache classifier de MemPalace.

    Seuil de similarité strict (0.92) pour éviter les faux positifs :
    deux messages cognitivement différents peuvent être lexicalement proches.

    Returns:
        CognitiveOperation si un pattern similaire est trouvé, None sinon.
    """
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
    """
    Stocke un mapping message → operation dans le cache classifier de MemPalace.

    Args:
        message   : message source
        operation : opération classifiée
        confirmed : True si validé par l'utilisateur (feedback loop)
    """
    try:
        store_interaction(
            text=json.dumps({"message": message, "operation": operation.value}),
            intent_id="classifier_cache",
            metadata={
                "wing": "aria_classifier",
                "room": "classifier_cache",
                "confirmed": confirmed,
                "type": "classifier_cache",
            },
        )
    except Exception as e:
        print(f"[CLASSIFIER STORE ERROR] {e}")


# =========================================================
# HELPERS
# =========================================================

def _parse_operation(s: str) -> CognitiveOperation:
    """
    Convertit une string en CognitiveOperation.

    Retourne UNKNOWN si la valeur ne correspond à aucune opération connue,
    plutôt que de lever une exception.
    """
    try:
        return CognitiveOperation(s.lower())
    except ValueError:
        return CognitiveOperation.UNKNOWN