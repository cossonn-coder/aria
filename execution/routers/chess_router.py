# aria/execution/routers/chess_router.py
#
# Router d'exécution du coach d'échecs (sprint 26, tronçon 02).
#
# Pipeline CHESS_ANALYSIS :
#   PGN collé → chess_coach.analysis.analyze (Stockfish)
#   → un diagramme PNG par position critique (≤ 3, flèche = meilleur coup)
#   → message enrichi des faits moteur (notation française)
#   → LLMExecutionRouter en REASONING, SANS skip_intent : l'échange suit
#     le pipeline normal (intent + écriture épisodique), décision Q4.
#
# Contrat de retour : {"text": str, "images": [{"path", "caption"}, …]}.
#
# Règle d'architecture :
#   La seule écriture propre à ce router est la fiche de partie
#   (write_chess_game, tronçon 03), via memory/writer.py (règle 1).
#   L'échange lui-même est écrit par LLMExecutionRouter.

import hashlib
from pathlib import Path
from uuid import uuid4

from chess_coach.analysis import analyze
from chess_coach.notation import to_french
from chess_coach.render import render_position
from chess_coach.summary import summarize, summary_text
from config import config
from cognition.cognitive_context import CognitiveOperation
from execution.routers.execution_base import BaseRouter
from logger import get_logger
from memory.writer import write_chess_game

log = get_logger(__name__)

_COLOR_FR = {"white": "blancs", "black": "noirs"}

_SOURCE_FR = {
    "header": "pseudo dans l'en-tête",
    "message": "précisé dans le message",
    "default": "supposé par défaut",
}

_KIND_FR = {
    "a": "erreur de Nico",
    "b": "occasion manquée après erreur adverse",
    "c": "coup unique trouvé",
}

_PHASE_FR = {"opening": "ouverture", "middlegame": "milieu de partie", "endgame": "finale"}

_TAG_FR = {
    "capture": "prise", "check": "échec", "pawn": "coup de pion", "king": "coup de roi",
    "castle": "roque", "retreat": "recul", "hanging": "pièce en prise",
}

# Clés de compteurs (qualité PlyAnalysis) → libellé français, dans l'ordre affiché.
_QUALITY_FR = [
    ("best", "meilleurs"), ("correct", "corrects"), ("inaccuracy", "imprécisions"),
    ("mistake", "erreurs"), ("blunder", "gaffes"),
]


def _move_label(move_number: int, color: str, san: str) -> str:
    """« 17.Cg4+ » pour les blancs, « 17...Cg4+ » pour les noirs."""
    dots = "." if color == "white" else "..."
    return f"{move_number}{dots}{to_french(san)}"


def _format_line(pv_san: list, move_number: int, color: str) -> str:
    """Ligne principale numérotée en notation française (ex. « 17...Fd7 18.Cf3 Cc6 »)."""
    parts = []
    for i, san in enumerate(pv_san):
        if color == "white":
            parts.append(f"{move_number}.{to_french(san)}")
            color = "black"
        else:
            parts.append(f"{move_number}...{to_french(san)}" if i == 0 else to_french(san))
            color = "white"
            move_number += 1
    return " ".join(parts)


def _header_lines(headers: dict) -> list:
    """En-têtes utiles du PGN (valeurs « ? » ou absentes ignorées)."""
    def h(key):
        value = headers.get(key, "")
        return "" if value in ("", "?", "????.??.??") else value

    lines = []
    for color_key, label in (("White", "Blancs"), ("Black", "Noirs")):
        if h(color_key):
            elo = f" ({h(color_key + 'Elo')} Elo)" if h(color_key + "Elo") else ""
            lines.append(f"{label} : {h(color_key)}{elo}")
    if h("Date"):
        lines.append(f"Date : {h('Date')}")
    opening = " ".join(v for v in (h("ECO"), h("Opening")) if v)
    if opening:
        lines.append(f"Ouverture : {opening}")
    if h("Result"):
        lines.append(f"Résultat : {h('Result')}")
    return lines


def _caption(index: int, critical) -> str:
    p = critical.ply
    if critical.kind == "c":
        return (f"Position {index} — coup {p.move_number} : "
                f"{_move_label(p.move_number, p.color, p.san)}, seul bon coup — bien joué")
    return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
            f"joué {_move_label(p.move_number, p.color, p.san)}, "
            f"meilleur {_move_label(p.move_number, p.color, p.best_san)}")


