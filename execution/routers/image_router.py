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
#   Mode échecs (sprint 59, prioritaire) : image d'échiquier (is_chess_image) :
#     photo → grille (Gemini, sinon lecteur local) → FEN → Stockfish
#              → {"text": ligne + éval, "images": [diagramme]}, sans LLM
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

from pathlib import Path
from uuid import uuid4

import chess

from execution.routers.execution_base import BaseRouter
from images.image_types import ImageInput
from cognition.cognitive_context import CognitiveOperation
from cognition.cognitive_classifier import is_chess_image, is_interrogative_caption
from chess_coach import board_local
from chess_coach.board_reading import grid_to_fen, position_problem, solve
from chess_coach.render import render_position
from execution.routers.chess_router import _format_line
from memory.writer import write_image_artifact, write_conversation_turn
from config import config
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

        # ── Mode échecs (sprint 59) : prioritaire sur le mode enrichi ──────
        if is_chess_image(artifact.caption, user_caption):
            return self._handle_chess_board(str(file_path), artifact.caption or "",
                                            user_caption, payload)

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

    def _handle_chess_board(self, path: str, description: str,
                            user_caption: str | None, payload: dict) -> dict:
        """
        Résout une position d'échecs envoyée en image (sprint 59).

        Grille lue par Gemini, sinon par le lecteur local ; FEN déduite ;
        ligne principale Stockfish + évaluation + diagramme, sans LLM.
        Position illégale : raison + diagramme lu sans flèche, pas de résolution.
        """
        grid = self.internal_router.read_board(path)
        if grid is not None:
            log.info("[BOARD] gemini")
        else:
            grid = board_local.read_board(path)
            log.info("[BOARD] %s", "local" if grid is not None else "illisible")
        if grid is None:
            return {"text": f"Je n'arrive pas à lire l'échiquier : {description}"}

        fen, bottom = grid_to_fen(grid, user_caption)
        out_dir = Path(config.image_output_dir) / "chess"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"{uuid4().hex[:8]}_position.png")

        problem = position_problem(fen)
        if problem:
            log.info("[BOARD] position impossible : %s fen=%s", problem, fen)
            render_position(fen, bottom, None, out_path)
            text = (f"Je lis une position impossible ({problem}). Voici ce que j'ai lu : "
                    f"renvoie une image plus nette.\nPosition lue : {fen}")
            return {"text": text, "images": [{"path": out_path, "caption": ""}]}

        board = chess.Board(fen)
        score, pv = solve(fen)
        line = pv[:10]
        line_san, replay = [], board.copy()
        for move in line:
            line_san.append(replay.san(move))
            replay.push(move)

        side = "white" if board.turn == chess.WHITE else "black"
        names = {"white": "blancs", "black": "noirs"}
        other = "black" if side == "white" else "white"
        if score.is_mate():
            mate = score.mate()
            winner = side if mate > 0 else other
            evaluation = f"mat en {abs(mate)} pour les {names[winner]}"
        else:
            pawns = score.score() / 100
            winner = side if pawns >= 0 else other
            evaluation = f"+{abs(pawns):.1f}".replace(".", ",") + f" pour les {names[winner]}"

        text = (f"Trait aux {names[side]}. Position lue : {fen}\n"
                f"Ligne principale : {_format_line(line_san, board.fullmove_number, side)}\n"
                f"Évaluation : {evaluation}")
        ucis = [move.uci() for move in line[:4]]
        render_position(fen, bottom, ucis[0] if ucis else None, out_path,
                        best_line_uci=ucis)
        log.info("[BOARD] résolu fen=%s eval=%s", fen, evaluation)

        # Historique : une relance (« et si 1...Qe7+ ? ») doit voir la position.
        conversation_key = str(payload.get("metadata", {}).get("chat_id", "default"))
        user_turn = f"[Position d'échecs lue sur image : {fen}]"
        if user_caption:
            user_turn += "\n\n" + user_caption
        try:
            write_conversation_turn(conversation_key, "user", user_turn)
            write_conversation_turn(conversation_key, "assistant", text)
            log.info("conversation_write OK key=%s", conversation_key)
        except Exception:
            log.exception("conversation_write ERROR key=%s", conversation_key)

        return {"text": text, "images": [{"path": out_path, "caption": ""}]}

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
