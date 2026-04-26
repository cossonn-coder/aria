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
#
# Sprint 0.2 : _handle_generation() enrichit le prompt avec
#   - les intents actifs (triés par salience)
#   - les souvenirs épisodiques pertinents (retrieve_memories)

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from memory.mempalace_writer import store_image_artifact


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    Args:
        internal_router : llm.image_router.ImageRouter (vision + génération)
        intent_engine   : IntentEngine — accès aux intents actifs (optionnel)
        mempalace_bridge: MempalaceBridge — recall épisodique (optionnel)

    intent_engine et mempalace_bridge sont optionnels pour rester
    compatibles avec les tests qui n'injectent que internal_router.
    """

    def __init__(self, internal_router, intent_engine=None, mempalace_bridge=None):
        self.internal_router = internal_router
        self.intent_engine = intent_engine
        self.mempalace_bridge = mempalace_bridge

    def execute(self, payload: dict) -> dict:
        op_type = payload.get("op_type", "")
        content = payload.get("content")

        if op_type == CognitiveOperation.IMAGE_INPUT.value:
            return self._handle_input(content, payload)

        if op_type == CognitiveOperation.IMAGE_GENERATION.value:
            return self._handle_generation(content, payload)

        raise ValueError(f"ImageExecutionRouter: op_type inconnu '{op_type}'")

    # =========================================================
    # IMAGE INPUT — inchangé
    # =========================================================

    def _handle_input(self, content, payload: dict) -> dict:
        file_path = content.get("file_path") if isinstance(content, dict) else content
        user_caption = content.get("caption") if isinstance(content, dict) else None

        artifact = self.internal_router.handle_input(
            ImageInput(path=str(file_path), caption=user_caption)
        )

        intent_id = payload.get("metadata", {}).get("intent_id")
        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            print(f"[MEMORY WRITE ERROR] image_input: {e}")

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": artifact.caption or "",
        }

    # =========================================================
    # IMAGE GENERATION — enrichi sprint 0.2
    # =========================================================

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis un prompt enrichi par le contexte cognitif.

        Flux :
            1. Extraction du prompt brut (message utilisateur)
            2. Construction du contexte : intents actifs + mémoire épisodique
            3. Enrichissement du prompt si contexte disponible
            4. Génération via ImageRouter
            5. Stockage épisodique
            6. Retour du path pour Telegram
        """
        raw_prompt = content if isinstance(content, str) else str(content)
        intent_id = payload.get("metadata", {}).get("intent_id")

        # ── Enrichissement du prompt ─────────────────────────────────────────
        context_block = self._build_generation_context(raw_prompt)
        enriched_prompt = _inject_context(raw_prompt, context_block)

        artifact = self.internal_router.generate(
            message=enriched_prompt,
            intent_id=intent_id,
        )

        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            print(f"[MEMORY WRITE ERROR] image_generation: {e}")

        return {
            "path": artifact.path,
            "caption": artifact.caption,
            "text": artifact.path,
        }

    # =========================================================
    # CONTEXT BUILDER (privé)
    # =========================================================

    def _build_generation_context(self, prompt: str) -> str:
        """
        Assemble le contexte cognitif disponible pour enrichir le prompt image.

        Retourne une chaîne vide si aucune information utile n'est disponible,
        ce qui évite d'injecter du bruit dans le prompt de génération.

        Deux sources :
        - Intents actifs (triés par salience décroissante, max 3)
        - Mémoire épisodique pertinente (max 3 souvenirs)
        """
        parts = []

        # ── Intents actifs ───────────────────────────────────────────────────
        if self.intent_engine is not None:
            active = self.intent_engine.list_attention_active()
            # Trier par salience décroissante, garder les 3 plus saillants
            active_sorted = sorted(
                active,
                key=lambda i: getattr(i, "salience", 0.0),
                reverse=True,
            )[:3]

            if active_sorted:
                intent_lines = [f"- {i.name}" for i in active_sorted]
                parts.append("Projets actifs de l'utilisateur :\n" + "\n".join(intent_lines))

        # ── Mémoire épisodique ───────────────────────────────────────────────
        if self.mempalace_bridge is not None:
            try:
                memories = self.mempalace_bridge.retrieve_memories(
                    query=prompt,
                    n=3,
                )
                if memories:
                    mem_lines = [f"- {m}" for m in memories]
                    parts.append("Souvenirs pertinents :\n" + "\n".join(mem_lines))
            except Exception as e:
                print(f"[CONTEXT BUILD ERROR] episodic recall: {e}")

        return "\n\n".join(parts)


# =========================================================
# HELPERS
# =========================================================

def _inject_context(prompt: str, context: str) -> str:
    """
    Injecte le contexte cognitif dans le prompt de génération.

    Si le contexte est vide, retourne le prompt original sans modification.
    Le contexte est placé AVANT le prompt pour que le modèle le traite
    comme information de fond plutôt que comme contrainte directe.

    Format :
        [Contexte : ...]

        <prompt utilisateur>
    """
    if not context.strip():
        return prompt

    return f"[Contexte :\n{context}]\n\n{prompt}"