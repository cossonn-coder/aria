# aria/cognition/cognitive_classifier.py
#
# Classificateur cognitif d'ARIA.
#
# Responsabilité unique : mapper un message entrant vers une CognitiveOperation.
#
# Pipeline de classification (ordre de priorité décroissant) :
#   1. Metadata image (Telegram envoie une photo)   → IMAGE_INPUT
#   1b. PGN collé (en-tête White/Black + coups)      → CHESS_ANALYSIS
#   2. URL http(s):// dans le message                → URL_READ
#   2b. « oui » / « lis la suite » après lecture partielle → URL_READ
#   2c. « relis… » ou « oui » après proposition de relecture → DOC_REREAD
#   3a. « fais une recherche sur… » (sprint 45)      → WEB_RESEARCH
#   3. Heuristique texte recherche web              → WEB_SEARCH
#   4. Heuristique texte image generation           → IMAGE_GENERATION
#   5. Message court → CONFIRMATION                 ← anti-intents parasites
#   6. Cache MemPalace (pattern déjà vu)             → opération mise en cache
#   7. Classifieur LLM                               → opération LLM
#   8. Fallback                                      → UNKNOWN
#
# Fonctions exportées :
#   classify_operation()              — mapping message → CognitiveOperation
#   detect_url()                      — première URL http(s) du message
#   detect_pgn()                      — partie PGN collée (sprint 26)
#   detect_web_search_intent()        — heuristique recherche web explicite
#   detect_web_research_intent()      — heuristique recherche autonome (sprint 45)
#   detect_image_generation_intent()  — heuristique génération image (texte pur)
#   is_interrogative_caption()        — caption = question sur le contenu de l'image

import json
import re
from cognition.cognitive_context import CognitiveOperation, REREAD_PROPOSAL, URL_PARTIAL_MARKER
from memory.mempalace_bridge import MempalaceBridge
from memory.writer import write_classifier_cache
from logger import get_logger

log = get_logger(__name__)


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
    "bannière",
    # Anglais
    "generate image", "draw", "make an image",
    "create image",
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


