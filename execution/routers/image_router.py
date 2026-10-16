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
#     photo → vision → {"text": description brute} + tours écrits dans aria_conversation
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
#   - Générer une image depuis le message brut (sans bloc de contexte, sprint 24)
#   - Stocker chaque artefact image dans la mémoire épisodique (aria_episodic)
#
# Règle d'architecture :
#   Ce router est le seul point d'écriture mémoire pour les images.
#   Aucun client vision, aucun client génération n'écrit en mémoire.

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_classifier import is_interrogative_caption
from memory.writer import write_image_artifact, write_conversation_turn
from logger import get_logger

log = get_logger(__name__)


class ImageExecutionRouter(BaseRouter):
    """
    Effecteur image du pipeline d'exécution.

    Args:
        internal_router      : llm.image_router.ImageRouter (vision + génération)
        intent_engine        : IntentEngine — passé par le kernel, inutilisé
                               depuis le sprint 24 (génération sans contexte)
        mempalace_bridge     : MempalaceBridge — idem, inutilisé depuis le sprint 24
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
            → retourne {"text": description_vision}, écrite dans aria_conversation (#57)

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
            write_image_artifact(artifact, intent_id=intent_id)
            log.info("image_write OK wing=aria_episodic intent_id=%s", intent_id)
        except Exception as e:
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

        # Mode standard : description vision brute.
        # Historique conversationnel (#57) : sans cette écriture, une relance
        # texte (« évalue la position ») ne voit pas la photo. Format aligné
        # sur le mode enrichi (décision Q3) ; le mode enrichi écrit déjà via
        # LLMExecutionRouter, d'où l'écriture ici seulement. Non bloquante.
        description = artifact.caption or ""
        conversation_key = str(payload.get("metadata", {}).get("chat_id", "default"))
        user_turn = f"[Analyse visuelle : {description}]"
        if user_caption:
            user_turn += "\n\n" + user_caption
        try:
            write_conversation_turn(conversation_key, "user", user_turn)
            write_conversation_turn(conversation_key, "assistant", description)
            log.info("conversation_write OK key=%s", conversation_key)
        except Exception:
            log.exception("conversation_write ERROR key=%s", conversation_key)

        return {"text": description}

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
            REASONING est aussi le rôle LLM le plus puissant (DeepSeek deepseek-v4-pro
            en fallback après groq).

        Format du message injecté :
            [Analyse visuelle : <description modèle vision>]
            [Consigne : rattachement projet seulement si justifié, sinon silence]
            [Consigne : langue de la réponse (FR par défaut, sinon celle de la question)]
            Language rule: <même règle en anglais>

            <question originale de l'utilisateur>

        Le bloc [Analyse visuelle] donne au LLM les faits visuels bruts.
        La question utilisateur oriente l'angle de réponse.
        La mémoire + intents enrichissent le contexte personnel.
        """
        # Consigne anti-rattachement abusif (#51) : sans intent résolu, le
        # lien projet ne passe plus que par le contexte, et seulement s'il
        # est justifié par la description ; sinon le LLM doit se taire sur
        # les projets (sans quoi il commente l'absence de lien).
        # Consigne de langue : user.md impose le français, donc la règle
        # « langue de la question » doit être explicite ici. Ligne FR + ligne
        # EN, comme le prompt vision (la version FR seule n'a pas suffi).
        enriched_message = (
            f"[Analyse visuelle : {vision_text}]\n"
            f"[Consigne : ne rattache cette photo à un projet de Nico que si "
            f"la description le justifie clairement ; sinon, ne mentionne pas "
            f"ses projets.]\n"
            f"[Consigne : réponds en français, sauf si la question de "
            f"l'utilisateur est dans une autre langue : réponds alors dans "
            f"cette langue.]\n"
            f"Language rule: if the user's message is not in French, write "
            f"your whole answer in the language of that message.\n\n"
            f"{user_caption}"
        )

        log.info("[IMAGE ENRICHED] caption interrogative → LLMExecutionRouter REASONING")

        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched_message,
            # skip_intent : aucune résolution/mutation d'intent (#51)
            "metadata": {**payload.get("metadata", {}), "skip_intent": True},
        })

    # =========================================================
    # IMAGE GENERATION
    # =========================================================

    def _handle_generation(self, content, payload: dict) -> dict:
        """
        Génère une image depuis le message brut de l'utilisateur.

        Contrat de sortie : {"path": str, "caption": str}
        _normalize() détecte l'extension image dans path et route vers send_photo().

        Flux :
            1. Extraction du prompt brut (message utilisateur)
            2. Génération via ImageRouter, prompt brut tel quel
            3. Stockage épisodique (demande brute)
            4. Retour path + caption basée sur raw_prompt

        Pourquoi pas de bloc de contexte (intents, souvenirs) ?
            Sprint 24 : il polluait le prompt du générateur et la mémoire
            épisodique (auto-pollution, audit §3.4).
        """
        raw_prompt = content if isinstance(content, str) else str(content)
        intent_id  = payload.get("metadata", {}).get("intent_id")

        artifact = self.internal_router.generate(
            message=raw_prompt,
            intent_id=intent_id,
        )

        # Stockage épisodique — non bloquant
        try:
            write_image_artifact(artifact, intent_id=intent_id)
        except Exception as e:
            log.error("memory write error: %s", e)

        caption = raw_prompt[:100] if raw_prompt else artifact.caption or ""

        return {
            "path"    : artifact.path,
            "caption" : caption,
        }
