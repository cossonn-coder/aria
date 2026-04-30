# aria/execution/routers/image_router.py
#
# Router d'exécution pour les opérations image.
#
# Gère deux sous-cas distincts via le champ op_type du payload :
#   IMAGE_INPUT      → analyse d'une image reçue (vision → description texte)
#   IMAGE_GENERATION → génération d'une image depuis un prompt texte
#
# Contrat de sortie strict (règle commune à tous les routers) :
#   IMAGE_INPUT      → {"text": str}              — description vision
#   IMAGE_GENERATION → {"path": str, "caption": str} — image générée
#   Jamais : {"status": ...} — c'est le rôle exclusif du dispatcher.
#
# Pipeline IMAGE_INPUT — deux modes :
#
#   Mode standard (caption descriptive ou absente) :
#     photo → vision → {"text": description brute}
#
#   Mode enrichi (caption interrogative : "c'est quoi ?", "tu reconnais ?") :
#     photo → vision → description injectée dans LLMExecutionRouter
#              → réponse enrichie par mémoire + intents actifs
#
#   Le mode est détecté dans _handle_input() via is_interrogative_caption().
#   is_interrogative_caption() est la source de vérité — pas le kernel,
#   pas CognitiveResult — pour éviter de toucher kernel.py.
#
# Activation du mode enrichi :
#   Nécessite llm_execution_router injecté au constructeur.
#   Sans lui, _handle_input() retourne toujours la description brute
#   (dégradation gracieuse).
#
# Responsabilités :
#   - Transmettre la caption utilisateur au modèle de vision
#   - Enrichir le prompt de génération avec intents + mémoire épisodique
#   - Stocker chaque artefact image dans la mémoire épisodique (aria_episodic)
#
# Règle d'architecture :
#   Ce router est le seul point d'écriture mémoire pour les images.
#   Aucun client vision, aucun client génération n'écrit en mémoire.

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_classifier import is_interrogative_caption
from memory.mempalace_writer import store_image_artifact


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    Args:
        internal_router      : llm.image_router.ImageRouter (vision + génération)
        intent_engine        : IntentEngine — accès aux intents actifs (optionnel)
        mempalace_bridge     : MempalaceBridge — recall épisodique (optionnel)
        llm_execution_router : LLMExecutionRouter — pipeline cognitif texte (optionnel)
                               Requis pour le mode enrichi (caption interrogative).
                               Sans lui, IMAGE_INPUT retourne toujours la description brute.
    """

    def __init__(
        self,
        internal_router,
        intent_engine=None,
        mempalace_bridge=None,
        llm_execution_router=None,
    ):
        self.internal_router      = internal_router
        self.intent_engine        = intent_engine
        self.mempalace_bridge     = mempalace_bridge
        self.llm_execution_router = llm_execution_router

    def execute(self, payload: dict) -> dict:
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
        Analyse une image reçue via la couche vision.

        Deux modes selon la caption :

        Mode standard — caption absente ou descriptive ("substrats usés") :
            → retourne {"text": description_vision}

        Mode enrichi — caption interrogative ("c'est quoi ?", "tu reconnais ?") :
            → description vision injectée dans LLMExecutionRouter comme contexte
            → retourne {"text": réponse_enrichie_mémoire_intents}
            → nécessite llm_execution_router injecté au constructeur

        Contrat de sortie : {"text": str} dans les deux cas.

        Pourquoi pas {"path": ...} ici ?
            artifact.path est le chemin local du fichier reçu, pas un résultat
            à renvoyer à l'utilisateur. Retourner ce path déclencherait
            _normalize() en mode image et ferait envoyer la photo d'origine
            par Telegram au lieu de la description vision.
        """
        file_path    = content.get("file_path") if isinstance(content, dict) else content
        user_caption = content.get("caption")   if isinstance(content, dict) else None

        artifact = self.internal_router.handle_input(
            ImageInput(path=str(file_path), caption=user_caption)
        )

        intent_id = payload.get("metadata", {}).get("intent_id")
        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            from logger import get_logger
            log = get_logger(__name__)
            log.error("memory write error: %s", e)

        # ── Mode enrichi : caption interrogative + LLM router disponible ────
        # is_interrogative_caption() est réévalué ici (source de vérité locale).
        # Pas de dépendance au flag CognitiveResult.interrogative du kernel —
        # évite le couplage et simplifie les tests.
        if is_interrogative_caption(user_caption) and self.llm_execution_router is not None:
            vision_text = artifact.caption or ""
            if vision_text:
                return self._handle_input_enriched(
                    vision_text=vision_text,
                    user_caption=user_caption,
                    payload=payload,
                )

        # Mode standard : description vision brute
        return {"text": artifact.caption or ""}

    def _handle_input_enriched(
        self,
        vision_text: str,
        user_caption: str,
        payload: dict,
    ) -> dict:
        """
        Pipeline vision enrichi pour les captions interrogatives.

        Injecte la description vision comme contexte factuel dans
        LLMExecutionRouter pour bénéficier de la mémoire + intents actifs.

        Pourquoi REASONING et pas FACT_RECALL ?
            TOP_K REASONING = 8 vs FACT_RECALL = 3.
            Une question sur une image peut mobiliser des souvenirs variés
            (jardinage, santé, activités) — le budget mémoire large est justifié.
            REASONING est aussi le rôle LLM le plus puissant (Cerebras qwen-3-235b).

        Format du message injecté :
            [Analyse visuelle : <description modèle vision>]

            <question originale de l'utilisateur>

        Le bloc [Analyse visuelle] donne au LLM les faits visuels bruts.
        La question utilisateur oriente l'angle de réponse.
        La mémoire + intents enrichissent le contexte personnel.
        """
        enriched_message = (
            f"[Analyse visuelle : {vision_text}]\n\n"
            f"{user_caption}"
        )

        from logger import get_logger
        log = get_logger(__name__)
        log.error("[IMAGE ENRICHED] caption interrogative → LLMExecutionRouter REASONING")

        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched_message,
            "metadata": payload.get("metadata", {}),
        })

    # =========================================================
    # IMAGE GENERATION
    # =========================================================

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis un prompt enrichi par le contexte cognitif.

        Contrat de sortie : {"path": str, "caption": str}
        _normalize() détecte l'extension image dans path et route vers send_photo().

        Flux :
            1. Extraction du prompt brut (message utilisateur)
            2. Construction du contexte : intents actifs + mémoire épisodique
            3. Enrichissement du prompt (pour le générateur uniquement)
            4. Génération via ImageRouter
            5. Stockage épisodique
            6. Retour path + caption basée sur raw_prompt (pas le prompt enrichi)

        Pourquoi séparer raw_prompt et enriched_prompt pour la caption ?
            Le bloc [Contexte :...] est multi-lignes et peut dépasser 100 chars.
            L'afficher dans la caption Telegram produit un texte debug illisible
            tronqué à 79 chars. La caption doit refléter l'intention utilisateur,
            pas le contexte cognitif interne.
        """
        raw_prompt = content if isinstance(content, str) else str(content)
        intent_id  = payload.get("metadata", {}).get("intent_id")

        # ── Enrichissement du prompt pour le générateur ──────────────────────
        # raw_prompt est conservé séparément pour la caption finale.
        context_block   = self._build_generation_context(raw_prompt)
        enriched_prompt = _inject_context(raw_prompt, context_block)

        artifact = self.internal_router.generate(
            message=enriched_prompt,
            intent_id=intent_id,
        )

        # Stockage épisodique — non bloquant
        try:
            store_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            from logger import get_logger
            log = get_logger(__name__)
            log.error("memory write error: %s", e)

        # Caption basée sur raw_prompt — lisible, sans le bloc contexte interne.
        caption = raw_prompt[:100] if raw_prompt else artifact.caption or ""

        return {
            "path"    : artifact.path,
            "caption" : caption,
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
                hits = memories.get("hits", [])
                if hits:
                    mem_lines = [f"- {h.get('text', '')}" for h in hits if h.get("text")]
                    if mem_lines:
                        parts.append("Souvenirs pertinents :\n" + "\n".join(mem_lines))
            except Exception as e:
                from logger import get_logger
                log = get_logger(__name__)
                log.error("[CONTEXT BUILD ERROR] episodic recall: %s", e)

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
        [Contexte :
        ...]

        <prompt utilisateur>
    """
    if not context.strip():
        return prompt

    return f"[Contexte :\n{context}]\n\n{prompt}"