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
import re
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
    "e": "tournant (erreur adverse punie)",
}

# Critère d'avantage clair (chess_coach.analysis.clear_advantage) → libellé français.
_EVIDENCE_FR = {
    "material": "gain matériel", "crushing": "position écrasante", "mate": "attaque de mat",
    "development": "avance de développement", "activity": "avance d'activité",
}

_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

_OUTCOME_FR = {"win": "victoire", "loss": "défaite", "draw": "nulle", "unknown": "issue inconnue"}

# Lettre de pièce française devant une case (prise, désambiguïsation comprises) :
# « Dxe5+ », « Cbd7 », « Tae1 ». R (roi en français, tour en anglais) laissé tel quel.
_FR_PIECE_RE = re.compile(r"\b([CFTD])([a-h]?[1-8]?x?[a-h][1-8])\b")
_FR_TO_EN = {"C": "N", "F": "B", "T": "R", "D": "Q"}

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


def _material_line(fen: str, nico_color: str) -> str:
    """Bilan matériel du point de vue de Nico (valeurs 1/3/3/5/9)."""
    board = chess.Board(fen)
    nico = chess.WHITE if nico_color == "white" else chess.BLACK
    balance = sum(
        value * (len(board.pieces(piece, nico)) - len(board.pieces(piece, not nico)))
        for piece, value in _VALUES.items()
    )
    if balance == 0:
        return "matériel : égal"
    return f"matériel : Nico {'+' if balance > 0 else '−'}{abs(balance)}"


def _square_label(board: chess.Board, sq: int) -> str:
    """« Nf3 » pour une pièce, « pion e5 » pour un pion."""
    piece = board.piece_at(sq)
    if piece.piece_type == chess.PAWN:
        return f"pion {chess.square_name(sq)}"
    return f"{piece.symbol().upper()}{chess.square_name(sq)}"


def _attacked_line(fen: str) -> str:
    """Pièces attaquées par l'adversaire, par camp (hors roi ; pions seulement si non
    défendus), avec leurs attaquants : le LLM ne doit décrire aucune autre attaque."""
    board = chess.Board(fen)
    sides = []
    for color, label in ((chess.WHITE, "blancs"), (chess.BLACK, "noirs")):
        items = []
        for sq in chess.SquareSet(board.occupied_co[color]):
            if board.piece_type_at(sq) == chess.KING:
                continue
            attackers = board.attackers(not color, sq)
            if not attackers:
                continue
            defended = bool(board.attackers(color, sq))
            if board.piece_type_at(sq) == chess.PAWN and defended:
                continue
            by = ", ".join(_square_label(board, a) for a in attackers)
            items.append(f"{_square_label(board, sq)}{'' if defended else ' non défendu'} (par {by})")
        if items:
            sides.append(f"{label} " + ", ".join(items))
    return "attaquées : " + (" ; ".join(sides) or "aucune")


def _to_english(text: str) -> str:
    """Notation française résiduelle du LLM → anglaise (C→N, F→B, T→R, D→Q)."""
    return _FR_PIECE_RE.sub(lambda m: _FR_TO_EN[m.group(1)] + m.group(2), text)


def _level_line(summary: dict) -> str:
    """Données de niveau de la partie (précision par phase, erreurs adverses punies, résultat)."""
    accuracies = ", ".join(
        f"{_PHASE_FR[phase]} {summary[f'accuracy_{phase}']:.0f} %"
        for phase in ("opening", "middlegame", "endgame") if summary[f"accuracy_{phase}"] is not None
    )
    parts = []
    if accuracies:
        parts.append(f"précision Nico : {accuracies}")
    parts.append(f"erreurs adverses punies : {summary['opponent_errors_punished']}"
                 f"/{summary['opponent_errors']}")
    parts.append(f"résultat : {summary['result'] or '?'} ({_OUTCOME_FR[summary['outcome']]})")
    return "Niveau (données) : " + " ; ".join(parts)


def _reply_start(p) -> tuple:
    """(numéro, couleur) du premier coup adverse après le coup de Nico en p."""
    if p.color == "white":
        return p.move_number, "black"
    return p.move_number + 1, "white"


