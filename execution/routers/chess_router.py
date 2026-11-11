# aria/execution/routers/chess_router.py
#
# Router d'exécution du coach d'échecs (sprint 26, tronçon 02).
#
# Pipeline CHESS_ANALYSIS :
#   PGN collé → chess_coach.analysis.analyze (Stockfish)
#   → un diagramme PNG par position critique (≤ 4, flèche verte = meilleur coup, bleue = coup joué)
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
#   Les fiches de partie sont relues via le bridge (règle 2) pour le bloc
#   « Progression » (sprint 28, tronçon 03), écrit par le router sous le texte LLM.

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

import chess

from chess_coach.analysis import analyze, new_targets, parse_pgn, split_pgn
from chess_coach.clock import long_thinks, lost_on_time, move_times, time_line, verdict
from chess_coach.conversion import conversion_line, repeated_ideas, winning_period
from chess_coach.explosive import _GAIN_MIN, is_brilliant
from chess_coach.level import accuracy_rank
from chess_coach.live import trapping_replies
from chess_coach.openings import opening_room
from chess_coach.player_model import LABELS, MATE_LABELS, build_profile, game_opening_group
from chess_coach.render import (ALT_ARROW, CURVE_BEST, CURVE_CORRECT, CURVE_NEUTRAL, PLAYED_ARROW, TRAP_ARROW, error_arrow,
                                render_curve, render_position)
from chess_coach.structure import structure_line
from chess_coach.summary import nico_wins, story_line, story_plies, summarize, summary_text
from config import config
from cognition.cognitive_context import CognitiveOperation
from execution.routers.execution_base import BaseRouter
from logger import get_logger
from memory.writer import delete_chess_games, write_chess_game

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

# Perte à partir de laquelle un point de la courbe prend la couleur d'une erreur.
_ERROR_POINT_MIN = 10

# Alerte précision adverse suspecte (sprint 56, décision de Nico du 2026-11-11) : un seul
# seuil de précision ; le nombre de coups affiché dit le poids de cette précision.
_SUSPECT_MIN_MOVES = 20
_SUSPECT_MIN_ACCURACY = 95

# Sorte d piégeante : remplace « occasion explosive » dans les faits donnés au LLM.
_TRAP_KIND_FR = "piège affiché"

# Critère d'avantage clair (chess_coach.analysis.clear_advantage) → libellé français.
_EVIDENCE_FR = {
    "material": "gain matériel", "crushing": "position écrasante", "mate": "attaque de mat",
    "development": "avance de développement", "activity": "avance d'activité",
}

_OUTCOME_FR = {"win": "victoire", "loss": "défaite", "draw": "nulle", "unknown": "issue inconnue"}

# Lettre de pièce française devant une case (prise, désambiguïsation comprises) :
# « Dxe5+ », « Cbd7 », « Tae1 ». R (roi en français, tour en anglais) laissé tel quel.
_FR_PIECE_RE = re.compile(r"\b([CFTD])([a-h]?[1-8]?x?[a-h][1-8])\b")
_FR_TO_EN = {"C": "N", "F": "B", "T": "R", "D": "Q"}

# Nom français de la pièce offerte (libellé du bloc d'occasion explosive).
_PIECE_FR = {"N": "le cavalier", "B": "le fou", "R": "la tour", "Q": "la dame", "K": "le roi"}

_FORCING_FR = {"check": "échec", "capture": "prise", "threat": "menace"}

_PHASE_FR = {"opening": "ouverture", "middlegame": "milieu de partie", "endgame": "finale"}
# Classements de la ligne fixe de la progression, hors lignes fusionnées.
_PHASE_THEMES = ("opening", "middlegame", "endgame")

_TAG_FR = {
    "capture": "prise", "check": "échec", "pawn": "coup de pion", "king": "coup de roi",
    "castle": "roque", "retreat": "recul", "hanging": "pièce en prise",
}

# Intent imposé aux échanges d'analyse de partie (bug 1, audit correctif 05) :
# le namer répondait « aucun » → échange non écrit en épisodique.
FORCED_INTENT_NAME = "jeux echecs"

# Clés de compteurs (qualité PlyAnalysis) → libellé français, dans l'ordre affiché.
# Raison affichée d'un badge débloqué (conditions : chess_coach.player_model).
_BADGE_REASON = {
    "Main propre": "aucune gaffe sur une partie d'au moins 40 demi-coups",
    "Justicier": "toutes les erreurs adverses punies (au moins 2)",
    "Coup de maître": "coup trouvé 400 Elo au-dessus du classement global",
    "Phénix": "nulle ou victoire après être tombé à 20 % de gain ou moins",
    "Bourreau": "3 victoires écrasantes de suite",
    "Série": "3 victoires de suite",
    "Répertoire": "5e partie dans la même famille d'ouverture",
}

_RESULT_FR = {1.0: "victoire", 0.5: "nulle", 0.0: "défaite"}

_QUALITY_FR = [
    ("best", "meilleurs"), ("correct", "corrects"), ("inaccuracy", "imprécisions"),
    ("mistake", "erreurs"), ("blunder", "gaffes"),
]

# Pastille d'un coup dans les légendes (sprint 50) : Telegram n'affiche que du texte brut.
# Sprint 51 : même couleur que la flèche des miniatures — meilleur coup du moteur vert
# (_MARK_BEST), coup joué meilleur bleu, coup joué correct blanc.
_MARK_BEST, _MARK_EXPLOSIVE, _MARK_TRAP = "🟢", "🟠", "🩵"
_QUALITY_MARK = {"best": "🔵", "correct": "⚪", "inaccuracy": "🩷", "mistake": "🔴", "blunder": "⚫"}
# Clé des pastilles de qualité, dans l'ordre de la légende : (qualité, libellé).
_MARKS_KEY = (("best", "meilleur"), ("correct", "correct"), ("inaccuracy", "imprécision"),
              ("mistake", "erreur"), ("blunder", "gaffe"))
# Erreurs par gravité dans le bilan : (qualité, singulier, pluriel).
_ERRORS_FR = (("inaccuracy", "imprécision", "imprécisions"), ("mistake", "erreur", "erreurs"),
              ("blunder", "gaffe", "gaffes"))


def _played_mark(p) -> str:
    """Pastille du coup joué : orange s'il est brillant, sinon celle de sa qualité."""
    if is_brilliant(p.fen_before, p.uci, p.win_before, p.loss):
        return _MARK_EXPLOSIVE
    return _QUALITY_MARK[p.quality]


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
        parts.append(summary["opening"])
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
    """Matériel en toutes lettres : un solde en points se lit à tort comme des pions (sprint 50)."""
    board = chess.Board(fen)
    nico = chess.WHITE if nico_color == "white" else chess.BLACK
    mine, theirs = [], []
    for piece in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
        gap = len(board.pieces(piece, nico)) - len(board.pieces(piece, not nico))
        (mine if gap > 0 else theirs).extend([chess.piece_symbol(piece).upper()] * abs(gap))
    parts = []
    if mine and theirs:
        parts.append(f"{', '.join(mine)} contre {', '.join(theirs)}")
    elif mine or theirs:
        parts.append(f"{', '.join(mine or theirs)} de {'plus' if mine else 'moins'}")
    my_pawns, their_pawns = len(board.pieces(chess.PAWN, nico)), len(board.pieces(chess.PAWN, not nico))
    if my_pawns != their_pawns:
        parts.append(f"{my_pawns} pion{'s' if my_pawns > 1 else ''} contre {their_pawns}")
    return f"matériel : Nico {', '.join(parts)}" if parts else "matériel : égal"


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


