# aria/execution/routers/chess_router.py
#
# Router d'exécution du coach d'échecs (sprint 26, tronçon 02).
#
# Pipeline CHESS_ANALYSIS :
#   PGN collé → chess_coach.analysis.analyze (Stockfish)
#   → un diagramme PNG par position critique (≤ 3, flèche = meilleur coup)
#   → message enrichi des faits moteur (notation anglaise, sprint 27)
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

import chess

from chess_coach.analysis import analyze
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
    "d": "occasion explosive",
    "e": "tournant",
}

# Nom français de la pièce offerte (libellé du bloc d'occasion explosive).
_PIECE_FR = {"N": "le cavalier", "B": "le fou", "R": "la tour", "Q": "la dame", "K": "le roi"}

_FORCING_FR = {"check": "échec", "capture": "prise", "threat": "menace"}

_PHASE_FR = {"opening": "ouverture", "middlegame": "milieu de partie", "endgame": "finale"}

_TAG_FR = {
    "capture": "prise", "check": "échec", "pawn": "coup de pion", "king": "coup de roi",
    "castle": "roque", "retreat": "recul", "hanging": "pièce en prise",
}

# Intent imposé aux échanges d'analyse de partie (bug 1, audit correctif 05) :
# le namer répondait « aucun » → échange non écrit en épisodique.
FORCED_INTENT_NAME = "jeux echecs"

# Clés de compteurs (qualité PlyAnalysis) → libellé français, dans l'ordre affiché.
_QUALITY_FR = [
    ("best", "meilleurs"), ("correct", "corrects"), ("inaccuracy", "imprécisions"),
    ("mistake", "erreurs"), ("blunder", "gaffes"),
]


def _move_label(move_number: int, color: str, san: str) -> str:
    """« 17.Cg4+ » pour les blancs, « 17...Cg4+ » pour les noirs."""
    dots = "." if color == "white" else "..."
    return f"{move_number}{dots}{san}"


def _format_line(pv_san: list, move_number: int, color: str) -> str:
    """Ligne principale numérotée en notation anglaise (ex. « 17...Bd7 18.Nf3 Nc6 »)."""
    parts = []
    for i, san in enumerate(pv_san):
        if color == "white":
            parts.append(f"{move_number}.{san}")
            color = "black"
        else:
            parts.append(f"{move_number}...{san}" if i == 0 else san)
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


def _anchor(summary: dict) -> str:
    """« Partie contre <adversaire> <date> <ouverture> » : identifiant lisible
    de la partie, pour qu'une question de suivi retrouve la bonne (Q11 b)."""
    parts = ["Partie contre", summary["opponent"] or "adversaire inconnu"]
    if summary["date"]:
        parts.append(summary["date"])
    if summary["opening"]:
        parts.append(summary["opening"].replace("-", " "))
    return " ".join(parts)


