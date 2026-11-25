# aria/llm/image_router.py
#
# Facade image du kernel cognitif.
#
# Responsabilité : router les opérations image vers les bons providers,
# avec fallback automatique dans l'ordre des routing tables.
#
# Deux capacités distinctes :
#   handle_input() → analyse d'une image reçue (vision → caption textuelle)
#   generate()     → génération d'une image depuis un prompt texte
#
# Ce module ne connaît pas MemPalace, ni IntentEngine, ni le kernel.
# Il reçoit des ImageInput, retourne des ImageArtifact. C'est tout.
#
# Pattern identique à LLMRouter : fallback automatique, clients injectables.

from images.image_types import ImageArtifact, ImageInput
from config import config
from llm.vision.groq_vision import GroqVisionClient
from llm.vision.gemini_vision import GeminiVisionClient
from llm.image_gen.pollinations_client import PollinationsClient
from logger import get_logger

log = get_logger(__name__)


# ── Routing tables ────────────────────────────────────────────────────────────
#
# Ordre = priorité. Le dispatcher essaie chaque entrée dans l'ordre
# et passe au suivant en cas d'exception (rate limit, timeout, etc.).

VISION_ROUTING_TABLE = [
    # groq ×3 d'abord.
    {
        "provider": "groq1",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key,
    },
    {
        "provider": "groq2",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key_2,
    },
    {
        "provider": "groq3",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key_3,
    },
    # DeepSeek en dernier depuis le 2026-11-25 (crédit épuisé) ; il était en premier
    # depuis le sprint 19 : descriptions plus justes que groq
    # qwen3.8, qui décrit souvent une photo unique comme plusieurs vues.
    # API compatible OpenAI, donc le client générique GroqVisionClient
    # suffit. Le raisonnement est coupé : sans ça, deepseek-flash consomme
    # ~900 tokens à réfléchir et la réponse visible est tronquée.
    {
        "provider": "deepseek",
        "client": GroqVisionClient,
        "model": config.deepseek_model,
        "base_url": "https://api.deepseek.com/chat/completions",
        "api_key": lambda: config.deepseek_api_key,
        "extra": {"thinking": {"type": "disabled"}},
    },
]

# Lecture d'une position d'échecs (sprint 59) : Gemini seul, la chaîne vision
# prod lit faux. 3.8-flash est juste mais souvent en 503 : il passe en second.
BOARD_ROUTING_TABLE = [
    {
        "provider": "gemini-3.5-flash",
        "client": GeminiVisionClient,
        "model": "gemini-3.5-flash",
        "api_key": lambda: config.gemini_api_key,
    },
    {
        "provider": "gemini-3.8-flash",
        "client": GeminiVisionClient,
        "model": "gemini-3.8-flash",
        "api_key": lambda: config.gemini_api_key,
    },
]

GENERATION_ROUTING_TABLE = [
    # Pollinations avec la clé de Nico (sprint 24) : sans filigrane.
    # Clé vide → le client lève, on tombe sur le secours anonyme.
    {
        "provider": "pollinations_key",
        "client": PollinationsClient,
        "base_url": "https://gen.pollinations.ai",
        "model": "tongyi-mai/z-image-turbo",
        "api_key": lambda: config.pollination_api_key,
    },
    # Secours : Pollinations anonyme (filigrane, 1 image / 45 s).
    {
        "provider": "pollinations_anon",
        "client": PollinationsClient,
        "base_url": "https://image.pollinations.ai",
    },
]


# ── Consignes OCR (sprint 42) ────────────────────────────────────────────────

# Ajoutée aux deux prompts de description : le texte lisible d'une photo
# (capture d'écran, ticket…) est recopié dans le même appel vision.
_TEXT_COPY_RULE = (
    "S'il y a du texte lisible (document, capture d'écran, ticket, panneau…), "
    "recopie-le intégralement à la fin, après « Texte : »."
)