def _explosive_lines(p, e, nico_color: str) -> list:
    """Faits moteur du coup explosif d'une position de sorte d : l'idée, la variante
    si l'adversaire joue la réponse logique, la difficulté de la bonne réponse."""
    lines = [f"  explosif {_move_label(p.move_number, p.color, e.san)}!?"]
    facts = []
    # Matériel : pièce offerte (posée en prise) prioritaire sur le sacrifice de ligne.
    if e.offered:
        facts.append(f"offre {_PIECE_FR.get(e.san[0], 'le pion')} ({e.offered})")
    elif e.sacrifice:
        facts.append(f"sacrifie {e.sacrifice} pion(s) sur la ligne")
    if e.forcing:
        facts.append("forçant : " + "/".join(_FORCING_FR[f] for f in e.forcing))
    if facts:
        lines.append("  " + " ; ".join(facts))
    # Réponse logique : prise naturelle du matériel offert, à défaut la 1re réponse moteur.
    if e.trap_reply_san:
        piece = _PIECE_FR.get(e.san[0], "le pion")
        offered = "offerte" if piece.startswith("la ") else "offert"
        lines.append(f"  réponse logique : {e.trap_reply_san} (prend {piece} {offered})")
    elif e.replies:
        lines.append(f"  réponse logique : {e.replies[0]['san']}")
    number, color = _reply_start(p)
    lines.append(f"  variante : {_format_line(e.trap_line_san, number, color)} "
                 f"({_EVIDENCE_FR[e.evidence]})")
    lines.append(f"  fin de variante : {_material_line(e.trap_end_fen, nico_color)}, "
                 f"% de gain Nico {e.trap_end_win:.0f} %")
    lines.append(f"  fin de variante, {_attacked_line(e.trap_end_fen)}")
    # Difficulté : réponses qui tiennent = écart ≤ 5 pts avec la meilleure réponse.
    difficulty = []
    if e.trap_reply_san:
        trap = f", elle lui fait perdre {e.trap:.0f} pts" if round(e.trap) else ""
        difficulty.append(f"la réponse logique gagne du matériel à vue{trap}")
    if e.replies:
        best = min(r["win"] for r in e.replies)
        holding = [r["san"] for r in e.replies if r["win"] - best <= 5]
        others = [r["win"] for r in e.replies if r["win"] - best > 5]
        label = "seule réponse qui tient" if len(holding) == 1 else "réponses qui tiennent"
        text = f"{label} : {', '.join(holding)}"
        if others:
            rest = "l'autre" if len(others) == 1 else f"les {len(others)} autres"
            text += f" ({rest} : Nico ≥ {min(others):.0f} %)"
        difficulty.append(text)
    if difficulty:
        lines.append("  difficulté pour l'adversaire : " + " ; ".join(difficulty))
    for reply in e.replies:
        lines.append(f"  si {reply['san']} : {_format_line(reply['line_san'], number, color)}, "
                     f"{reply['win']:.0f} % pour Nico")
    return lines


