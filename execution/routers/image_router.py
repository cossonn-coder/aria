# aria/execution/routers/image_router.py
#
# Router d'exécution pour les opérations image.
#
# Gère deux sous-cas distincts via le champ op_type du payload :
#   IMAGE_INPUT      → analyse d'une image reçue (vision → caption)
#   IMAGE_GENERATION → génération d'une image depuis un prompt texte
#
# Ce router est un effecteur pur : il reçoit un payload structuré,
# délègue à InternalImageRouter (llm/image_router.py), et retourne
# un dict de résultat.
#
# Responsabilités ajoutées (sprint 1.1) :
#   - Transmettre la caption utilisateur au modèle de vision
#   - Stocker chaque artefact image dans la mémoire épisodique (aria_episodic)
#
# Règle d'architecture :
#   Ce router est le seul point d'écriture mémoire pour les images.
#   Aucun client vision, aucun client génération n'écrit en mémoire.

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from memory.mempalace_writer import store_image_artifact


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    Reçoit le payload construit par AriaKernel et délègue
    à l'ImageRouter interne (llm/image_router.py).

    Args:
        internal_router : instance de llm.image_router.ImageRouter
                          Injecté par AriaKernel pour permettre le remplacement
                          en tests sans toucher le router lui-même.
    """

    def __init__(self, internal_router):
        self.internal_router = internal_router

    def execute(self, payload: dict) -> dict:
        """
        Dispatche vers handle_input ou generate selon op_type.

        payload attendu :
            op_type  : "image_input" | "image_generation"
            content  : str (prompt) ou dict {"file_path": ..., "caption": ...}
            metadata : dict passé depuis l'Event (peut contenir intent_id)
        """
        op_type = payload.get("op_type", "")
        content = payload.get("content")

        if op_type == CognitiveOperation.IMAGE_INPUT.value:
            return self._handle_input(content, payload)

        if op_type == CognitiveOperation.IMAGE_GENERATION.value:
            return self._handle_generation(content, payload)

        # Cas non attendu — on lève pour que ExecutionDispatcher capture l'erreur
        raise ValueError(f"ImageExecutionRouter: op_type inconnu '{op_type}'")

    def _handle_input(self, content, payload: dict) -> dict:
        """
        Analyse une image reçue (photo Telegram, fichier).

        Flux :
            1. Extraction du path et de la caption utilisateur
            2. Construction d'ImageInput avec la caption — elle sera
               injectée dans le prompt vision par ImageRouter
            3. Analyse par le modèle de vision
            4. Stockage en mémoire épisodique
            5. Retour du résultat

        content attendu : dict {"file_path": str, "caption": str | None}
        """
        file_path = content.get("file_path") if isinstance(content, dict) else content
        user_caption = content.get("caption") if isinstance(content, dict) else None

        # La caption est maintenant transmise à ImageInput.
        # ImageRouter l'injecte dans le prompt vision pour contextualiser
        # l'analyse — le modèle sait ce que l'utilisateur cherche à montrer.
        artifact = self.internal_router.handle_input(
            ImageInput(
                path=str(file_path),
                caption=user_caption,   # contexte utilisateur → prompt vision
            )
        )

        # ── Stockage mémoire épisodique ──────────────────────────────────────
        # On stocke l'artefact immédiatement après l'analyse.
        # La caption vision + caption utilisateur sont indexées ensemble
        # pour un recall sémantique riche ("ma courge", "jardin mars", etc.)
        intent_id = payload.get("metadata", {}).get("intent_id")
        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            # Erreur mémoire non bloquante — l'utilisateur reçoit quand même
            # la description de son image
            print(f"[MEMORY WRITE ERROR] image_input: {e}")

        # Construction de la réponse : description vision en premier,
        # puis rappel de la caption utilisateur si elle apporte du contexte
        # supplémentaire non couvert par l'analyse.
        response = artifact.caption or ""

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": response,
        }

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis un prompt texte.

        Flux :
            1. Extraction du prompt (message utilisateur)
            2. Génération via ImageRouter (Pollinations → HuggingFace)
            3. Stockage en mémoire épisodique (prompt indexé)
            4. Retour du path pour envoi Telegram

        content attendu : str (message utilisateur complet, déjà traduit EN)
        """
        prompt = content if isinstance(content, str) else str(content)
        intent_id = payload.get("metadata", {}).get("intent_id")

        artifact = self.internal_router.generate(
            message=prompt,
            intent_id=intent_id,
        )

        # ── Stockage mémoire épisodique ──────────────────────────────────────
        # Le prompt est ce qui sera indexé et retrouvable plus tard.
        # "dessine mon jardin en été" doit rester dans la mémoire d'ARIA
        # pour que "montre-moi les images de mon jardin" fonctionne.
        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            print(f"[MEMORY WRITE ERROR] image_generation: {e}")

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            # Telegram reçoit le path — TelegramInterface.send() l'envoie comme fichier
            "text": artifact.path,
        }