# Consigne de transcription pure, pour les pages scannées d'un PDF.
_TRANSCRIBE_PROMPT = (
    "Transcris intégralement et fidèlement tout le texte visible, dans sa "
    "langue d'origine, sans résumer ni commenter. S'il n'y a aucun texte, "
    "réponds exactement : AUCUN TEXTE."
)
_NO_TEXT = "AUCUN TEXTE"


# ── Lecture d'échiquier (sprint 59) ──────────────────────────────────────────

# Consigne mesurée à l'audit : grille telle qu'affichée, sans interprétation.
_BOARD_PROMPT = (
    "Cette image montre un échiquier. Lis les 8 rangées TELLES QU'AFFICHÉES, "
    "de la rangée du haut à celle du bas, chaque rangée de gauche à droite. "
    "Pour chaque case : lettre de pièce (K Q R B N P pour les pièces blanches, "
    "k q r b n p pour les noires) ou '.' si vide. "
    "Réponds UNIQUEMENT par 8 lignes de 8 caractères."
)
_BOARD_CHARS = set("KQRBNPkqrbnp.")


def _parse_grid(text: str) -> list[str] | None:
    """Extrait 8 rangées de 8 cases d'une réponse ; None si non conforme."""
    # Les lignes de clôture ``` (avec ou sans langage) sont ignorées.
    rows = [
        line.strip() for line in text.splitlines()
        if line.strip() and not line.strip().startswith("```")
    ]
    if len(rows) != 8:
        return None
    if any(len(row) != 8 or not set(row) <= _BOARD_CHARS for row in rows):
        return None
    return rows


# ── Router ────────────────────────────────────────────────────────────────────