def _caption(index: int, critical, plies: list) -> str:
    p = critical.ply
    if critical.kind == "e":
        prev = plies[p.ply - 1]
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"tournant après {_move_label(prev.move_number, prev.color, prev.san)}?, "
                f"joué {_move_label(p.move_number, p.color, p.san)} "
                f"(meilleur {_move_label(p.move_number, p.color, p.best_san)})")
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
            images.append({"path": str(out_path), "caption": _caption(i, critical, analysis.plies)})

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

        enriched = self._build_enriched(analysis, message, _anchor(summary), summary)
        result = self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # Pas de skip_intent (Q4) : la partie doit aller en mémoire épisodique,
            # sous un intent imposé (le namer répondait « aucun », audit 05).
            "metadata": {**metadata, "forced_intent_name": FORCED_INTENT_NAME},
        })

        log.info("chess_router OK critical=%d images=%d", len(analysis.critical), len(images))
        return {"text": _to_english(result["text"]), "images": images}

    def _build_enriched(self, analysis, message: str, anchor: str, summary: dict) -> str:
        """Ancre de la partie, puis faits moteur en français, puis message original."""
        color = analysis.nico_color
        opening = summary["opening"]
        nico_plies = [p for p in analysis.plies if p.color == color]
        counts = ", ".join(
            f"{label} {sum(1 for p in nico_plies if p.quality == key)}" for key, label in _QUALITY_FR
        )

        lines = [anchor, f"[Analyse Stockfish de la partie — Nico joue les {_COLOR_FR[color]} "
                 f"({_SOURCE_FR[analysis.color_source]}) :"]
        lines += _header_lines(analysis.headers)
        lines.append(f"Compteurs Nico : {counts}")
        lines.append(_level_line(summary))
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
                f"  {_material_line(p.fen_before, color)}",
                f"  {_attacked_line(p.fen_before)}",
            ]
            if critical.kind == "e":
                prev = analysis.plies[p.ply - 1]
                lines.append(f"  erreur adverse {_move_label(prev.move_number, prev.color, prev.san)} : "
                             f"perte {prev.loss:.0f} pts "
                             f"(meilleur {_move_label(prev.move_number, prev.color, prev.best_san)})")
            if critical.kind in ("c", "e"):
                lines.append(f"  variante : {_format_line(critical.line_san, p.move_number, p.color)} "
                             f"({_EVIDENCE_FR[critical.evidence]})")
            if critical.kind == "d":
                lines += _explosive_lines(p, critical.explosive, color)
        block = "\n".join(lines) + "]"

        elo = analysis.headers.get("WhiteElo" if color == "white" else "BlackElo", "")
        player = f"joueur d'environ {elo} Elo" if elo and elo != "?" else "joueur amateur"
        consigne = (
            f"[Consigne : réponse COURTE à Nico, {player}. Format imposé : 1re ligne "
            f"exacte « {anchor} » ; puis une entrée par position, dans l'ordre Position 1, "
            "2, 3 (Nico voit les diagrammes du même numéro), de 1 à 3 phrases : le coup, "
            "l'idée, le chiffre clé ; puis une ligne « Niveau : » de 2 phrases (mal joué, "
            "passif, solide ou brillant), justifiée par la ligne « Niveau (données) ». Rien "
            "d'autre : pas de section « ce qui se passe » ni « pourquoi ». Utilise "
            "uniquement les coups et lignes fournis ci-dessus ; n'invente aucun coup "
            "ni évaluation, ni emplacement de pièce : fie-toi à la liste des pièces. "
            "Ne décris aucune attaque, défense, menace ou colonne absente des lignes "
            "matériel / attaquées. Notation anglaise : N, B, R, Q, K.]"
        )
        parts = [block, consigne]
        if opening:
            parts.append(
                f"[Consigne : ouverture jouée : {opening.replace('-', ' ')}. Quand c'est "
                "pertinent, relie la position aux idées classiques de cette ouverture en une "
                "demi-phrase. Un gambit d'ouverture choisi par Nico est un choix assumé, "
                "pas une faute à corriger.]"
            )
        if any(c.kind == "e" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque tournant, nomme l'erreur adverse et montre la "
                "variante qui la punit (coups fournis).]"
            )
        if any(c.kind == "d" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque occasion explosive : l'idée en une phrase ; la "
                "variante si l'adversaire joue la réponse logique (coups fournis, rien "
                "au-delà) et l'avantage atteint (critère fourni), expliqué par les pièces "
                "protégées / vulnérables de la fin de variante ; pourquoi la bonne réponse "
                "est difficile à trouver pour l'adversaire, d'après la ligne difficulté. Ne "
                "donne ni le coût, ni quand le tenter, et ne le présente jamais comme le "
                "meilleur coup. Cette entrée peut dépasser 3 phrases.]"
            )
        if analysis.color_source == "default":
            parts.append(
                "[Consigne : signale que tu as supposé que Nico joue les blancs faute "
                "de pseudo, et qu'il peut préciser « je joue les noirs ».]"
            )
        return "\n".join(parts) + f"\n\n{message}"
