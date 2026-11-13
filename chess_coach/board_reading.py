# aria/chess_coach/board_reading.py
#
# Grille lue sur une image → FEN (sprint 59, tronçon 01).
#
# La grille arrive telle qu'affichée (rangée du haut d'abord, chaque rangée de
# gauche à droite). On en déduit le camp affiché en bas, le trait et les roques.
# Module pur : aucun import mémoire, LLM ou réseau.

import re

import chess

_WHITE_RE = re.compile(r"\bblancs?\b", re.IGNORECASE)
_BLACK_RE = re.compile(r"\bnoirs?\b", re.IGNORECASE)

# Raisons lisibles des drapeaux de chess.Board.status(), dans l'ordre de priorité.
_STATUS_REASONS = (
    (chess.STATUS_NO_WHITE_KING, "pas de roi blanc"),
    (chess.STATUS_NO_BLACK_KING, "pas de roi noir"),
    (chess.STATUS_TOO_MANY_KINGS, "trop de rois"),
    (chess.STATUS_PAWNS_ON_BACKRANK, "pion sur la première ou la dernière rangée"),
    (chess.STATUS_OPPOSITE_CHECK, "le camp qui n'a pas le trait est en échec"),
    (chess.STATUS_TOO_MANY_WHITE_PIECES, "trop de pièces blanches"),
    (chess.STATUS_TOO_MANY_BLACK_PIECES, "trop de pièces noires"),
    (chess.STATUS_TOO_MANY_WHITE_PAWNS, "trop de pions blancs"),
    (chess.STATUS_TOO_MANY_BLACK_PAWNS, "trop de pions noirs"),
)

# Roques : (roi, tour, lettre FEN), sur les cases d'origine.
_CASTLING = (
    (chess.E1, chess.H1, chess.WHITE, "K"),
    (chess.E1, chess.A1, chess.WHITE, "Q"),
    (chess.E8, chess.H8, chess.BLACK, "k"),
    (chess.E8, chess.A8, chess.BLACK, "q"),
)


def side_from_caption(caption: str | None) -> str | None:
    """« blanc(s) » seul → "white", « noir(s) » seul → "black", sinon None."""
    if not caption:
        return None
    white = bool(_WHITE_RE.search(caption))
    black = bool(_BLACK_RE.search(caption))
    if white and not black:
        return "white"
    if black and not white:
        return "black"
    return None


def _mean_row(rows: list[str], piece: str) -> float | None:
    """Indice de rangée affichée moyen d'une pièce, None si absente."""
    found = [i for i, row in enumerate(rows) for c in row if c == piece]
    return sum(found) / len(found) if found else None


def _bottom_side(rows: list[str], to_move: str | None) -> str:
    """Camp affiché en bas : pions, sinon rois, sinon trait donné, sinon blancs."""
    for white_piece, black_piece in (("P", "p"), ("K", "k")):
        white_row = _mean_row(rows, white_piece)
        black_row = _mean_row(rows, black_piece)
        if white_row is not None and black_row is not None and white_row != black_row:
            # Indice plus grand = plus bas à l'écran.
            return "white" if white_row > black_row else "black"
    return to_move or "white"


def grid_to_fen(rows: list[str], caption: str | None) -> tuple[str, str]:
    """
    Convertit une grille affichée en FEN.

    Returns:
        (fen, bottom) : bottom est le camp affiché en bas ("white"/"black"),
        c'est l'orientation à passer à render_position.
    """
    to_move = side_from_caption(caption)
    bottom = _bottom_side(rows, to_move)

    # Blancs en bas : rangée affichée 0 = rang 8, colonnes a→h.
    # Noirs en bas : rangée affichée 0 = rang 1, colonnes h→a.
    if bottom == "white":
        ranks = rows
    else:
        ranks = [row[::-1] for row in reversed(rows)]

    board = chess.Board(None)
    for i, row in enumerate(ranks):
        rank = 7 - i
        for file, c in enumerate(row):
            if c != ".":
                board.set_piece_at(chess.square(file, rank), chess.Piece.from_symbol(c))

    # Trait : légende, sinon le camp du bas (règle de Nico).
    turn = to_move or bottom
    board.turn = chess.WHITE if turn == "white" else chess.BLACK

    # Roque possible si roi et tour sont sur leurs cases d'origine.
    rights = ""
    for king_sq, rook_sq, color, letter in _CASTLING:
        if (board.piece_at(king_sq) == chess.Piece(chess.KING, color)
                and board.piece_at(rook_sq) == chess.Piece(chess.ROOK, color)):
            rights += letter
    board.set_castling_fen(rights or "-")

    return board.fen(), bottom


def position_problem(fen: str) -> str | None:
    """None si la position est légale, sinon une raison courte en français."""
    board = chess.Board(fen)
    if board.is_valid():
        return None
    status = board.status()
    # Deux rois d'une même couleur : drapeau « trop de rois », message plus précis.
    if status & chess.STATUS_TOO_MANY_KINGS:
        if len(board.pieces(chess.KING, chess.WHITE)) > 1:
            return "deux rois blancs"
        if len(board.pieces(chess.KING, chess.BLACK)) > 1:
            return "deux rois noirs"
    for flag, reason in _STATUS_REASONS:
        if status & flag:
            return reason
    return "position impossible"