def is_interrogative_caption(caption: str | None) -> bool:
    """
    Retourne True si la caption d'une photo est une question sur son contenu.

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
# HEURISTIQUE PGN (sprint 26)
# =========================================================

_PGN_HEADER_RE = re.compile(r'\[(?:White|Black) "')
_PGN_MOVES_RE = re.compile(r"\b1\.\s*\S")


def detect_pgn(message: str) -> bool:
    """
    Retourne True si le message contient une partie PGN : un en-tête
    `[White "` ou `[Black "` ET un texte de coups commençant par `1.`.

    Une suite de coups sans en-tête (« après 1.e4 e5 quelles idées ? »)
    reste au LLM.
    """
    return bool(_PGN_HEADER_RE.search(message) and _PGN_MOVES_RE.search(message))


# =========================================================
# HEURISTIQUE LECTURE D'URL
# =========================================================

_URL_RE = re.compile(r"https?://\S+")

# Ponctuation finale retirée : « regarde https://x.fr/page. » → https://x.fr/page
_URL_TRAILING_PUNCT = ".,;:!?)»"


def detect_url(message: str) -> str | None:
    """
    Retourne la première URL http(s) du message, ou None.

    Seule la première URL est lue (sprint 23) ; la ponctuation collée en
    fin d'URL est retirée.
    """
    match = _URL_RE.search(message)
    if match is None:
        return None
    return match.group(0).rstrip(_URL_TRAILING_PUNCT)


# Réponses de reprise après une lecture partielle (sprint 23, tronçon 02).
# Comparaison exacte après nettoyage ; « lis/lire la suite » matche aussi
# en sous-chaîne.
_URL_RESUME_EXACT = {
    "oui", "ouais", "vas-y", "vas y", "ok", "continue",
    "la suite", "lis la suite", "oui lis la suite",
}
_URL_RESUME_PHRASES = ["lis la suite", "lire la suite"]


def detect_url_resume(message: str, metadata: dict, bridge) -> bool:
    """
    Retourne True si le message demande la suite d'une lecture partielle.

    L'historique n'est lu (via le bridge) que si le message est une
    réponse de reprise : le dernier tour `user` doit contenir le marqueur
    URL_PARTIAL_MARKER posé par WebExecutionRouter. Sinon, un « oui »
    reste une CONFIRMATION ordinaire.
    """
    lower = message.lower().strip().rstrip("?!. ")
    if lower not in _URL_RESUME_EXACT and not any(p in lower for p in _URL_RESUME_PHRASES):
        return False
    if bridge is None:
        return False
    conversation_key = str(metadata.get("chat_id", "default"))
    history = bridge.load_conversation_history(conversation_key, n=2)
    user_turns = [t["content"] for t in history if t.get("role") == "user"]
    return bool(user_turns) and URL_PARTIAL_MARKER in user_turns[-1]


# Verbes de relecture explicite d'un document en mémoire (sprint 43).
_DOC_REREAD_WORDS = ["relis", "relire", "rouvre"]


def detect_doc_reread(message: str, metadata: dict, bridge) -> bool:
    """
    Retourne True si le message demande de relire un document déjà lu.

    Cas explicite : « relis / relire / rouvre » dans le message, sans
    lecture d'historique. Cas acceptation : réponse de reprise (« oui »,
    « vas-y »…) alors que le dernier tour `assistant` contient la
    proposition REREAD_PROPOSAL posée par la consigne de contexte.
    """
    lower = message.lower().strip().rstrip("?!. ")
    if any(w in lower for w in _DOC_REREAD_WORDS):
        return True
    if lower not in _URL_RESUME_EXACT or bridge is None:
        return False
    conversation_key = str(metadata.get("chat_id", "default"))
    history = bridge.load_conversation_history(conversation_key, n=2)
    assistant_turns = [t["content"] for t in history if t.get("role") == "assistant"]
    return bool(assistant_turns) and REREAD_PROPOSAL in assistant_turns[-1]


# =========================================================
# HEURISTIQUE RECHERCHE WEB
# =========================================================

# Phrases explicites de Nico déclenchant WEB_SEARCH (sous-chaîne, minuscules).
_WEB_SEARCH_PHRASES = [
    "cherche en ligne", "cherche sur le web", "cherche sur internet",
    "recherche en ligne", "recherche sur le web",
    "donne-moi les sources", "donne moi les sources",
]

# Messages courts qui, seuls, demandent les sources de la réponse précédente.
# Comparaison exacte : « la source de la Seine » ne doit pas matcher.
_WEB_SEARCH_EXACT = {"source", "sources"}


def detect_web_search_intent(message: str) -> bool:
    """
    Retourne True si un message texte demande explicitement une recherche web.

    Placée avant la règle « message court → CONFIRMATION » dans
    classify_operation(), sinon « source ? » serait avalé comme confirmation.

    Exemples positifs : "cherche sur le web le score du match", "source ?"
    Exemples négatifs : "il faut trouver une source d'eau", "la source de la Seine"
    """
    lower = message.lower()
    if any(p in lower for p in _WEB_SEARCH_PHRASES):
        return True
    # Nettoyage : ponctuation finale et espaces retirés (« Sources ? » → « sources »)
    return lower.strip().rstrip("?!. ") in _WEB_SEARCH_EXACT


# Phrases explicites déclenchant WEB_RESEARCH (sprint 45, sous-chaîne, minuscules).
# Recherche longue (plusieurs requêtes + lecture de pages) : jamais déduite
# par le classifier LLM, uniquement sur demande explicite.
_WEB_RESEARCH_PHRASES = [
    "fais une recherche sur", "fais une recherche en ligne sur", "fais des recherches sur",
    "fais une recherche approfondie", "recherche approfondie",
    "renseigne-toi sur", "renseigne toi sur",
]


def detect_web_research_intent(message: str) -> bool:
    """
    Retourne True si le message demande explicitement une recherche autonome.

    Exemples positifs : "fais une recherche sur la rotation des cultures",
    "renseigne-toi sur le paillage"
    Exemple négatif : "cherche en ligne la météo" (recherche rapide, WEB_SEARCH)
    """
    lower = message.lower()
    return any(p in lower for p in _WEB_RESEARCH_PHRASES)


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
- web_search : information récente ou externe que tu ne peux pas connaître (actualité, résultats sportifs, prix, météo, horaires, événements récents) ("quel temps demain à Caen", "score du match d'hier", "prix actuel du cuivre")
- meta_memory      : synthèse globale ("quels sujets on a abordé", "résume notre conversation")
- profile_query    : question sur soi-même ("est ce que je peux manger ça", "suis-je allergique")
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
    bridge: MempalaceBridge | None = None,
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

    # ── 1b. PGN collé → analyse de la partie ────────────────────────────────
    # Avant la règle URL : l'export Chess.com contient `[Link "https://…"]`.
    if detect_pgn(message):
        return CognitiveOperation.CHESS_ANALYSIS

    # ── 2. URL collée → lecture de la page ──────────────────────────────────
    # Prioritaire sur la recherche web (URL + « cherche en ligne » = lecture)
    # et sur « message court » (une URL seule = résumé de la page).
    if detect_url(message):
        return CognitiveOperation.URL_READ

    # ── 2b. Suite d'une lecture partielle ───────────────────────────────────
    # Avant « message court » : « oui » serait sinon une CONFIRMATION.
    if detect_url_resume(message, metadata, bridge):
        return CognitiveOperation.URL_READ

    # ── 2c. Relecture d'un document en mémoire (sprint 43) ──────────────────
    # Avant « message court » : « oui » serait sinon une CONFIRMATION.
    if detect_doc_reread(message, metadata, bridge):
        return CognitiveOperation.DOC_REREAD

    # ── 3a. Recherche autonome (sprint 45) ──────────────────────────────────
    # Avant la règle 3 : « fais une recherche en ligne sur X » contient
    # « recherche en ligne » mais demande une recherche autonome.
    if detect_web_research_intent(message):
        return CognitiveOperation.WEB_RESEARCH

    # ── 3. Heuristique recherche web ────────────────────────────────────────
    # Avant la règle « message court » : « source ? » ferait 8 caractères.
    if detect_web_search_intent(message):
        return CognitiveOperation.WEB_SEARCH

    # ── 4. Heuristique génération image ─────────────────────────────────────
    if detect_image_generation_intent(message):
        return CognitiveOperation.IMAGE_GENERATION

    # ── 5. Message court → CONFIRMATION ────────────────────────────────────
    # Les salutations ("Salut", "Ok"), réponses brèves ("Les deux", "Oui"),
    # et continuations contextuelles ne doivent pas créer d'intent.
    # CONFIRMATION est routé vers llm_router mais n'implique pas de création
    # d'intent dans LLMExecutionRouter (recall_decision.action != "create").
    if len(message.strip()) <= MIN_MESSAGE_LENGTH:
        return CognitiveOperation.CONFIRMATION

    # ── 6. Cache MemPalace ───────────────────────────────────────────────────
    cached = _search_cache(message, bridge)
    if cached:
        return cached

    # ── 7. Classifieur LLM ───────────────────────────────────────────────────
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
        from logger import get_logger
        log = get_logger(__name__)
        log.error("[CLASSIFIER ERROR] : %s", e)
        return CognitiveOperation.UNKNOWN


# =========================================================
# CACHE
# =========================================================

def store_confirmed_operation(message: str, operation: CognitiveOperation):
    """Stocke un mapping confirmé explicitement par l'utilisateur."""
    _store_cache(message, operation, confirmed=True)


