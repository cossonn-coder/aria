# aria/chess_coach/combination.py
#
# Pointe d'une combinaison (sprint 61, tronçon 01).
#
# À partir de la suite du meilleur coup d'une erreur de Nico, repère le coup
# où se fait le gain matériel final, le coup qui le prépare (clouage absolu
# sur le roi), le coup adverse qui a amené le roi sur la ligne du clouage et
# le défenseur éliminé en chemin. Fonction pure : python-chess, sans moteur.

import chess

_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def _label(board: chess.Board, sq: int) -> str:
    """« Nf3 » pour une pièce, « pion e5 » pour un pion (convention du router)."""
    piece = board.piece_at(sq)
    if piece.piece_type == chess.PAWN:
        return f"pion {chess.square_name(sq)}"
    return f"{piece.symbol().upper()}{chess.square_name(sq)}"


def _balance(board: chess.Board, nico: chess.Color) -> int:
    """Matériel de Nico moins matériel adverse."""
    return sum(value * (len(board.pieces(piece, nico)) - len(board.pieces(piece, not nico)))
               for piece, value in _VALUES.items())


def point_of(fen: str, line_san: list, nico_color: str) -> dict | None:
    """Pointe de la suite line_san (coup de Nico en tête) jouée depuis fen.

    None si la suite ne gagne pas de matériel ou si aucune prise de Nico ne
    fixe ce gain. Voir docs/sprint61/01_calcul_pointe.md pour chaque champ.
    """
    nico = chess.WHITE if nico_color == "white" else chess.BLACK
    board = chess.Board(fen)
    initial = _balance(board, nico)
    # Positions avant chaque coup (boards[i]) et soldes après chaque coup (balances[i]).
    boards, moves, balances = [], [], []
    for san in line_san:
        move = board.parse_san(san)
        boards.append(board.copy(stack=False))
        moves.append(move)
        board.push(move)
        balances.append(_balance(board, nico))
    if not balances or balances[-1] <= initial:
        return None
    final = balances[-1]

    # Gain : première prise de Nico après laquelle le solde ne redescend plus sous le final.
    gain = next((i for i in range(0, len(moves), 2)
                 if boards[i].is_capture(moves[i]) and min(balances[i:]) >= final), None)
    if gain is None:
        return None
    won_square = moves[gain].to_square
    prep = gain - 2 if gain >= 2 else None

    # Clouage absolu, dans la position après le coup préparatoire, de la pièce prise au gain.
    pin = brought = None
    if prep is not None:
        after_prep = boards[prep + 1]
        # La pièce prise peut n'arriver sur la case qu'après la préparation (interposition
        # sur un échec) : case vide, pas de clouage (run live sprint 68, plantage).
        if after_prep.color_at(won_square) == (not nico) and after_prep.is_pinned(not nico, won_square):
            king = after_prep.king(not nico)
            pin = (_label(after_prep, won_square), _label(after_prep, king))
            # Coup adverse, avant la préparation, qui a amené le roi sur sa case.
            brought = next((i for i in range(prep - 1, 0, -2) if moves[i].to_square == king), None)

    # Défenseur éliminé : première prise de Nico, avant le gain, d'une pièce qui défendait la case gagnée.
    defender = next(((i, _label(boards[i], moves[i].to_square)) for i in range(0, gain, 2)
                     if boards[i].is_capture(moves[i])
                     and moves[i].to_square in boards[i].attackers(not nico, won_square)), None)

    return {"gain": gain, "won": _label(boards[gain], won_square), "prep": prep, "pin": pin,
            "brought": brought, "defender": defender}