def _move_fact_items(fen: str, moves_san: list, move_number: int, color: str) -> list:
    """Ligne rejouée depuis `fen` : liste de (libellé du coup, faits observables) —
    prise, échec, mat, roque, promotion, pièces adverses nouvellement attaquées par la
    pièce jouée (non défendues ou de valeur supérieure), et pièces de son camp qu'il
    décloue (clouage sur le roi seulement). Calcul unique partagé
    par la ligne « faits : » du message enrichi et la ligne « Variante : » des légendes."""
    board = chess.Board(fen)
    parts = []
    recapture_square = None
    for san in moves_san:
        move = board.parse_san(san)
        mover = board.turn
        castling = board.is_castling(move)
        facts = []
        if castling:
            facts.append("roque")
        elif board.is_capture(move):
            # Reprise : prise sur la case où l'adversaire vient de prendre.
            if move.to_square == recapture_square:
                facts.append("reprend")
            else:
                captured = move.to_square
                if board.is_en_passant(move):
                    captured += -8 if mover == chess.WHITE else 8
                facts.append(f"prend {_square_label(board, captured)}")
        recapture_square = move.to_square if board.is_capture(move) else None
        if move.promotion:
            facts.append(f"promotion en {chess.piece_symbol(move.promotion).upper()}")
        attacked = new_targets(board, move)
        # La pièce jouée elle-même n'est pas « déclouée » : seules celles restées en place.
        pinned = [sq for sq in chess.SquareSet(board.occupied_co[mover])
                  if sq != move.from_square and board.is_pinned(mover, sq)]
        board.push(move)
        if board.is_checkmate():
            facts.append("mat")
        elif board.is_check():
            facts.append("échec")
        if attacked and not board.is_checkmate():
            facts.append("attaque " + ", ".join(_square_label(board, sq) for sq in attacked))
        unpinned = [sq for sq in pinned if not board.is_pinned(mover, sq)]
        if unpinned:
            facts.append("décloue " + ", ".join(_square_label(board, sq) for sq in unpinned))
        parts.append((_move_label(move_number, color, san), facts))
        if color == "black":
            move_number += 1
        color = "black" if color == "white" else "white"
    return parts


def _move_facts(fen: str, moves_san: list, move_number: int, color: str) -> str:
    """Ligne « faits : » du message enrichi : chaque coup suivi de ses faits entre
    parenthèses. Le LLM s'appuie sur ces faits au lieu de les deviner."""
    return " ".join(
        f"{label} ({', '.join(facts)})" if facts else label
        for label, facts in _move_fact_items(fen, moves_san, move_number, color)
    )


def _played_facts(analysis, p) -> str:
    """Faits du coup joué suivi de la réponse adverse jouée dans la partie (seul s'il
    termine la partie) : c'est la réponse qui dit si la pièce prise est reprise (sprint 53)."""
    moves = [p.san]
    if p.ply + 1 < len(analysis.plies):
        moves.append(analysis.plies[p.ply + 1].san)
    return _move_facts(p.fen_before, moves, p.move_number, p.color)


_PIN_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def _relative_pins(board: chess.Board, color: chess.Color) -> set:
    """Clouages relatifs du camp `color` : (pièce clouée, pièce derrière, cloueur), libellés.
    Une pièce à longue portée adverse attaque la pièce, et derrière elle, sur la même ligne,
    une dame ou une tour de plus grande valeur (le clouage sur le roi relève de is_pinned)."""
    pins = set()
    for slider in chess.SquareSet(board.occupied_co[not color]):
        if board.piece_type_at(slider) not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        for sq in board.attacks(slider) & board.occupied_co[color]:
            for behind in board.pieces(chess.QUEEN, color) | board.pieces(chess.ROOK, color):
                between = chess.SquareSet(chess.between(slider, behind))
                if (sq in between and between & board.occupied == chess.SquareSet(chess.BB_SQUARES[sq])
                        and board.piece_type_at(sq) != chess.KING
                        and _PIN_VALUES[board.piece_type_at(behind)] > _PIN_VALUES[board.piece_type_at(sq)]):
                    pins.add(f"{_square_label(board, sq)} cloué sur {_square_label(board, behind)} "
                             f"(par {_square_label(board, slider)})")
    return pins


_START_SQUARES = {chess.WHITE: (chess.B1, chess.G1, chess.C1, chess.F1),
                  chess.BLACK: (chess.B8, chess.G8, chess.C8, chess.F8)}
_CENTER = (chess.D4, chess.E4, chess.D5, chess.E5)


def _intent_line(plies: list, p, seconds: float | None = None, human_line: list = ()) -> str | None:
    """Ligne « idée du coup joué » d'une erreur de Nico (sprint 54) : coup adverse précédent
    et ses faits, ce que le coup joué cherchait (met à l'abri, défend, décloue, développe,
    attaque, contrôle, vise le roi, active, libère), clouages relatifs qu'il crée, trace Maia
    après le coup 10 (fréquence du coup à son niveau, suite humaine probable `human_line`,
    coup joué en tête), temps passé. Indices de l'idée probable de Nico et de ce qu'elle a
    négligé ; None si aucun segment n'a de contenu."""
    segments = []
    if p.ply >= 1:
        prev = plies[p.ply - 1]
        segments.append(_move_facts(prev.fen_before, [prev.san], prev.move_number, prev.color))
    board = chess.Board(p.fen_before)
    move = board.parse_san(p.san)
    mover = board.turn
    after = board.copy(stack=False)
    after.push(move)
    intent = []
    if board.attackers(not mover, move.from_square) and not after.attackers(not mover, move.to_square):
        intent.append(f"met à l'abri {_square_label(board, move.from_square)}")
    for sq in chess.SquareSet(board.occupied_co[mover]):
        if (sq != move.from_square and board.piece_type_at(sq) != chess.KING
                and board.attackers(not mover, sq) and not board.attackers(mover, sq)
                and after.piece_at(sq) == board.piece_at(sq) and after.attackers(mover, sq)):
            intent.append(f"défend {_square_label(board, sq)}")
    # « roque », « décloue » et « attaque » : faits déjà calculés par _move_fact_items, repris tels quels.
    facts = _move_fact_items(p.fen_before, [p.san], p.move_number, p.color)[0][1]
    intent += [f for f in facts if f == "roque" or f.startswith("décloue")]
    # Intentions élargies (tronçon 01b), sur la pièce jouée X (libellée à sa case d'arrivée).
    piece = _square_label(after, move.to_square)
    if (board.piece_type_at(move.from_square) in (chess.KNIGHT, chess.BISHOP)
            and move.from_square in _START_SQUARES[mover]):
        intent.append(f"développe {piece}")
    intent += [f for f in facts if f.startswith("attaque")]
    seen_before, seen_after = board.attacks(move.from_square), after.attacks(move.to_square)
    center = [chess.square_name(sq) for sq in _CENTER if sq in seen_after and sq not in seen_before]
    if center:
        intent.append("contrôle " + ", ".join(center))
    king_zone = chess.SquareSet(chess.BB_KING_ATTACKS[after.king(not mover)])
    if (seen_after & king_zone) - (seen_before & king_zone):
        intent.append("vise le roi")
    # Mobilité : cases attaquées hors cases occupées par son propre camp.
    n = len(seen_before - chess.SquareSet(board.occupied_co[mover]))
    m = len(seen_after - chess.SquareSet(after.occupied_co[mover]))
    if m - n >= 3:
        intent.append(f"active {piece} ({n} → {m} cases)")
    freed = [_square_label(board, sq) for sq in chess.SquareSet(board.occupied_co[mover])
             if sq != move.from_square and board.piece_type_at(sq) in (chess.BISHOP, chess.ROOK, chess.QUEEN)
             and after.piece_at(sq) == board.piece_at(sq) and len(after.attacks(sq)) > len(board.attacks(sq))]
    if freed:
        intent.append("libère " + ", ".join(freed))
    if intent:
        segments.append("ton coup : " + ", ".join(intent))
    pins = sorted(_relative_pins(after, mover) - _relative_pins(board, mover))
    if pins:
        segments.append("après ton coup : " + ", ".join(pins))
    # Trace Maia : rien en ouverture (Maia non fiable jusqu'au coup 10) ni sans Maia.
    if p.move_number > 10 and p.played_p is not None:
        maia = f"Maia : coup choisi par {p.played_p * 100:.0f} % des joueurs de ton niveau"
        if len(human_line) > 1:
            items = _move_fact_items(p.fen_before, human_line, p.move_number, p.color)[1:]
            maia += " ; suite probable : " + " ".join(
                f"{label} ({', '.join(f)})" if f else label for label, f in items)
        segments.append(maia)
    if seconds is not None:
        segments.append(f"temps : {seconds:.0f} s")
    return "  idée du coup joué, faits : " + " ; ".join(segments) if segments else None


def _told_moves(label: str, p, moves: list, mark: str = "") -> str:
    """« label : » puis les coups séparés par « ; », chacun suivi de ses faits ; mark,
    pastille éventuelle du premier coup."""
    items = _move_fact_items(p.fen_before, moves, p.move_number, p.color)
    return f"{label} : {mark + ' ' if mark else ''}" + " ; ".join(
        f"{move} {', '.join(facts)}" if facts else move for move, facts in items
    ) + "."


def _trap_replies(critical) -> list:
    """Réponses piégeantes d'une position de sorte d, sinon []. La règle est celle de
    l'échiquier, le coup analysé donnant le % de gain du meilleur coup."""
    if critical.kind != "d":
        return []
    return trapping_replies(critical.explosive.replies, critical.ply.win_before)


