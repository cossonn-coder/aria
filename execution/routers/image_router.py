# aria/execution/routers/image_router.py
#
# Router d'exécution pour les opérations image.
#
# Gère deux sous-cas distincts via le champ op_type du payload :
#   - IMAGE_INPUT      : analyse d'une image reçue (vision → caption)
#   - IMAGE_GENERATION : génération d'une image depuis un prompt texte
#
# Ce router est un effecteur pur : il reçoit un payload structuré,
# délègue à InternalImageRouter (llm/image_router.py), et retourne
# un dict de résultat. Aucune logique cognitive ici.
#
# InternalImageRouter (llm/image_router.py) porte la routing table
# des providers (Groq vision, Pollinations, HuggingFace, etc.)

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    Reçoit le payload construit par AriaKernel._to_execution()
    et délègue à l'ImageRouter interne (llm/image_router.py).

    Retour :
        dict avec "path" et "caption" de l'ImageArtifact produit
    """

    def __init__(self, internal_router):
        # internal_router = instance de llm.image_router.ImageRouter
        # Injecté par AriaKernel pour permettre le remplacement en tests
        self.internal_router = internal_router

    def execute(self, payload: dict) -> dict:
        """
        Dispatche vers handle_input ou generate selon op_type.

        payload attendu :
            op_type  : "image_input" | "image_generation"
            content  : str (prompt texte) ou dict {"file_path": ..., "caption": ...}
            metadata : dict passé depuis l'Event
        """
        op_type = payload.get("op_type", "")
        content = payload.get("content")

        if op_type == CognitiveOperation.IMAGE_INPUT.value:
            return self._handle_input(content, payload)

        if op_type == CognitiveOperation.IMAGE_GENERATION.value:
            return self._handle_generation(content, payload)

        # Cas non attendu — on lève pour que l'ExecutionDispatcher capture l'erreur
        raise ValueError(f"ImageExecutionRouter: op_type inconnu '{op_type}'")

    def _handle_input(self, content, payload: dict) -> dict:
        """
        Analyse une image reçue (photo Telegram, fichier, etc.)

        content attendu : dict {"file_path": str, "caption": str|None}
        """
        file_path = content.get("file_path") if isinstance(content, dict) else content
        user_caption = content.get("caption") if isinstance(content, dict) else None

        artifact = self.internal_router.handle_input(
            ImageInput(path=str(file_path))
        )

        # On enrichit la caption avec celle de l'utilisateur si présente
        response = artifact.caption or ""
        if user_caption:
            response = f"{response}\n\n(Message : {user_caption})"

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": response,
        }

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis un prompt texte.

        content attendu : str (le message utilisateur complet)
        """
        prompt = content if isinstance(content, str) else str(content)
        intent_id = payload.get("metadata", {}).get("intent_id")

        artifact = self.internal_router.generate(
            message=prompt,
            intent_id=intent_id,
        )

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": artifact.path,   # Telegram recevra le path — l'interface l'envoie comme fichier
        }