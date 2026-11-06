# aria/chess_coach/conversion.py
#
# Conversion d'une position gagnante (sprint 51, tronçon 02).
#
# Quand Nico ne gagne pas une partie où il a longtemps été gagnant, le code
# repère la période gagnante (coups consécutifs de Nico à ≥ 80 %) et les idées
# du moteur répétées qu'il n'a pas jouées (même meilleur coup proposé ≥ 3 fois
# dans une fenêtre de 6 coups), chacune nommée par son concept.
# Module pur : fonctions sur des PlyAnalysis, aucun import mémoire / LLM.

from dataclasses import dataclass

import chess

from chess_coach.structure import _passed

_WIN_MIN = 80
_PERIOD_MIN = 10
_IDEA_MIN = 3
_IDEA_WINDOW = 6
_IDEAS_MAX = 2

_PIECE_FR = {chess.PAWN: "le pion", chess.KNIGHT: "le cavalier", chess.BISHOP: "le fou",
             chess.ROOK: "la tour", chess.QUEEN: "la dame"}


@dataclass
class Idea:
    """Idée du moteur répétée et non jouée pendant la période gagnante."""
    san: str
    moves: list          # numéros de coup où elle était proposée et non jouée
    first: object        # PlyAnalysis du 1er coup où elle était proposée
    played_at: int | None  # numéro du coup où Nico l'a finalement jouée
    concept: str


def winning_period(plies: list, nico_color: str, outcome: str) -> list | None:
    """Plus longue suite de coups consécutifs de Nico à win_before ≥ 80, si ≥ 10 coups,
    pour une défaite ou une nulle seulement ; sinon None."""
    if outcome not in ("loss", "draw"):
        return None
    best, run = [], []
    for p in (p for p in plies if p.color == nico_color):
        run = run + [p] if p.win_before >= _WIN_MIN else []
        if len(run) > len(best):
            best = run
    return best if len(best) >= _PERIOD_MIN else None


def _concept(p) -> str:
    """Concept du meilleur coup, depuis la position avant le coup."""
    board = chess.Board(p.fen_before)
    move = chess.Move.from_uci(p.best_uci)
    piece = board.piece_at(move.from_square)
    if piece.piece_type == chess.KING:
        return "activer le roi"
    if piece.piece_type == chess.PAWN:
        if move.from_square in _passed(board, piece.color):
            return "pousser le pion passé"
        return "avancer le pion"
    if board.is_capture(move):
        # Prise en passant : la case d'arrivée est vide, la pièce prise est un pion.
        captured = board.piece_at(move.to_square)
        name = _PIECE_FR[captured.piece_type] if captured else "le pion"
        return f"prendre {name} {chess.square_name(move.to_square)}"
    return "améliorer " + _PIECE_FR[piece.piece_type]


def repeated_ideas(period: list, plies: list) -> list:
    """Idées répétées de la période (≤ 2), par occurrences décroissantes puis chronologie."""
    index = {p.ply: i for i, p in enumerate(period)}
    missed = {}
    for p in period:
        if p.best_san != p.san:
            missed.setdefault(p.best_san, []).append(p)
    ideas = []
    for san, found in missed.items():
        pos = [index[p.ply] for p in found]
        # ≥ 3 occurrences dans une fenêtre de 6 coups consécutifs de Nico.
        if not any(pos[k + _IDEA_MIN - 1] - pos[k] < _IDEA_WINDOW for k in range(len(pos) - _IDEA_MIN + 1)):
            continue
        first = found[0]
        played = next((q.move_number for q in plies
                       if q.ply > first.ply and q.color == first.color and q.san == san), None)
        ideas.append(Idea(san, [p.move_number for p in found], first, played, _concept(first)))
    ideas.sort(key=lambda i: (-len(i.moves), i.first.ply))
    return ideas[:_IDEAS_MAX]


def conversion_line(period: list, ideas: list) -> str:
    """Ligne Conversion, écrite par le code."""
    line = (f"🔄 Conversion : {len(period)} coups à {_WIN_MIN} % ou plus "
            f"(coups {period[0].move_number} à {period[-1].move_number}) sans gagner.")
    if not ideas:
        return line
    parts = []
    for idea in ideas:
        played = f"joué au {idea.played_at}" if idea.played_at is not None else "jamais joué"
        parts.append(f"{idea.concept} ({idea.san}, proposé aux coups "
                     f"{', '.join(str(n) for n in idea.moves)}, {played})")
    return line + " Idées du moteur non jouées : " + " ; ".join(parts) + "."


def ideas_text(ideas: list) -> str | None:
    """Idées pour la fiche : « Kd3 activer le roi ×4 ; b5 pousser le pion passé ×5 »."""
    return " ; ".join(f"{i.san} {i.concept} ×{len(i.moves)}" for i in ideas) or None