def _trap_line(p, explosive, reply: dict) -> str:
    """Ligne « Piège : » d'une légende, écrite par le code à partir de la réponse piégeante
    la plus probable. « Sinon, pas de mat. » : seule cette réponse connue mène au mat."""
    number, color = _reply_start(p)
    head = (f"Piège : {_move_label(p.move_number, p.color, explosive.san)}!? "
            f"Si {_move_label(number, color, reply['san'])} ({reply['p'] * 100:.0f} %)")
    # Après la réponse adverse, le trait revient à Nico, au coup suivant.
    if len(reply["line_san"]) > 1:
        head += ", " + _format_line(reply["line_san"][1:], p.move_number + 1, p.color)
    if reply["line_san"][-1].endswith("#"):
        others = [r for r in explosive.replies if r is not reply]
        no_other_mate = not any("#" in san for r in others for san in r["line_san"])
        return f"{head}." + (" Sinon, pas de mat." if no_other_mate else "")
    return f"{head}, {reply['win']:.0f} % pour toi."


def _line_end(p, moves: list, win: float) -> str:
    """Fin d'une suite comparée : mat, ou matériel et % de gain de la ligne du moteur."""
    board = chess.Board(p.fen_before)
    for san in moves:
        board.push_san(san)
    if board.is_checkmate():
        return "  → mat"
    return f"  → {_material_line(board.fen(), p.color)}, {win:.0f} % de gain"


def _compared_lines(critical) -> str:
    """Suites du meilleur coup et du coup joué, avec leur fin : le code dit où chacune mène."""
    p = critical.ply
    return "\n".join((
        _told_moves("Meilleur coup", p, critical.best_line_san, _MARK_BEST),
        _line_end(p, critical.best_line_san, p.win_before),
        _told_moves("Ton coup", p, critical.played_line_san, _played_mark(p)),
        _line_end(p, critical.played_line_san, p.win_after),
    ))


def _variant_line(critical) -> str:
    """Ligne « Variante : » d'une légende, racontée par le code (tronçon 15). Vide si
    la ligne n'a aucun coup. Sorte d : variante du coup explosif, puis la ligne « Piège : »
    s'il est piégeant, puis une ligne pour la variante du meilleur coup (les autres
    sortes la donnent déjà). Sortes a et b : les deux suites comparées."""
    p = critical.ply
    if critical.best_line_san:
        return _compared_lines(critical)
    if critical.kind in ("c", "e"):
        moves = critical.line_san
    elif critical.kind == "d":
        moves = [critical.explosive.san] + critical.explosive.trap_line_san
    else:
        moves = p.pv_san
    if not moves:
        return ""
    line = _told_moves("Variante", p, moves)
    trapping = _trap_replies(critical)
    if trapping:
        line += "\n" + _trap_line(p, critical.explosive, trapping[0])
    if critical.kind == "d" and p.pv_san:
        line += "\n" + _told_moves("Variante du meilleur coup", p, p.pv_san)
    return line


def _evaluation(win: float) -> str:
    """État de la position d'après le % de gain de Nico."""
    if win >= 60:
        return "avantage Nico"
    if win <= 40:
        return "avantage adverse"
    return "équilibre"


def _to_english(text: str) -> str:
    """Notation française résiduelle du LLM → anglaise (C→N, F→B, T→R, D→Q)."""
    return _FR_PIECE_RE.sub(lambda m: _FR_TO_EN[m.group(1)] + m.group(2), text)


def _level_line(summary: dict) -> str:
    """Données de niveau de la partie (précision Lichess, erreurs adverses punies, résultat)."""
    parts = []
    if summary["accuracy"] is not None:
        parts.append(f"précision Nico : {summary['accuracy']:.0f} %")
    parts.append(f"erreurs adverses punies : {summary['opponent_errors_punished']}"
                 f"/{summary['opponent_errors']}")
    parts.append(f"résultat : {summary['result'] or '?'} ({_OUTCOME_FR[summary['outcome']]})")
    return "Niveau (données) : " + " ; ".join(parts)


def _errors_by_gravity(summary: dict, side: str) -> str:
    """« 2 imprécisions, 1 gaffe » (catégories à zéro omises), « aucune » sinon."""
    parts = [f"{summary[f'{side}_{q}']} {one if summary[f'{side}_{q}'] == 1 else many}"
             for q, one, many in _ERRORS_FR if summary[f"{side}_{q}"]]
    return ", ".join(parts) or "aucune"


def _marks_key(summary: dict, analysis) -> str:
    """Clé des pastilles avec comptes (sprint 51) : qualités toi / adversaire ; explosif / brillant
    et piège pour Nico seul (non calculés pour l'adversaire)."""
    parts = [f"{_QUALITY_MARK[q]} {label} {summary[f'nico_{q}']} / {summary[f'opponent_{q}']}"
             for q, label in _MARKS_KEY]
    traps = sum(1 for c in analysis.explosive if _trap_replies(c))
    brilliant = sum(1 for p in analysis.plies if p.color == analysis.nico_color
                    and is_brilliant(p.fen_before, p.uci, p.win_before, p.loss))
    parts.append(f"{_MARK_EXPLOSIVE} explosif / brillant {len(analysis.explosive) - traps + brilliant}")
    parts.append(f"{_MARK_TRAP} piège {traps}")
    parts.append(f"{_MARK_BEST} meilleur coup du moteur")
    return " · ".join(parts)


def _elo_suffix(elo: int | None) -> str:
    """« (1354) » si l'Elo est connu, sinon rien."""
    return f" ({elo})" if elo is not None else ""


def _day(game: dict) -> str:
    """Jour AAAA-MM-JJ d'une fiche : même règle que `_game_day` (interfaces/meta_commands.py),
    recopiée ici pour ne pas faire dépendre le routeur du module Telegram (dette #204)."""
    return (game.get("date") or game.get("timestamp") or "")[:10].replace(".", "-")


def _rank_line(summary: dict, games: list) -> str:
    """Dernière ligne du bilan (sprint 52, étendue sprint 55) : rang de la précision sur toutes
    les fiches, sur celles du même jour et sur celles de la même ouverture (groupe + couleur).
    Un segment jour ou ouverture qui ne porte que sur 1 partie est omis."""
    accuracy = summary["accuracy"]

    def segment(subset: list, label: str = "") -> str | None:
        rank, total = accuracy_rank(accuracy, subset)
        if label and total <= 1:
            return None
        return f"{'1re' if rank == 1 else f'{rank}e'} sur {total}{label}"

    # Jour de la partie courante ; sans date PGN, la fiche vient d'être écrite aujourd'hui.
    day = _day(summary) or date.today().isoformat()
    segments = [segment(games), segment([g for g in games if _day(g) == day], " aujourd'hui")]
    if summary["opening"]:
        group, color = game_opening_group(summary), summary["nico_color"]
        same = [g for g in games if g.get("opening") and g.get("nico_color") == color
                and game_opening_group(g) == group]
        segments.append(segment(same, f" en {group} ({_COLOR_FR[color]})"))
    return f"🏅 Précision {accuracy:.0f} % : " + " · ".join(s for s in segments if s)


def _moves_line(summary: dict, analysis) -> str:
    """Bloc déterministe sous le texte LLM (tronçon 08, sprint 50) : précision, meilleurs
    coups et erreurs des deux camps, coups brillants, meilleur et pire coup, clé des pastilles."""
    lines = []
    if summary["accuracy"] is not None:
        # Sprint 52 : Elo officiel de chaque camp entre parenthèses, quand il est connu.
        line = f"🎯 Précision : toi {summary['accuracy']:.0f} %" + _elo_suffix(summary["elo_nico"])
        if summary["accuracy_opponent"] is not None:
            line += f" · adversaire {summary['accuracy_opponent']:.0f} %" + _elo_suffix(summary["elo_opponent"])
        lines.append(line)
        # Sprint 56 : précision adverse anormalement haute sur une partie assez longue.
        acc_opp = summary["accuracy_opponent"]
        if (acc_opp is not None and summary["opponent_moves"] >= _SUSPECT_MIN_MOVES
                and acc_opp >= _SUSPECT_MIN_ACCURACY):
            elo = summary["elo_opponent"]
            lines.append(f"⚠️ Précision adverse {acc_opp:.0f} % sur {summary['opponent_moves']} coups"
                         + (f" ({elo} Elo)" if elo is not None else "") + " : à surveiller")
    lines.append(f"Meilleurs coups : toi {summary['nico_best']}/{summary['nico_moves']}"
                 f" · adversaire {summary['opponent_best']}/{summary['opponent_moves']}")
    lines.append(f"Erreurs : toi {_errors_by_gravity(summary, 'nico')}"
                 f" · adversaire {_errors_by_gravity(summary, 'opponent')}")
    if summary["brilliant_moves"]:
        lines.append(f"💥 Coups brillants : {summary['brilliant_moves']}")
    parts = []
    if summary["best_move"]:
        parts.append(f"meilleur coup {summary['best_move']} "
                     f"(trouvé par {summary['best_move_p'] * 100:.0f} % des joueurs de ton niveau)")
    if summary["worst_move"]:
        parts.append(f"pire coup {summary['worst_move']} "
                     f"({summary['worst_win_before']:.0f} % → {summary['worst_win_after']:.0f} %)")
    if parts:
        line = " · ".join(parts)
        lines.append(line[0].upper() + line[1:])
    lines.append(_marks_key(summary, analysis))
    return "\n".join(lines)