def _search_cache(
    message: str,
    bridge: MempalaceBridge | None,
) -> CognitiveOperation | None:
    """
    Recherche un pattern similaire dans le cache classifier via MempalaceBridge.

    Schéma post-T2 sprint 5 (fix dette #20) : l'operation est portée par
    hit["room"] (cf. docs/sprint5/audit_cache_classifier.md). Plus de
    json.loads sur le document — le hit propage `room` via le wrapper
    mempalace.searcher.search_memories sans transformation custom.

    Seuil strict (0.92) appliqué côté caller — le bridge est appelé avec
    max_distance=None pour ne pas rejeter les hits de l'aria_classifier
    avant que le seuil métier puisse les évaluer.
    """
    if bridge is None:
        return None
    try:
        result = bridge.retrieve_memories(
            query=message,
            wing="aria_classifier",
            n=1,
            max_distance=None,
        )
        hits = result.get("hits", [])
        if not hits:
            log.debug("classifier cache MISS empty for %r", message[:50])
            return None

        hit = hits[0]
        sim = hit.get("similarity", 0)
        if sim < 0.92:
            log.debug(
                "classifier cache MISS sim=%.3f for %r",
                sim, message[:50],
            )
            return None

        op = _parse_operation(hit.get("room", "unknown"))
        log.info(
            "classifier cache HIT sim=%.3f op=%s for %r",
            sim, op.value, message[:50],
        )
        return op

    except Exception as e:
        log.warning("classifier cache error: %s", e)
        return None


def _store_cache(message: str, operation: CognitiveOperation, confirmed: bool = False):
    """Stocke un mapping message → operation dans le cache classifier."""
    try:
        write_classifier_cache(message, operation.value, confirmed=confirmed)
    except Exception as e:
        from logger import get_logger
        log = get_logger(__name__)
        log.error("[CLASSIFIER STORE ERROR] : %s", e)


# =========================================================
# HELPERS
# =========================================================

def _parse_operation(s: str) -> CognitiveOperation:
    """Convertit une string en CognitiveOperation, UNKNOWN si invalide."""
    try:
        return CognitiveOperation(s.lower())
    except ValueError:
        return CognitiveOperation.UNKNOWN