def _pieces_line(fen: str) -> str:
    """Pièces par camp tirées du FEN (ex. « pièces : blancs Kg1 Nf3, pions e4 ; noirs … ») :
    le LLM ne voit pas l'échiquier, cette liste l'empêche de placer une pièce inexistante."""
    board = chess.Board(fen)
    sides = []
    for color, label in ((chess.WHITE, "blancs"), (chess.BLACK, "noirs")):
        pieces = [
            f"{chess.piece_symbol(piece).upper()}{chess.square_name(sq)}"
            for piece in (chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
            for sq in board.pieces(piece, color)
        ]
        pawns = [chess.square_name(sq) for sq in board.pieces(chess.PAWN, color)]
        sides.append(f"{label} {' '.join(pieces)}, pions {' '.join(pawns) or 'aucun'}")
    return "  pièces : " + " ; ".join(sides)


def _reply_start(p) -> tuple:
    """(numéro, couleur) du premier coup adverse après le coup de Nico en p."""
    if p.color == "white":
        return p.move_number, "black"
    return p.move_number + 1, "white"


def _explosive_lines(p, e) -> list:
    """Faits moteur du coup explosif d'une position de sorte d (éléments nuls omis)."""
    lines = [
        f"  explosif {_move_label(p.move_number, p.color, e.san)}!? : coût {e.loss:.0f} pts "
        f"de % de gain ({e.win_after + e.loss:.0f} % → {e.win_after:.0f} %), "
        f"ligne : {_format_line(e.pv_san, p.move_number, p.color)}"
    ]
    facts = []
    # Matériel : pièce offerte (posée en prise) prioritaire sur le sacrifice de ligne.
    if e.offered:
        facts.append(f"offre {_PIECE_FR.get(e.san[0], 'le pion')} ({e.offered})")
    elif e.sacrifice:
        facts.append(f"sacrifie {e.sacrifice} pion(s) sur la ligne")
    if e.forcing:
        facts.append("forçant : " + "/".join(_FORCING_FR[f] for f in e.forcing))
    if round(e.volatility):
        facts.append(f"volatilité {e.volatility:.0f} pts")
    if facts:
        lines.append("  " + " ; ".join(facts))
    number, color = _reply_start(p)
    if e.trap_reply_san and round(e.trap):
        lines.append(f"  si l'adversaire prend {e.trap_reply_san} : "
                     f"{_format_line(e.trap_line_san, number, color)} (il perd {e.trap:.0f} pts)")
    for reply in e.replies:
        lines.append(f"  si {reply['san']} : {_format_line(reply['line_san'], number, color)}, "
                     f"{reply['win']:.0f} % pour Nico")
    return lines


def _caption(index: int, critical) -> str:
    p = critical.ply
    if critical.kind == "c":
        return (f"Position {index} — coup {p.move_number} : "
                f"{_move_label(p.move_number, p.color, p.san)}, seul bon coup — bien joué")
    if critical.kind == "d":
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"joué {_move_label(p.move_number, p.color, p.san)}, "
                f"explosif {_move_label(p.move_number, p.color, critical.explosive.san)}!? "
                f"(meilleur {_move_label(p.move_number, p.color, p.best_san)})")
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
            # Sorte d : 2e flèche (orange) pour le coup explosif.
            alt_uci = critical.explosive.uci if critical.kind == "d" else None
            render_position(critical.ply.fen_before, analysis.nico_color,
                            critical.ply.best_uci, str(out_path), alt_uci=alt_uci)
            images.append({"path": str(out_path), "caption": _caption(i, critical)})

        # ── Fiche de partie (non bloquante) ──────────────────────────────────
        # Hash des coups seuls (pas des en-têtes) : le même PGN recopié sans
        # en-têtes reste la même partie → même doc_id → la fiche est remplacée.
        game_hash = hashlib.sha256(
            "".join(p.uci for p in analysis.plies).encode()
        ).hexdigest()[:16]
        summary = summarize(analysis)
        try:
            write_chess_game(summary_text(analysis, summary), game_hash, extra=summary)
            log.info("chess_game_write OK hash=%s plies=%d", game_hash, len(analysis.plies))
        except Exception:
            log.exception("chess_game_write ERROR hash=%s", game_hash)

        enriched = self._build_enriched(analysis, message, _anchor(summary), summary["opening"])
        result = self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # Pas de skip_intent (Q4) : la partie doit aller en mémoire épisodique,
            # sous un intent imposé (le namer répondait « aucun », audit 05).
            "metadata": {**metadata, "forced_intent_name": FORCED_INTENT_NAME},
        })

        log.info("chess_router OK critical=%d images=%d", len(analysis.critical), len(images))
        return {"text": result["text"], "images": images}

    def _build_enriched(self, analysis, message: str, anchor: str, opening: str) -> str:
        """Ancre de la partie, puis faits moteur en français, puis message original."""
        color = analysis.nico_color
        nico_plies = [p for p in analysis.plies if p.color == color]
        counts = ", ".join(
            f"{label} {sum(1 for p in nico_plies if p.quality == key)}" for key, label in _QUALITY_FR
        )

        lines = [anchor, f"[Analyse Stockfish de la partie — Nico joue les {_COLOR_FR[color]} "
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
                _pieces_line(p.fen_before),
            ]
            if critical.kind == "d":
                lines += _explosive_lines(p, critical.explosive)
        block = "\n".join(lines) + "]"

        elo = analysis.headers.get("WhiteElo" if color == "white" else "BlackElo", "")
        player = f"joueur d'environ {elo} Elo" if elo and elo != "?" else "joueur amateur"
        consigne = (
            f"[Consigne : explique à Nico, {player}, les IDÉES de chaque position "
            "(plans, menaces, pourquoi le meilleur coup est meilleur), dans l'ordre "
            "Position 1, 2, 3 — Nico voit les diagrammes du même numéro. Utilise "
            "uniquement les coups et lignes fournis ci-dessus ; n'invente aucun coup "
            "ni évaluation, ni emplacement de pièce : fie-toi à la liste des pièces. "
            "Notation anglaise : N, B, R, Q, K. Termine par 1 à 3 "
            "axes de travail. Commence ta réponse par la ligne exacte "
            f"« {anchor} ».]"
        )
        parts = [block, consigne]
        if opening:
            parts.append(
                f"[Consigne : ouverture jouée : {opening.replace('-', ' ')}. Relie chaque "
                "position aux idées classiques de cette ouverture (plans typiques, "
                "structures, pourquoi le coup s'inscrit ou non dans ces idées). Un gambit "
                "d'ouverture choisi par Nico est un choix assumé (tempo, développement, "
                "sortir l'adversaire de sa théorie), pas une faute à corriger.]"
            )
        if any(c.kind == "d" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque position « occasion explosive », explique "
                "l'idée du coup explosif (initiative, attaque, piège), son coût objectif "
                "en % de gain, et dans quel contexte pratique le tenter (pari pratique) ; "
                "ne le présente jamais comme le meilleur coup.]"
            )
        if analysis.color_source == "default":
            parts.append(
                "[Consigne : signale que tu as supposé que Nico joue les blancs faute "
                "de pseudo, et qu'il peut préciser « je joue les noirs ».]"
            )
        return "\n".join(parts) + f"\n\n{message}"