def _signed(x: float) -> str:
    """ΔR arrondi signé, − typographique (comme _material_line)."""
    n = round(x)
    return f"+{n}" if n >= 0 else f"−{abs(n)}"


def _history_line(after) -> str:
    """Données d'historique pour la ligne « Bilan : » du LLM."""
    g = after.ratings["global"]
    return (f"Historique (données) : {after.n_games} parties saison 1, classement global "
            f"{round(g.value)} (niveau {g.level}), {_signed(after.last_game['global'].delta)} "
            "sur cette partie")


def _trial_text(trial) -> str:
    """Épreuve qui a le plus pesé : « 17.Qb3 trouvé (difficulté ≈1950) »."""
    if trial.label == "résultat":
        return f"{_RESULT_FR[trial.score]} contre {round(trial.difficulty)}"
    text = (f"{trial.label} {'trouvé' if trial.score else 'raté'} "
            f"(difficulté ≈{round(trial.difficulty, -1):.0f})")
    return f"{text}, {trial.mate}" if trial.mate else text


def _motif_fr(motif: str) -> str:
    """Libellé français d'un motif (« fork » → « fourchette ») pour le bloc enrichi."""
    if motif in MATE_LABELS:
        return MATE_LABELS[motif]
    label = LABELS["hanging" if motif == "hangingPiece" else motif]
    return label[0].lower() + label[1:]


def _rating_line(key: str, before, after) -> str:
    """« ⬆️ Punir les erreurs 1385 (+25) · niveau 13 atteint » (flèche si palier changé)."""
    rating, gd = after.ratings[key], after.last_game[key]
    line = f"{LABELS[key]} {round(rating.value)} ({_signed(gd.delta)})"
    old = before.ratings[key].level if before.ratings else rating.level
    if rating.level > old:
        return f"⬆️ {line} · niveau {rating.level} atteint"
    if rating.level < old:
        return f"⬇️ {line} · retour au niveau {rating.level}"
    return f"{line} · niveau {rating.level}" if key == "global" else line


def _phases_line(after) -> str:
    """Ligne fixe des trois phases, affichée même à variation nulle."""
    return " · ".join(
        f"{LABELS[key]} {round(after.ratings[key].value)} ({_signed(after.last_game[key].delta)})"
        for key in _PHASE_THEMES
    )


def _progression_block(before, after, summary: dict) -> str:
    """Bloc « Progression » écrit par le router (exact par construction).
    Chaîne vide si la partie n'entre pas dans la saison (fiche ignorée)."""
    if after.n_games == before.n_games:
        return ""
    first = before.n_games == 0
    lines = ["🎮 Progression — saison 1 lancée" if first
             else f"🎮 Progression — saison 1, partie {after.n_games}"]
    lines.append(_rating_line("global", before, after))
    if not first:
        lines.append(_phases_line(after))
        # Thèmes dont l'épreuve décisive est la même : une seule ligne, segments
        # joints par « · », texte de l'épreuve une fois (ordre de LABELS).
        merged = {}
        for key in LABELS:
            gd = after.last_game[key]
            if key == "global" or key in _PHASE_THEMES or round(gd.delta) == 0:
                continue
            merged.setdefault(gd.top.label, (gd.top, []))[1].append(
                _rating_line(key, before, after))
        for trial, segments in merged.values():
            lines.append(f"{' · '.join(segments)} : {_trial_text(trial)}")
    for badge in after.badges:
        if badge in before.badges:
            continue
        if badge == "Tueur de géant":
            gap = summary["elo_opponent"] - summary["elo_nico"]
            reason = f"victoire contre un adversaire à {summary['elo_opponent']} (+{gap})"
        else:
            reason = _BADGE_REASON[badge]
        lines.append(f"🏆 Badge débloqué : {badge} — {reason}")
    if not first and summary["opening"]:
        group = game_opening_group(summary)
        stats = after.openings.get((group, summary["nico_color"]))
        if stats:
            lines.append(
                f"📖 {group} ({_COLOR_FR[summary['nico_color']]}) : "
                f"{stats.wins} V, {stats.draws} N, {stats.losses} D — {stats.win_rate * 100:.0f} %"
            )
    return "\n".join(lines)


def _reply_start(p) -> tuple:
    """(numéro, couleur) du premier coup adverse après le coup de Nico en p."""
    if p.color == "white":
        return p.move_number, "black"
    return p.move_number + 1, "white"


def _explosive_lines(p, e, nico_color: str) -> list:
    """Faits moteur du coup explosif d'une position de sorte d : l'idée, les réponses
    humaines probables (Maia, Elo adverse), l'espérance face à un humain, la variante
    si l'adversaire joue la réponse la plus probable."""
    lines = [f"  explosif {_move_label(p.move_number, p.color, e.san)}!?"]
    facts = []
    # Matériel : pièce offerte (posée en prise) prioritaire sur le sacrifice de ligne.
    if e.offered:
        facts.append(f"offre {_PIECE_FR.get(e.san[0], 'le pion')} ({e.offered})")
    elif max(e.sacrifice, e.accepted):
        facts.append(f"sacrifie {max(e.sacrifice, e.accepted)} pion(s) sur la ligne")
    if e.forcing:
        facts.append("forçant : " + "/".join(_FORCING_FR[f] for f in e.forcing))
    if facts:
        lines.append("  " + " ; ".join(facts))
    top = e.replies[0]
    lines.append(f"  réponse humaine la plus probable : {top['san']} ({top['p'] * 100:.0f} %)")
    lines.append(f"  espérance face à un humain : Nico {e.expected:.0f} % "
                 f"(meilleur coup : {e.best_expected:.0f} %)")
    # Admis par la seule règle sprint 28 (sacrifice / piège) : c'est un pari.
    if e.expected - e.best_expected < _GAIN_MIN:
        lines.append("  pari : face à un humain l'espérance n'est pas meilleure que le meilleur coup")
    number, color = _reply_start(p)
    # Admis sans avantage clair (sacrifice accepté avec échec) : pas de variante.
    if e.evidence is not None:
        lines.append(f"  variante : {_format_line(e.trap_line_san, number, color)} "
                     f"({_EVIDENCE_FR[e.evidence]})")
        after = chess.Board(p.fen_before)
        after.push_san(e.san)
        lines.append(f"  faits : {_move_facts(after.fen(), e.trap_line_san, number, color)}")
        lines.append(f"  fin de variante : {_material_line(e.trap_end_fen, nico_color)}, "
                     f"% de gain Nico {e.trap_end_win:.0f} %")
        lines.append(f"  fin de variante, {_attacked_line(e.trap_end_fen)}")
    for reply in e.replies:
        lines.append(f"  si {reply['san']} ({reply['p'] * 100:.0f} %) : "
                     f"{_format_line(reply['line_san'], number, color)}, {reply['win']:.0f} % pour Nico")
    return lines


def _win_drop(before: float, after: float, drop: float) -> str:
    """« 62 % → 41 % (−21 pts) » : % de gain de Nico, comme la courbe et la page."""
    return f"{before:.0f} % → {after:.0f} % (−{drop:.0f} pts)"


def _point_colors(analysis) -> list:
    """Couleur de chaque point de la courbe : le point d'une position porte le coup joué depuis
    elle. Par priorité : erreur, piège, explosif, brillant, meilleur coup (bleu), correct (blanc), sinon neutre ; la dernière
    position n'a pas de coup. La stratégie n'est calculée qu'à l'échiquier."""
    explosive = {c.ply.ply: c for c in analysis.explosive}
    colors = []
    for p in analysis.plies:
        found = explosive.get(p.ply)
        if p.loss >= _ERROR_POINT_MIN:
            colors.append(error_arrow(p.loss)[:3])
        elif found and _trap_replies(found):
            colors.append(TRAP_ARROW[:3])
        elif found or is_brilliant(p.fen_before, p.uci, p.win_before, p.loss):
            colors.append(ALT_ARROW[:3])
        else:
            colors.append({"best": CURVE_BEST, "correct": CURVE_CORRECT}.get(p.quality, CURVE_NEUTRAL))
    return colors + [CURVE_NEUTRAL]