class ChessExecutionRouter(BaseRouter):
    """
    Effecteur « coach d'échecs » du pipeline d'exécution.

    Args:
        llm_execution_router : LLMExecutionRouter — production de l'explication
    """

    def __init__(self, llm_execution_router):
        self.llm_execution_router = llm_execution_router

    def execute(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})

        analysis = analyze(message, message, config.chess_username, config.stockfish_path)
        if analysis is None:
            log.warning("chess_router PGN unreadable")
            return self.llm_execution_router.execute({
                "op_type" : CognitiveOperation.REASONING.value,
                "content" : f"[PGN illisible : dis-le à Nico en une phrase.]\n\n{message}",
                "metadata": metadata,
            })

        # ── Diagrammes : un PNG par position critique ────────────────────────
        out_dir = Path(config.image_output_dir) / "chess"
        out_dir.mkdir(parents=True, exist_ok=True)
        images = []
        for i, critical in enumerate(analysis.critical, 1):
            out_path = out_dir / f"{uuid4().hex[:8]}_{i}.png"
            render_position(critical.ply.fen_before, analysis.nico_color,
                            critical.ply.best_uci, str(out_path))
            images.append({"path": str(out_path), "caption": _caption(i, critical)})

        # ── Fiche de partie (non bloquante) ──────────────────────────────────
        # Hash des coups seuls (pas des en-têtes) : le même PGN recopié sans
        # en-têtes reste la même partie → même doc_id → la fiche est remplacée.
        game_hash = hashlib.sha256(
            "".join(p.uci for p in analysis.plies).encode()
        ).hexdigest()[:16]
        try:
            summary = summarize(analysis)
            write_chess_game(summary_text(analysis, summary), game_hash, extra=summary)
            log.info("chess_game_write OK hash=%s plies=%d", game_hash, len(analysis.plies))
        except Exception:
            log.exception("chess_game_write ERROR hash=%s", game_hash)

        enriched = self._build_enriched(analysis, message)
        result = self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # Pas de skip_intent (Q4) : la partie doit aller en mémoire épisodique.
            "metadata": metadata,
        })

        log.info("chess_router OK critical=%d images=%d", len(analysis.critical), len(images))
        return {"text": result["text"], "images": images}

    def _build_enriched(self, analysis, message: str) -> str:
        """Message enrichi des faits moteur, en français, suivi du message original."""
        color = analysis.nico_color
        nico_plies = [p for p in analysis.plies if p.color == color]
        counts = ", ".join(
            f"{label} {sum(1 for p in nico_plies if p.quality == key)}" for key, label in _QUALITY_FR
        )

        lines = [f"[Analyse Stockfish de la partie — Nico joue les {_COLOR_FR[color]} "
                 f"({_SOURCE_FR[analysis.color_source]}) :"]
        lines += _header_lines(analysis.headers)
        lines.append(f"Compteurs Nico : {counts}")
        for i, critical in enumerate(analysis.critical, 1):
            p = critical.ply
            tags = ", ".join(_TAG_FR.get(t, t) for t in p.tags) or "aucune"
            lines += [
                f"Position {i} ({_KIND_FR[critical.kind]}) — coup {p.move_number} :",
                f"  joué {_move_label(p.move_number, p.color, p.san)}, perte {p.loss:.0f} pts "
                f"de % de gain ({p.win_before:.0f} % → {p.win_after:.0f} %)",
                f"  meilleur {_move_label(p.move_number, p.color, p.best_san)}, "
                f"ligne : {_format_line(p.pv_san, p.move_number, p.color)}",
                f"  étiquettes : {tags}, phase : {_PHASE_FR[p.phase]}",
            ]
        block = "\n".join(lines) + "]"

        elo = analysis.headers.get("WhiteElo" if color == "white" else "BlackElo", "")
        player = f"joueur d'environ {elo} Elo" if elo and elo != "?" else "joueur amateur"
        consigne = (
            f"[Consigne : explique à Nico, {player}, les IDÉES de chaque position "
            "(plans, menaces, pourquoi le meilleur coup est meilleur), dans l'ordre "
            "Position 1, 2, 3 — Nico voit les diagrammes du même numéro. Utilise "
            "uniquement les coups et lignes fournis ci-dessus ; n'invente aucun coup "
            "ni évaluation. Notation française (C, F, T, D, R). Termine par 1 à 3 "
            "axes de travail.]"
        )
        parts = [block, consigne]
        if analysis.color_source == "default":
            parts.append(
                "[Consigne : signale que tu as supposé que Nico joue les blancs faute "
                "de pseudo, et qu'il peut préciser « je joue les noirs ».]"
            )
        return "\n".join(parts) + f"\n\n{message}"
