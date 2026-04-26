# aria/execution/routers/image_router.py
#
# Router d'exécution pour les opérations image.
#
# Gère deux sous-cas distincts via le champ op_type du payload :
#   - IMAGE_INPUT      : analyse d'une image reçue (vision → caption en français)
#   - IMAGE_GENERATION : génération d'une image depuis un prompt utilisateur
#
# Traduction de prompt :
#   Les modèles de génération image (Pollinations, FLUX, etc.) produisent
#   de meilleurs résultats avec des prompts en anglais détaillés.
#   _enhance_prompt() traduit et enrichit le prompt FR → EN via LLM
#   avant d'appeler le router de génération.
#
# Ce router est un effecteur pur : pas de logique cognitive,
# pas d'accès mémoire. Il reçoit, traduit si besoin, génère, retourne.

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from llm.llm_role import LLMRole


# Prompt système pour la traduction et l'enrichissement du prompt image.
# On demande un prompt anglais optimisé pour les modèles text-to-image :
# style, éclairage, composition, qualité — sans aucun texte superflu.
_PROMPT_ENHANCER = """Tu es un expert en génération d'images par IA.
Transforme la demande suivante en un prompt optimisé en anglais \
pour un modèle text-to-image (Stable Diffusion, FLUX, etc.).

Règles :
- Réponds UNIQUEMENT avec le prompt en anglais
- Inclus le sujet, le style, l'éclairage, la composition, la qualité
- Pas d'explication, pas de guillemets, pas de ponctuation finale

Demande : {message}"""


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    llm_router       : utilisé pour traduire/enrichir les prompts FR→EN
    internal_router  : llm.image_router.ImageRouter (vision + génération)
    """

    def __init__(self, internal_router, llm_router=None):
        self.internal_router = internal_router
        # llm_router optionnel — sans lui le prompt est passé tel quel
        self.llm_router = llm_router

    def execute(self, payload: dict) -> dict:
        """
        Dispatche vers handle_input ou generate selon op_type.

        payload attendu :
            op_type  : "image_input" | "image_generation"
            content  : str (prompt) ou dict {"file_path": ..., "caption": ...}
            metadata : dict passé depuis l'Event
        """
        op_type = payload.get("op_type", "")
        content = payload.get("content")

        if op_type == CognitiveOperation.IMAGE_INPUT.value:
            return self._handle_input(content, payload)

        if op_type == CognitiveOperation.IMAGE_GENERATION.value:
            return self._handle_generation(content, payload)

        raise ValueError(f"ImageExecutionRouter: op_type inconnu '{op_type}'")

    # =========================================================
    # IMAGE INPUT
    # =========================================================

    def _handle_input(self, content, payload: dict) -> dict:
        """
        Analyse une image reçue via Groq vision.
        La description est demandée en français.
        """
        file_path = content.get("file_path") if isinstance(content, dict) else content
        user_caption = content.get("caption") if isinstance(content, dict) else None

        artifact = self.internal_router.handle_input(
            ImageInput(path=str(file_path)),
        )

        response = artifact.caption or ""
        if user_caption:
            response = f"{response}\n\n(Message : {user_caption})"

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": response,
        }

    # =========================================================
    # IMAGE GENERATION
    # =========================================================

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis un prompt utilisateur.

        Flux :
            message FR → _enhance_prompt() → prompt EN enrichi
                       → InternalImageRouter.generate()
                       → ImageArtifact
        """
        user_message = content if isinstance(content, str) else str(content)
        intent_id = payload.get("metadata", {}).get("intent_id")

        # Traduction + enrichissement FR → EN avant génération
        enhanced_prompt = self._enhance_prompt(user_message)

        artifact = self.internal_router.generate(
            message=enhanced_prompt,
            intent_id=intent_id,
        )

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": artifact.path,
        }

    def _enhance_prompt(self, message: str) -> str:
        """
        Traduit et enrichit un prompt utilisateur en anglais optimisé
        pour les modèles de génération image.

        Sans llm_router : retourne le message original (mode dégradé).
        En cas d'erreur LLM : idem, on ne bloque jamais la génération.
        """
        if self.llm_router is None:
            return message

        try:
            response = self.llm_router.complete(
                prompt=_PROMPT_ENHANCER.format(message=message),
                role=LLMRole.CHAT,
                temperature=0.7,
                max_tokens=150,
            )
            enhanced = response.content.strip()
            print(f"[IMAGE PROMPT] '{message}' → '{enhanced}'")
            return enhanced

        except Exception as e:
            print(f"[IMAGE PROMPT] enhancement failed, using original: {e}")
            return message