def _caption(index: int, critical, plies: list) -> str:
    p = critical.ply
    if critical.kind == "e":
        prev = plies[p.ply - 1]
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"tournant après {_played_mark(prev)} {_move_label(prev.move_number, prev.color, prev.san)}?, "
                f"joué {_played_mark(p)} {_move_label(p.move_number, p.color, p.san)} "
                f"(meilleur {_MARK_BEST} {_move_label(p.move_number, p.color, p.best_san)})")
    if critical.kind == "c":
        return (f"Position {index} — coup {p.move_number} : "
                f"{_played_mark(p)} {_move_label(p.move_number, p.color, p.san)}, seul bon coup — bien joué, "
                f"2e meilleur coup : {_win_drop(p.win_before, p.win_before - p.second_gap, p.second_gap)}")
    if critical.kind == "d":
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"joué {_played_mark(p)} {_move_label(p.move_number, p.color, p.san)}, "
                f"explosif {_MARK_TRAP if _trap_replies(critical) else _MARK_EXPLOSIVE} "
                f"{_move_label(p.move_number, p.color, critical.explosive.san)}!? "
                f"(meilleur {_MARK_BEST} {_move_label(p.move_number, p.color, p.best_san)})")
    return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
            f"joué {_played_mark(p)} {_move_label(p.move_number, p.color, p.san)}, "
            f"meilleur {_MARK_BEST} {_move_label(p.move_number, p.color, p.best_san)}, "
            f"évaluation : {_win_drop(p.win_before, p.win_after, p.loss)}")


def _think_caption(index: int, p, seconds: float, think_verdict: str) -> str:
    """Légende d'une réflexion longue hors positions critiques, écrite par le code."""
    caption = (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
               f"joué {_played_mark(p)} {_move_label(p.move_number, p.color, p.san)} en {seconds:.0f} s, "
               f"meilleur {_MARK_BEST} {_move_label(p.move_number, p.color, p.best_san)}, "
               f"évaluation : {_win_drop(p.win_before, p.win_after, p.loss)}")
    return caption + (f"\nVerdict : {think_verdict}." if think_verdict else "")


def _conversion_caption(idea) -> str:
    """Légende de la miniature de conversion : idée répétée et coup joué à sa 1re apparition."""
    p = idea.first
    return (f"Conversion — coup {p.move_number} : idée répétée {_MARK_BEST} "
            f"{_move_label(p.move_number, p.color, idea.san)} ({idea.concept}), proposée {len(idea.moves)} fois ; "
            f"joué {_played_mark(p)} {_move_label(p.move_number, p.color, p.san)}")


# Début d'entrée « Position N — » en début de ligne (gras Markdown toléré) ;
# une ligne « Bilan : » clôt la dernière entrée.
_ENTRY_RE = re.compile(r"^\**Position (\d+)\**\s*[—–-]\**\s*", re.MULTILINE)
_LEVEL_RE = re.compile(r"^\**Bilan\b", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"[.!?…](?=\s|$)")

# Limite Telegram d'une légende de photo.
_CAPTION_MAX = 1024


def _fit_entry(entry: str, budget: int) -> str:
    """Entrée ≤ budget : coupée à la dernière phrase complète qui tient, puis « … »."""
    if len(entry) <= budget:
        return entry
    head = entry[:budget - 2]
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(head)]
    return (head[:ends[-1]] if ends else head).rstrip() + " …"


def _split_entries(text: str, images: list) -> tuple:
    """
    Déplace l'entrée « Position N » du LLM dans la légende de l'image N.

    Retourne (texte restant, images). Si une entrée 1…len(images) manque,
    texte et images sont rendus tels quels (pas de découpage partiel).
    """
    marks = list(_ENTRY_RE.finditer(text))
    found = {int(m.group(1)): m for m in marks}
    if not images or any(i not in found for i in range(1, len(images) + 1)):
        log.info("chess_caption_split FALLBACK images=%d entries=%s",
                 len(images), sorted(found))
        return text, images

    # Fin d'une entrée : début de l'entrée suivante, ligne « Bilan », ou fin du texte.
    bounds = [m.start() for m in marks] + [m.start() for m in _LEVEL_RE.finditer(text)]
    rest, cursor, captioned = [], 0, []
    for m in marks:
        n = int(m.group(1))
        if n > len(images):
            continue
        end = min([b for b in bounds if b > m.start()] + [len(text)])
        rest.append(text[cursor:m.start()])
        cursor = end
        entry = text[m.end():end].strip()
        factual = images[n - 1]["caption"]
        captioned.append((n, factual + "\n" + _fit_entry(entry, _CAPTION_MAX - len(factual) - 1)))
    rest.append(text[cursor:])

    new_images = [dict(img) for img in images]
    for n, caption in captioned:
        new_images[n - 1]["caption"] = caption
    remaining = re.sub(r"\n{3,}", "\n\n", "".join(rest)).strip()
    log.info("chess_caption_split OK images=%d", len(images))
    return remaining, new_images


def _game_hash(ucis) -> str:
    """Identité d'une partie : hash des coups seuls (pas des en-têtes), le même PGN
    recopié sans en-têtes reste la même partie, doc_id chess_game_<hash>."""
    return hashlib.sha256("".join(ucis).encode()).hexdigest()[:16]


def _pgn_hash(text: str) -> str | None:
    """Hash calculé sans moteur, avant l'analyse (None si PGN illisible)."""
    game = parse_pgn(text)
    return _game_hash(m.uci() for m in game.mainline_moves()) if game else None


def _same_game(fiche: dict, ucis: list, players: set) -> bool:
    """Sprint 56 : la fiche et la partie reçue sont la même partie si les coups de
    l'une sont le début exact des coups de l'autre et si l'adversaire de la fiche
    est l'un des joueurs (`players` : noms en minuscules). Couvre le PGN coupé
    plus tôt comme le PGN complété ; un hash identique est traité avant."""
    known = [p["uci"] for p in json.loads(fiche.get("plies_json") or "[]")]
    n = min(len(known), len(ucis))
    opponent = (fiche.get("opponent") or "").lower()
    return n > 0 and known[:n] == ucis[:n] and bool(opponent) and opponent in players


def _prefix_fiche(known: dict, text: str) -> dict | None:
    """Fiche connue qui est la même partie que le PGN reçu (préfixe), sinon None."""
    game = parse_pgn(text)
    if game is None:
        return None
    ucis = [m.uci() for m in game.mainline_moves()]
    players = {game.headers.get(key, "").lower() for key in ("White", "Black")}
    return next((f for f in known.values() if _same_game(f, ucis, players)), None)


def _pgn_length(text: str) -> int:
    """Nombre de demi-coups de la ligne principale du PGN."""
    return sum(1 for _ in parse_pgn(text).mainline_moves())


def _fiche_without_clock(fiche: dict) -> bool:
    """Fiche dont aucun demi-coup n'a d'horloge (PGN envoyé sans `%clk`).
    Fiche sans demi-coups (marqueur de doublon interne) → False : pas de réanalyse."""
    plies = json.loads(fiche.get("plies_json") or "[]")
    return bool(plies) and all(p.get("clock") is None for p in plies)


def _pgn_has_clock(text: str) -> bool:
    """Au moins un coup de la ligne principale porte une horloge `[%clk …]`."""
    game = parse_pgn(text)
    return game is not None and any(node.clock() is not None for node in game.mainline())


def _reanalyze(fiche: dict, text: str) -> bool:
    """Sprint 51 : une partie déjà envoyée sans horloge est réanalysée quand le PGN
    recollé apporte les horloges ; sinon c'est un doublon."""
    return _pgn_has_clock(text) and _fiche_without_clock(fiche)


def _duplicate_text(game: dict) -> str:
    """Réponse à une partie déjà enregistrée : une phrase écrite par le code.
    La date est celle de l'envoi (timestamp de la fiche), pas celle de la partie."""
    opponent = game.get("opponent")
    date = game.get("timestamp", "")[:10]
    return (f"Cette partie{f' contre {opponent}' if opponent else ''} a déjà été envoyée"
            f"{f' le {date}' if date else ''}.")


