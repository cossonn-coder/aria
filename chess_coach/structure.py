# aria/chess_coach/structure.py
#
# Faits structurels d'une position (sprint 46, tronçon 02) : le LLM écrit son « Plan : »
# à partir de cette ligne au lieu d'inventer colonnes, pions et rois.
#
# Module pur : aucun import mémoire, LLM ou exécution, et rien d'évaluatif (ni « bon », ni « faible »).

import chess

_FILES = "abcdefgh"

# Cases de départ des pièces mineures, par camp.
_MINOR_HOMES = {
    chess.WHITE: ((chess.B1, chess.KNIGHT), (chess.C1, chess.BISHOP),
                  (chess.F1, chess.BISHOP), (chess.G1, chess.KNIGHT)),
    chess.BLACK: ((chess.B8, chess.KNIGHT), (chess.C8, chess.BISHOP),
                  (chess.F8, chess.BISHOP), (chess.G8, chess.KNIGHT)),
}


def _pawn_files(board: chess.Board, color: chess.Color) -> set:
    return {chess.square_file(sq) for sq in board.pieces(chess.PAWN, color)}


def _isolated(board: chess.Board, color: chess.Color) -> list:
    files = _pawn_files(board, color)
    return [sq for sq in board.pieces(chess.PAWN, color)
            if not files & {chess.square_file(sq) - 1, chess.square_file(sq) + 1}]


def _doubled(board: chess.Board, color: chess.Color) -> list:
    pawns = list(board.pieces(chess.PAWN, color))
    return [sq for sq in pawns
            if sum(chess.square_file(o) == chess.square_file(sq) for o in pawns) > 1]


def _passed(board: chess.Board, color: chess.Color) -> list:
    """Pions sans pion adverse devant eux, sur leur colonne ni sur les colonnes voisines."""
    enemies = list(board.pieces(chess.PAWN, not color))

    def ahead(sq: int, enemy: int) -> bool:
        if color == chess.WHITE:
            return chess.square_rank(enemy) > chess.square_rank(sq)
        return chess.square_rank(enemy) < chess.square_rank(sq)

    return [sq for sq in board.pieces(chess.PAWN, color)
            if not any(abs(chess.square_file(e) - chess.square_file(sq)) <= 1 and ahead(sq, e)
                       for e in enemies)]


def _king_text(board: chess.Board, color: chess.Color) -> str:
    """Case du roi, roqué ou au centre si l'une des deux s'applique, pions devant lui.

    Le FEN ne garde pas l'historique : « roqué » = roi sur sa 1re rangée, à l'aile.
    """
    king = board.king(color)
    file, rank = chess.square_file(king), chess.square_rank(king)
    home = 0 if color == chess.WHITE else 7
    step = 1 if color == chess.WHITE else -1
    shield = sum(
        1 for sq in board.pieces(chess.PAWN, color)
        if abs(chess.square_file(sq) - file) <= 1 and chess.square_rank(sq) - rank in (step, 2 * step)
    )
    parts = [chess.square_name(king)]
    if file in (3, 4):
        parts.append("au centre")
    elif rank == home and file != 5:
        parts.append("roqué")
    parts.append(f"{shield} pion{'s' if shield > 1 else ''} devant")
    return ", ".join(parts)


def _undeveloped(board: chess.Board, color: chess.Color) -> list:
    """Pièces mineures encore sur leur case de départ, notées « Nb1 »."""
    return [f"{chess.piece_symbol(piece).upper()}{chess.square_name(sq)}"
            for sq, piece in _MINOR_HOMES[color]
            if board.piece_at(sq) == chess.Piece(piece, color)]


def structure_line(fen: str, nico_color: str) -> str:
    """Faits structurels en une ligne, du point de vue de Nico ; une catégorie vide n'apparaît pas."""
    board = chess.Board(fen)
    nico = chess.WHITE if nico_color == "white" else chess.BLACK
    nico_files, other_files = _pawn_files(board, nico), _pawn_files(board, not nico)

    def files_text(files) -> str:
        return ", ".join(_FILES[f] for f in sorted(files))

    def sides_text(nico_items: list, other_items: list) -> str:
        sides = []
        if nico_items:
            sides.append("Nico " + " ".join(nico_items))
        if other_items:
            sides.append("adversaire " + " ".join(other_items))
        return ", ".join(sides)

    def pawns_text(find) -> str:
        return sides_text([chess.square_name(sq) for sq in find(board, nico)],
                          [chess.square_name(sq) for sq in find(board, not nico)])

    candidates = (
        ("colonnes ouvertes", files_text(set(range(8)) - nico_files - other_files)),
        ("colonnes semi-ouvertes pour Nico", files_text(other_files - nico_files)),
        ("colonnes semi-ouvertes pour l'adversaire", files_text(nico_files - other_files)),
        ("pions isolés", pawns_text(_isolated)),
        ("pions doublés", pawns_text(_doubled)),
        ("pions passés", pawns_text(_passed)),
        ("roi de Nico", _king_text(board, nico)),
        ("roi adverse", _king_text(board, not nico)),
        ("pièces mineures sur leur case de départ",
         sides_text(_undeveloped(board, nico), _undeveloped(board, not nico))),
    )
    return " ; ".join(f"{label} : {text}" for label, text in candidates if text)