class ImageRouter:
    """
    Facade image — délègue aux providers via routing tables avec fallback.

    Injection de dépendances pour la testabilité :
        ImageRouter(vision_table=[FakeVision()]) → tests unitaires sans réseau
    """

    def __init__(
        self,
        vision_table=None,
        generation_table=None,
        board_table=None,
    ):
        self.vision_table = vision_table or VISION_ROUTING_TABLE
        self.generation_table = generation_table or GENERATION_ROUTING_TABLE
        self.board_table = board_table or BOARD_ROUTING_TABLE

    def handle_input(self, image_input: ImageInput) -> ImageArtifact:
        """
        Analyse une image et retourne une description textuelle.

        Contextalisation du prompt :
            Si l'utilisateur a accompagné son image d'un texte (caption),
            ce contexte est injecté dans le prompt vision. Cela permet au
            modèle de répondre à l'intention réelle de l'utilisateur plutôt
            que de produire une description générique de la scène.

            Exemple :
                Sans caption → "A green plant in a pot on a wooden table."
                Avec "c'est la courge plantée en mars" →
                    "La courge semble bien développée pour mars,
                     les feuilles sont saines..."

        Args:
            image_input: ImageInput avec path ou base64, et optionnellement
                         une caption utilisateur.

        Returns:
            ImageArtifact avec la description produite par le modèle de vision.
        """
        source = image_input.path or image_input.base64

        # Construction du prompt : générique ou contextualisé selon la caption.
        # La caption utilisateur devient le cadre interprétatif de l'analyse.
        if image_input.caption:
            # Règle de langue : français par défaut, sinon la langue de la légende.
            prompt = (
                f"L'utilisateur a envoyé cette image avec le message : "
                f"« {image_input.caption} »\n"
                f"Réponds en tenant compte de ce contexte, en quelques phrases. "
                f"N'affirme rien qui ne soit visible sur l'image ; si tu n'es pas "
                f"sûr de ce qu'est un élément ou un lieu, dis-le au lieu de deviner. "
                f"Réponds en français, sauf si le message de l'utilisateur est "
                f"dans une autre langue.\n"
                f"Language rule: if the user's message is not in French, write "
                f"your whole answer in the language of that message.\n"
                f"{_TEXT_COPY_RULE}"
            )
        else:
            # Prompt de description sobre : court, en français, anti-invention.
            prompt = (
                "Décris cette photo en français, en quelques phrases : sujet "
                "principal, contexte, éléments notables. Ne décris que ce qui est "
                "visible ; si tu n'es pas sûr de ce qu'est un élément ou un lieu, "
                "dis-le au lieu de deviner.\n"
                f"{_TEXT_COPY_RULE}"
            )

        caption = self._run_vision(source, prompt=prompt)

        return ImageArtifact(
            source=image_input.source,
            path=image_input.path,
            caption=caption,
            metadata={
                # On conserve la caption originale de l'utilisateur
                # pour traçabilité et éventuel stockage mémoire
                "user_caption": image_input.caption or "",
            },
        )

    def transcribe(self, image) -> str:
        """
        Transcrit le texte visible d'une image (OCR par la chaîne vision).

        Args:
            image: chemin local, URL ou data URL de l'image.

        Returns:
            Le texte transcrit, ou "" si le modèle répond « AUCUN TEXTE ».
        """
        text = self._run_vision(image, prompt=_TRANSCRIBE_PROMPT).strip()
        return "" if text.rstrip(".") == _NO_TEXT else text

    def read_board(self, image) -> list[str] | None:
        """
        Lit la grille d'un échiquier en image, telle qu'affichée.

        Args:
            image: chemin local de l'image.

        Returns:
            8 chaînes de 8 caractères (rangée du haut d'abord, chaque rangée de
            gauche à droite ; KQRBNP blancs, kqrbnp noirs, '.' vide), ou None
            si aucun modèle n'a rendu une grille valide.
        """
        # Une entrée à la fois : une réponse non conforme compte comme un échec
        # et fait passer au modèle suivant, comme une exception réseau.
        for entry in self.board_table:
            try:
                text = self._dispatch([entry], "describe", image=image, prompt=_BOARD_PROMPT)
            except RuntimeError:
                continue
            rows = _parse_grid(text)
            if rows is not None:
                return rows
            log.warning("[BOARD] %s : grille non conforme.", entry.get("provider"))
        return None

    def generate(self, message: str, intent_id: str | None = None) -> ImageArtifact:
        """
        Génère une image depuis un prompt texte.

        Args:
            message   : prompt de génération (message brut de l'utilisateur)
            intent_id : intent cognitif associé — pour lier l'image à un projet

        Returns:
            ImageArtifact avec le chemin du fichier généré.
        """
        result = self._run_generation(message)

        return ImageArtifact(
            source="generated",
            path=result.path,
            caption=result.caption,
            prompt=message,
            intent_id=intent_id,
            metadata={},
        )

    # ── Dispatch interne ─────────────────────────────────────────────────────

    def _dispatch(self, table, method, **kwargs):
        """
        Dispatcher générique avec fallback automatique.

        Itère sur la routing table dans l'ordre.
        En cas d'exception (réseau, rate limit, timeout),
        passe au provider suivant sans interrompre le pipeline.

        Lève RuntimeError si tous les providers échouent.
        """
        last_error = None

        for entry in table:
            try:
                client = entry["client"](
                    base_url=entry.get("base_url"),
                    model=entry.get("model"),
                    models=entry.get("models"),
                    api_key=entry.get("api_key", lambda: None)(),
                    output_dir=config.image_output_dir,
                    extra=entry.get("extra"),
                )
                result = getattr(client, method)(**kwargs)
                # Log du fournisseur qui a servi, pour lecture en run live.
                if method == "describe":
                    log.info("[VISION] %s (%s) a répondu.", entry.get("provider"), entry.get("model"))
                else:
                    log.info("[IMAGE GEN] %s a répondu.", entry.get("provider"))
                return result

            except Exception as e:
                log.warning("[IMAGE ROUTER FALLBACK] %s failed: %s", entry.get("provider"), e)
                last_error = e

        raise RuntimeError(
            f"All image providers failed. Last error: {last_error}"
        )

    def _run_vision(self, image, prompt: str) -> str:
        return self._dispatch(
            self.vision_table,
            "describe",
            image=image,
            prompt=prompt,
        )

    def _run_generation(self, prompt: str):
        return self._dispatch(
            self.generation_table,
            "generate",
            prompt=prompt,
        )