class ChessExecutionRouter(BaseRouter):
    """
    Effecteur « coach d'échecs » du pipeline d'exécution.

    Args:
        llm_execution_router : LLMExecutionRouter — production de l'explication
        mempalace_bridge     : MempalaceBridge — relecture des fiches (bloc Progression)
    """

    def __init__(self, llm_execution_router, mempalace_bridge):
        self.llm_execution_router = llm_execution_router
        self.mempalace_bridge = mempalace_bridge

    def execute(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})

        # Plusieurs parties (sprint 42) : toutes analysées, réponse groupée.
        games = split_pgn(message)
        if len(games) > 1:
            return self._execute_many(games, metadata)

        game_hash = _pgn_hash(message)
        fiches = self._known_games()
        known = fiches.get(f"chess_game_{game_hash}")
        timestamp, replaces = None, None
        if known is not None:
            if not _reanalyze(known, message):
                log.info("chess_router duplicate hash=%s", game_hash)
                return {"text": _duplicate_text(known)}
            log.info("chess_router reanalyze hash=%s reason=clock", game_hash)
            timestamp = known.get("timestamp")
        elif (prefix := _prefix_fiche(fiches, message)) is not None:
            # Sprint 56 : même partie coupée (doublon) ou complétée (remplace la fiche).
            if _pgn_length(message) <= len(json.loads(prefix["plies_json"])):
                log.info("chess_router duplicate hash=%s prefix_of=%s", game_hash, prefix["id"])
                return {"text": _duplicate_text(prefix)}
            timestamp, replaces = prefix.get("timestamp"), prefix["id"]

        analysis = analyze(message, message, config.stockfish_path, config.maia_models_dir,
                           self._past_games())
        if analysis is None:
            log.warning("chess_router PGN unreadable")
            return self.llm_execution_router.execute({
                "op_type" : CognitiveOperation.REASONING.value,
                "content" : f"[PGN illisible : dis-le à Nico en une phrase.]\n\n{message}",
                "metadata": metadata,
            })
        return self._execute_game(analysis, message, metadata, timestamp=timestamp, replaces=replaces)

    def _past_games(self) -> list:
        """(couleur de Nico, coups UCI) des fiches ; palace indisponible → aucune, l'analyse continue."""
        try:
            return [(g["nico_color"], [p["uci"] for p in json.loads(g["plies_json"])])
                    for g in self.mempalace_bridge.load_chess_games()]
        except Exception:
            log.exception("chess_past_games ERROR")
            return []

    def _known_games(self) -> dict:
        """Fiches par doc_id ; palace indisponible → aucune, l'analyse continue."""
        try:
            return {g["id"]: g for g in self.mempalace_bridge.load_chess_games()}
        except Exception:
            log.exception("chess_known_games ERROR")
            return {}

    def _execute_many(self, games: list[str], metadata: dict) -> dict:
        """Une analyse complète par partie, puis fusion en une seule réponse.

        Images concaténées (légende préfixée « Partie k — »), puis un bloc de
        texte par partie sous son titre ; une partie illisible ou déjà envoyée
        tient une ligne.
        """
        texts, images, ok = [], [], 0
        known = self._known_games()
        for k, game in enumerate(games, 1):
            game_hash = _pgn_hash(game)
            fiche = known.get(f"chess_game_{game_hash}")
            timestamp, replaces = None, None
            if fiche is not None:
                if not _reanalyze(fiche, game):
                    log.info("chess_router duplicate hash=%s game=%d", game_hash, k)
                    texts.append(f"Partie {k} — déjà envoyée")
                    continue
                log.info("chess_router reanalyze hash=%s reason=clock", game_hash)
                timestamp = fiche.get("timestamp")
            elif (prefix := _prefix_fiche(known, game)) is not None:
                # Sprint 56 : même partie coupée (doublon) ou complétée (remplace la fiche).
                if _pgn_length(game) <= len(json.loads(prefix["plies_json"])):
                    log.info("chess_router duplicate hash=%s prefix_of=%s game=%d", game_hash, prefix["id"], k)
                    texts.append(f"Partie {k} — déjà envoyée")
                    continue
                timestamp, replaces = prefix.get("timestamp"), prefix["id"]
            analysis = analyze(game, game, config.stockfish_path, config.maia_models_dir,
                               self._past_games())
            if analysis is None:
                log.warning("chess_router PGN unreadable game=%d", k)
                texts.append(f"Partie {k} — PGN illisible")
                continue
            result = self._execute_game(analysis, game, metadata, timestamp=timestamp, replaces=replaces)
            # La même partie plus loin dans ce message est aussi un doublon.
            known[f"chess_game_{game_hash}"] = {}
            known.pop(replaces, None)
            ok += 1
            h = analysis.headers
            title = f"Partie {k} — {h.get('White', '?')} – {h.get('Black', '?')} ({h.get('Result', '*')})"
            texts.append(f"{title}\n{result['text']}")
            images += [{**img, "caption": f"Partie {k} — {img['caption']}"} for img in result["images"]]
        log.info("chess_router multi games=%d ok=%d", len(games), ok)
        return {"text": "\n\n".join(texts), "images": images}

    def _execute_game(self, analysis, message: str, metadata: dict,
                      timestamp: str | None = None, replaces: str | None = None) -> dict:
        """Pipeline d'une partie analysée : diagrammes, fiche, progression, LLM.
        timestamp : date de la fiche réanalysée, conservée (None = nouvelle partie).
        replaces  : doc_id de la fiche tronquée que cette partie complète (sprint 56),
                    supprimée une fois la nouvelle fiche écrite."""
        # ── Diagrammes : un PNG par position critique ────────────────────────
        out_dir = Path(config.image_output_dir) / "chess"
        out_dir.mkdir(parents=True, exist_ok=True)
        images = []
        # Sprint 51 : réflexions longues de Nico (PGN avec horloges), verdict écrit par le code.
        times = move_times(analysis.plies, analysis.headers.get("TimeControl"))
        elo = analysis.headers.get("WhiteElo" if analysis.nico_color == "white" else "BlackElo", "")
        elo = int(elo) if elo.isdigit() else None
        thinks = [(p, t, verdict(p, elo)) for p, t in long_thinks(analysis.plies, times, analysis.nico_color)]
        think_of = {p.ply: (t, v) for p, t, v in thinks}
        for i, critical in enumerate(analysis.critical, 1):
            out_path = out_dir / f"{uuid4().hex[:8]}_{i}.png"
            # Sorte d : 2e flèche pour le coup explosif, cyan s'il est piégeant, sinon orange.
            alt_uci = critical.explosive.uci if critical.kind == "d" else None
            # Sortes a et b : le coup joué est une erreur, sa flèche en dit la gravité.
            played_color = error_arrow(critical.ply.loss) if critical.kind in ("a", "b") else PLAYED_ARROW
            render_position(critical.ply.fen_before, analysis.nico_color,
                            critical.ply.best_uci, str(out_path), alt_uci=alt_uci,
                            played_uci=critical.ply.uci,
                            best_line_uci=critical.ply.pv_uci[:3], played_color=played_color,
                            alt_color=TRAP_ARROW if _trap_replies(critical) else ALT_ARROW)
            # La variante est écrite sous la ligne factuelle dès la création de la
            # légende : elle survit au repli chess_caption_split FALLBACK.
            caption = _caption(i, critical, analysis.plies)
            variant = _variant_line(critical)
            if variant:
                caption += "\n" + variant
            # Réflexion longue déjà position critique : pas de doublon, une ligne en plus.
            if critical.ply.ply in think_of:
                seconds, think_verdict = think_of[critical.ply.ply]
                caption += f"\n⏱️ réfléchi {seconds:.0f} s" + (f" · {think_verdict}" if think_verdict else "")
            images.append({"path": str(out_path), "caption": caption})
        # Autres réflexions longues : positions numérotées à la suite des critiques ;
        # elles reçoivent une entrée LLM « Pour jouer vite : » (avant _split_entries).
        critical_plies = {c.ply.ply for c in analysis.critical}
        extra_thinks = [(p, t, v) for p, t, v in thinks if p.ply not in critical_plies]
        for p, seconds, think_verdict in extra_thinks:
            index = len(images) + 1
            out_path = out_dir / f"{uuid4().hex[:8]}_{index}.png"
            render_position(p.fen_before, analysis.nico_color, p.best_uci, str(out_path),
                            played_uci=p.uci, best_line_uci=p.pv_uci[:3])
            images.append({"path": str(out_path), "caption": _think_caption(index, p, seconds, think_verdict)})

        # ── Fiche de partie (non bloquante) ──────────────────────────────────
        game_hash = _game_hash(p.uci for p in analysis.plies)
        summary = summarize(analysis)
        try:
            write_chess_game(summary_text(analysis, summary), game_hash, extra=summary,
                             room=opening_room(summary["opening_group"]), timestamp=timestamp)
            log.info("chess_game_write OK hash=%s plies=%d", game_hash, len(analysis.plies))
            # Supprimée avant le calcul de la progression : sinon la partie compterait
            # deux fois dans « avant ».
            if replaces:
                delete_chess_games([replaces])
                log.info("chess_router extend old=%s new=%s", replaces, game_hash)
        except Exception:
            log.exception("chess_game_write ERROR hash=%s", game_hash)

        # ── Progression (non bloquante) : profil avant / après cette partie ──
        # Recalculé depuis les fiches (la courante est en base depuis l'écriture).
        block, history, games = "", None, None
        try:
            games = self.mempalace_bridge.load_chess_games()
            before = build_profile([g for g in games if g["id"] != f"chess_game_{game_hash}"])
            after = build_profile(games)
            block = _progression_block(before, after, summary)
            if block:
                history = _history_line(after)
                log.info("chess_progression OK games=%d global=%d",
                         after.n_games, round(after.ratings["global"].value))
        except Exception:
            log.exception("chess_progression ERROR")

        story = story_line(analysis.plies, analysis.nico_color, summary["outcome"])
        # Sprint 51 : période gagnante non convertie, ligne écrite par le code.
        period = winning_period(analysis.plies, analysis.nico_color, summary["outcome"])
        ideas = repeated_ideas(period, analysis.plies) if period else []
        conversion = conversion_line(period, ideas) if period else None
        timing = time_line(analysis.plies, times, analysis.nico_color, period, summary["errors_low_clock"],
                           summary["outcome"], summary["termination"], summary["time_control"])
        enriched = self._build_enriched(analysis, message, _anchor(summary), summary, story, history,
                                        conversion, timing, extra_thinks, times)
        result = self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # Pas de skip_intent (Q4) : la partie doit aller en mémoire épisodique,
            # sous un intent imposé (le namer répondait « aucun », audit 05).
            # skip_history (tronçon 15) : les analyses passées en historique servaient
            # de moule au LLM ; l'échange reste écrit pour les questions de suivi.
            "metadata": {**metadata, "forced_intent_name": FORCED_INTENT_NAME,
                         "skip_history": True},
        })

        log.info("chess_router OK critical=%d images=%d", len(analysis.critical), len(images))
        # Chaque entrée « Position N » part en légende de son diagramme (tronçon 05).
        text, images = _split_entries(_to_english(result["text"]), images)
        # Déroulé du code sous le titre, puis les lignes Conversion et Temps, au-dessus du bilan du LLM.
        title, _, rest = text.partition("\n")
        head = "\n".join(line for line in (story, conversion, timing) if line)
        text = f"{title}\n{head}" + (f"\n{rest}" if rest else "")
        # Miniature de l'idée principale, hors budget des positions : ajoutée après le
        # découpage (le LLM n'a pas d'entrée « Position » pour elle), avant la courbe.
        if ideas:
            p = ideas[0].first
            mini_path = out_dir / f"{uuid4().hex[:8]}_conversion.png"
            render_position(p.fen_before, analysis.nico_color, p.best_uci, str(mini_path),
                            played_uci=p.uci, best_line_uci=p.pv_uci[:3])
            images.append({"path": str(mini_path), "caption": _conversion_caption(ideas[0])})
        # La courbe, ajoutée après ce découpage, reste la dernière image avant le bilan.
        curve_path = out_dir / f"{uuid4().hex[:8]}_curve.png"
        render_curve(nico_wins(analysis.plies, analysis.nico_color),
                     [p.move_number for p in analysis.plies], _point_colors(analysis), str(curve_path))
        images.append({"path": str(curve_path), "caption": "Courbe de la partie : % de gain de Nico"})
        moves_line = _moves_line(summary, analysis)
        if moves_line:
            text += "\n\n" + moves_line
        if block:
            text += "\n\n" + block
        # Rang de la précision : toujours la dernière ligne (fiches déjà chargées, courante incluse).
        if summary["accuracy"] is not None and games is not None:
            text += "\n\n" + _rank_line(summary, games)
        return {"text": text, "images": images}

    def _build_enriched(self, analysis, message: str, anchor: str, summary: dict,
                        story: str, history: str | None = None, conversion: str | None = None,
                        timing: str | None = None, extra_thinks: list = (), times: list | None = None) -> str:
        """Ancre de la partie, puis faits moteur en français, puis message original.
        times : temps par ply (move_times), None sans pendule."""
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
        lines.append(f"Déroulé (données) : {story}")
        cited = story_plies(analysis.plies, color)
        if cited:
            lines.append("Coups du déroulé, faits : " + " ; ".join(_played_facts(analysis, p) for p in cited))
        if conversion:
            lines.append(f"Conversion (données) : {conversion}")
        if timing:
            lines.append(f"Temps (données) : {timing}")
        if history:
            lines.append(history)
        for i, critical in enumerate(analysis.critical, 1):
            p = critical.ply
            tags = ", ".join(_TAG_FR.get(t, t) for t in p.tags) or "aucune"
            trap = bool(_trap_replies(critical))
            lines += [
                f"Position {i} ({_TRAP_KIND_FR if trap else _KIND_FR[critical.kind]}) — coup {p.move_number} :",
                f"  joué {_move_label(p.move_number, p.color, p.san)}, perte {p.loss:.0f} pts "
                f"de % de gain ({p.win_before:.0f} % → {p.win_after:.0f} %)",
                f"  suite jouée, faits : {_played_facts(analysis, p)}",
                f"  meilleur {_move_label(p.move_number, p.color, p.best_san)}, "
                f"ligne : {_format_line(p.pv_san, p.move_number, p.color)}",
                f"  faits : {_move_facts(p.fen_before, p.pv_san, p.move_number, p.color)}",
                f"  étiquettes : {tags}, phase : {_PHASE_FR[p.phase]}",
                _pieces_line(p.fen_before),
                f"  {_material_line(p.fen_before, color)}",
                f"  {_attacked_line(p.fen_before)}",
                f"  structure : {structure_line(p.fen_before, color)}",
                f"  évaluation : {_evaluation(p.win_before)} ({p.win_before:.0f} %)",
            ]
            if p.motifs:
                lines.append(f"  motifs : {', '.join(_motif_fr(m) for m in p.motifs)}")
            if critical.kind == "e":
                prev = analysis.plies[p.ply - 1]
                lines.append(f"  erreur adverse {_move_label(prev.move_number, prev.color, prev.san)} : "
                             f"perte {prev.loss:.0f} pts "
                             f"(meilleur {_move_label(prev.move_number, prev.color, prev.best_san)})")
                lines.append(f"  erreur adverse, faits : "
                             f"{_move_facts(prev.fen_before, [prev.san], prev.move_number, prev.color)}")
            if critical.best_line_san:
                lines.append(f"  suite du meilleur coup, faits : "
                             f"{_move_facts(p.fen_before, critical.best_line_san, p.move_number, p.color)}")
                lines.append(_line_end(p, critical.best_line_san, p.win_before))
                lines.append(f"  suite du coup joué, faits : "
                             f"{_move_facts(p.fen_before, critical.played_line_san, p.move_number, p.color)}")
                lines.append(_line_end(p, critical.played_line_san, p.win_after))
                intent = _intent_line(analysis.plies, p, times[p.ply] if times else None,
                                      critical.human_line_san)
                if intent:
                    lines.append(intent)
            if critical.kind in ("c", "e"):
                lines.append(f"  variante : {_format_line(critical.line_san, p.move_number, p.color)} "
                             f"({_EVIDENCE_FR[critical.evidence]})")
                lines.append(f"  faits : {_move_facts(p.fen_before, critical.line_san, p.move_number, p.color)}")
            # Piège : sa ligne est écrite par le code, le LLM n'en reçoit pas les faits.
            if critical.kind == "d" and not trap:
                lines += _explosive_lines(p, critical.explosive, color)
        # Réflexions longues hors positions critiques : numérotées à la suite.
        for k, (p, seconds, think_verdict) in enumerate(extra_thinks, len(analysis.critical) + 1):
            lines += [
                f"Position {k} (réflexion longue de {seconds:.0f} s) — coup {p.move_number} :",
                f"  joué {_move_label(p.move_number, p.color, p.san)}, perte {p.loss:.0f} pts "
                f"de % de gain ({p.win_before:.0f} % → {p.win_after:.0f} %)",
                f"  suite jouée, faits : {_played_facts(analysis, p)}",
                f"  meilleur {_move_label(p.move_number, p.color, p.best_san)}, "
                f"ligne : {_format_line(p.pv_san, p.move_number, p.color)}",
                f"  faits : {_move_facts(p.fen_before, p.pv_san, p.move_number, p.color)}",
                _pieces_line(p.fen_before),
                f"  {_material_line(p.fen_before, color)}",
                f"  {_attacked_line(p.fen_before)}",
                f"  structure : {structure_line(p.fen_before, color)}",
                f"  évaluation : {_evaluation(p.win_before)} ({p.win_before:.0f} %)",
            ]
            if p.motifs:
                lines.append(f"  motifs : {', '.join(_motif_fr(m) for m in p.motifs)}")
            if think_verdict:
                lines.append(f"  verdict : {think_verdict}")
        block = "\n".join(lines) + "]"

        elo = analysis.headers.get("WhiteElo" if color == "white" else "BlackElo", "")
        player = f"joueur d'environ {elo} Elo" if elo and elo != "?" else "joueur amateur"
        n = len(analysis.critical) + len(extra_thinks)
        consigne = (
            f"[Consigne : réponse COURTE à Nico, {player}. Format imposé : 1re ligne "
            f"exacte « {anchor} » ; puis une entrée pour chacune des {n} positions, de "
            f"Position 1 à Position {n}, aucune omise (Nico voit les diagrammes du même "
            "numéro), 1 à 3 phrases et 400 caractères : après « Position N — », commence par "
            "« Plan : » et dis quoi viser dans cette position (pièce à améliorer, colonne à "
            "occuper, pion ou roi à attaquer) d'après les lignes « structure », « évaluation », "
            "« motifs » et le but du meilleur coup (d'après ses faits) ; ne nomme une colonne, "
            "un pion ou un roi que s'il figure dans ces lignes ; exception, si la position a les "
            "lignes « suite du meilleur coup » et « suite du coup joué » : commence par « Pourquoi : » "
            "au lieu de « Plan : » et écris 3 phrases au plus : (1) l'idée probable de Nico, au "
            "conditionnel (« tu voulais sans doute… »), tirée de la ligne « idée du coup joué », dont "
            "les faits sont des indices et non une liste fermée (menace du coup adverse précédent, "
            "faits de « ton coup », temps : coup rapide = réflexe, long = réfléchi ; Maia : coup "
            "fréquent à ton niveau = coup naturel, rare = idée personnelle ; « suite probable » = ce "
            "que Nico avait sans doute calculé) : retiens celui qui explique le mieux le coup ; si "
            "aucun ne colle, dis que l'idée n'est pas claire plutôt que d'en inventer une ; (2) ce que cette idée a négligé, d'après « après ton coup » "
            "et la suite du coup joué, ses faits et sa fin ; (3) ce que fait le meilleur coup, d'après "
            "sa suite, ses faits et sa fin ; "
            "si un de ces faits dit « décloue », cite-le : le coup libère cette pièce ; "
            "ne dis qu'une pièce est prise ou épargnée que si ces faits le montrent ; n'énumère pas les coups "
            "de la variante : elle est affichée sous le diagramme ; au plus un chiffre "
            "réduit à « 50 % → 37 % », ou aucun ; chaque entrée commence en début de ligne par "
            "« Position N — » et ne recopie pas la ligne « coup … joué … meilleur … » "
            "(elle est déjà sous le diagramme) ; puis une ligne « Bilan : » de 3 à 5 phrases : part "
            "de la ligne « Déroulé (données) », relie la partie aux idées d'ouverture et de position, "
            "dis quoi travailler, en t'appuyant sur "
            "la ligne « Niveau (données) » et, si présente, la ligne « Historique (données) ». Les "
            "faits de la partie (coups, évaluations, causes) viennent uniquement des données du code. "
            "Partout, entrées et Bilan : ne dis qu'une pièce est prise, échangée, reprise ou épargnée "
            "que si une ligne « faits » le montre (dont « suite jouée » et « Coups du déroulé »). "
            "Aucune cause de "
            "défaite ou de victoire absente du déroulé ; n'annonce un mat que s'il est joué ou s'il "
            "figure dans une ligne, en disant s'il dépend d'une réponse adverse. Rien "
            "d'autre : pas de section « ce qui se passe ». Utilise "
            "uniquement les coups et lignes fournis ci-dessus ; n'invente aucun coup "
            "ni évaluation, ni emplacement de pièce : fie-toi à la liste des pièces. "
            "Ne décris aucune attaque, défense, menace ou colonne absente des lignes "
            "matériel / attaquées / structure / faits. Ne recopie ni ne paraphrase « matériel égal » "
            "ou « aucune attaquée ». Notation anglaise : N, B, R, Q, K.]"
        )
        parts = [block, consigne]
        if opening:
            parts.append(
                f"[Consigne : ouverture jouée : {opening}. Quand c'est "
                "pertinent, relie la position aux idées classiques de cette ouverture en une "
                "demi-phrase. Un gambit d'ouverture choisi par Nico est un choix assumé, "
                "pas une faute à corriger.]"
            )
        if n == 0:
            # Partie entièrement dans le répertoire : rien à numéroter.
            parts.append(
                "[Consigne : aucune position à commenter dans cette partie : n'écris aucune entrée "
                "« Position », seulement la 1re ligne et la ligne « Bilan : ».]"
            )
        if summary["opening_group"] == "Göring Gambit" and color == "white":
            parts.append(
                "[Consigne : dans ce Göring, Nico sacrifie un ou deux pions (d4, c3) pour ouvrir les "
                "colonnes c et d et les diagonales a1-h8 et a2-g8 à ses fous, et lancer une attaque "
                "forte sur plusieurs plans avec fous, dame, cavaliers (Nf3, Nd5) et tours. Tu peux "
                "nommer ces colonnes et diagonales. Ne présente jamais la reprise du pion sacrifié "
                "comme l'idée du Göring : reprendre en d4 du cavalier, c'est la Scotch normale.]"
            )
        if any(c.kind == "e" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque tournant, nomme l'erreur adverse et montre la "
                "variante qui la punit (coups fournis).]"
            )
        if any(_trap_replies(c) for c in analysis.critical):
            parts.append(
                f"[Consigne : pour chaque position « {_TRAP_KIND_FR} », écris seulement le plan, "
                "sans parler du piège ni de mat : la ligne « Piège » est sous le diagramme.]"
            )
        if any(c.kind == "d" and not _trap_replies(c) for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque occasion explosive : d'abord le plan, puis l'idée en une phrase ; la "
                "variante si l'adversaire joue la réponse humaine la plus probable (coups fournis, rien "
                "au-delà) et l'avantage atteint (critère fourni), expliqué par les pièces "
                "protégées / vulnérables de la fin de variante ; quelles réponses humaines "
                "probables perdent et ce qu'elles coûtent à l'adversaire, d'après les lignes "
                "« si … ». Ne donne ni le coût, ni quand le tenter, et ne le présente jamais "
                "comme le meilleur coup. Si la ligne « pari » est présente, une demi-phrase "
                "la présente comme une idée risquée. Cette entrée peut dépasser 3 phrases.]"
            )
        if extra_thinks:
            parts.append(
                "[Consigne : pour chaque position « réflexion longue », l'entrée commence par "
                "« Pour jouer vite : » au lieu de « Plan : » et donne en 1 à 2 phrases l'idée ou le plan "
                "qui permettait de choisir vite, d'après ses lignes de données ; elle ne répète pas "
                "le verdict.]"
            )
        if not timing:
            if lost_on_time(summary["outcome"], summary["termination"]):
                parts.append(
                    "[Consigne : aucune donnée de pendule : ne parle pas de gestion du temps ; la partie "
                    "est perdue au temps : dis seulement « perdu au temps, pendule non fournie ».]"
                )
            else:
                parts.append("[Consigne : aucune donnée de pendule : ne parle pas de gestion du temps.]")
        if conversion:
            parts.append(
                "[Consigne : dans le Bilan, une phrase par idée nommée dans la ligne « Conversion "
                "(données) », expliquant pourquoi ce concept fait progresser une position gagnante, "
                "sans autre coup que ceux fournis.]"
            )
        if analysis.color_source == "default":
            parts.append(
                "[Consigne : signale que tu as supposé que Nico joue les blancs faute "
                "de pseudo, et qu'il peut préciser « je joue les noirs ».]"
            )
        return "\n".join(parts) + f"\n\n{message}"
