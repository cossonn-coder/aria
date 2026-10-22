# aria/chess_coach/motifs.py
#
# Tagueur de motifs tactiques (sprint 29, tronçon 02), à la manière des thèmes
# de puzzles Lichess.
#
# Source : portage de `tagger/cook.py` et des fonctions utilisées de
# `tagger/util.py` / `tagger/model.py` de lichess-puzzler
# (https://github.com/ornicar/lichess-puzzler), licence AGPL-3.0.
# Le code porté garde sa logique (noms et commentaires d'origine en anglais) ;
# ce qui est ajouté ou adapté est commenté en français :
#   - entrée `tag_motifs` (construction du Puzzle depuis un FEN + une ligne) ;
#   - tri des tags : seuls les motifs tactiques et les mats sont rendus (pas
#     d'évaluation, de longueur, de finale, de côté d'attaque, etc.) ;
#   - onze mats nommés supplémentaires (fin de fichier).
# Module pur : aucun import mémoire / LLM / exécution.

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import chess
import chess.pgn
from chess import (
    square_rank,
    square_file,
    Board,
    Color,
    SquareSet,
    Piece,
    Square,
    square_distance,
)
from chess import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from chess.pgn import ChildNode, Game


# ---------------------------------------------------------------------------
# Entrée publique (ajout ARIA)
# ---------------------------------------------------------------------------


def tag_motifs(fen_before_opponent: str, opponent_uci: str, line_uci: list) -> list[str]:
    """Rend les motifs tactiques de la ligne (clés anglaises stables, façon Lichess).

    Format du Puzzle Lichess : la partie démarre AVANT le coup adverse, la
    mainline vaut [coup adverse, meilleur coup de Nico, suite de la PV…] et le
    pov est le camp de Nico (celui qui ne joue pas au départ).
    """
    game = Game()
    game.setup(Board(fen_before_opponent))
    node = game
    for uci in [opponent_uci, *line_uci]:
        node = node.add_variation(chess.Move.from_uci(uci))
    return cook(_Puzzle(game))


@dataclass
class _Puzzle:
    # Équivalent de model.Puzzle sans `id` ni `cp` (inutiles ici).
    game: Game
    pov: Color = field(init=False)
    mainline: List[ChildNode] = field(init=False)

    def __post_init__(self):
        self.pov = not self.game.turn()
        self.mainline = list(self.game.mainline())


def cook(puzzle: _Puzzle) -> List[str]:
    tags: List[str] = []

    # Un seul mat nommé par ligne : ceux de cook.py d'abord, puis les ajouts.
    # Un mat sans motif nommé rend "mate" seul (compté au classement « Mats »).
    if is_mate(puzzle):
        tags.append(named_mate(puzzle) or "mate")

    if attraction(puzzle):
        tags.append("attraction")

    if deflection(puzzle):
        tags.append("deflection")

    if advanced_pawn(puzzle):
        tags.append("advancedPawn")

    if double_check(puzzle):
        tags.append("doubleCheck")

    if sacrifice(puzzle):
        tags.append("sacrifice")

    if x_ray(puzzle):
        tags.append("xRayAttack")

    if fork(puzzle):
        tags.append("fork")

    if hanging_piece(puzzle):
        tags.append("hangingPiece")

    if trapped_piece(puzzle):
        tags.append("trappedPiece")

    if discovered_attack(puzzle):
        tags.append("discoveredAttack")

    if exposed_king(puzzle):
        tags.append("exposedKing")

    if skewer(puzzle):
        tags.append("skewer")

    if collinear(puzzle):
        tags.append("collinearMove")

    if self_interference(puzzle) or interference(puzzle):
        tags.append("interference")

    if intermezzo(puzzle):
        tags.append("intermezzo")

    if pin_prevents_attack(puzzle) or pin_prevents_escape(puzzle):
        tags.append("pin")

    if attacking_f2_f7(puzzle):
        tags.append("attackingF2F7")

    if clearance(puzzle):
        tags.append("clearance")

    if capturing_defender(puzzle):
        tags.append("capturingDefender")

    return tags


def is_mate(puzzle: _Puzzle) -> bool:
    # Adapté de mate_in : on exige que ce soit l'adversaire qui soit mat (une
    # PV peut, en théorie, finir sur un mat contre Nico ; un puzzle Lichess non).
    board = puzzle.game.end().board()
    return board.is_checkmate() and board.turn != puzzle.pov


def named_mate(puzzle: _Puzzle) -> Optional[str]:
    # Ordre de cook.py, puis les mats ajoutés (ordre du plus spécifique au plus large).
    if smothered_mate(puzzle):
        return "smotheredMate"
    if back_rank_mate(puzzle):
        return "backRankMate"
    if anastasia_mate(puzzle):
        return "anastasiaMate"
    if hook_mate(puzzle):
        return "hookMate"
    if arabian_mate(puzzle):
        return "arabianMate"
    found = boden_or_double_bishop_mate(puzzle)
    if found:
        return found
    if dovetail_mate(puzzle):
        return "dovetailMate"
    for detector in _EXTRA_MATES:
        found = detector(puzzle)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# util.py (fonctions utilisées)
# ---------------------------------------------------------------------------


def moved_piece_type(node: ChildNode) -> chess.PieceType:
    pt = node.board().piece_type_at(node.move.to_square)
    assert pt
    return pt


def is_advanced_pawn_move(node: ChildNode) -> bool:
    if node.move.promotion:
        return True
    if moved_piece_type(node) != chess.PAWN:
        return False
    to_rank = square_rank(node.move.to_square)
    return to_rank < 3 if node.turn() else to_rank > 4


def is_very_advanced_pawn_move(node: ChildNode) -> bool:
    if not is_advanced_pawn_move(node):
        return False
    to_rank = square_rank(node.move.to_square)
    return to_rank < 2 if node.turn() else to_rank > 5


def is_king_move(node: ChildNode) -> bool:
    return moved_piece_type(node) == chess.KING


def is_castling(node: ChildNode) -> bool:
    return is_king_move(node) and square_distance(node.move.from_square, node.move.to_square) > 1


def is_capture(node: ChildNode) -> bool:
    return node.parent.board().is_capture(node.move)


def next_node(node: ChildNode) -> Optional[ChildNode]:
    return node.variations[0] if node.variations else None


def next_next_node(node: ChildNode) -> Optional[ChildNode]:
    nn = next_node(node)
    return next_node(nn) if nn else None


values = {PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9}
king_values = {PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9, KING: 99}
ray_piece_types = [QUEEN, ROOK, BISHOP]


def material_count(board: Board, side: Color) -> int:
    return sum(len(board.pieces(piece_type, side)) * value for piece_type, value in values.items())


def material_diff(board: Board, side: Color) -> int:
    return material_count(board, side) - material_count(board, not side)


def attacked_opponent_squares(board: Board, from_square: Square, pov: Color) -> List[Tuple[Piece, Square]]:
    pieces = []
    for attacked_square in board.attacks(from_square):
        attacked_piece = board.piece_at(attacked_square)
        if attacked_piece and attacked_piece.color != pov:
            pieces.append((attacked_piece, attacked_square))
    return pieces


def is_defended(board: Board, piece: Piece, square: Square) -> bool:
    if board.attackers(piece.color, square):
        return True
    # ray defense https://lichess.org/editor/6k1/3q1pbp/2b1p1p1/1BPp4/rp1PnP2/4PRNP/4Q1P1/4B1K1_w_-_-_0_1
    for attacker in board.attackers(not piece.color, square):
        attacker_piece = board.piece_at(attacker)
        assert attacker_piece
        if attacker_piece.piece_type in ray_piece_types:
            bc = board.copy(stack=False)
            bc.remove_piece_at(attacker)
            if bc.attackers(piece.color, square):
                return True
    return False


def is_hanging(board: Board, piece: Piece, square: Square) -> bool:
    return not is_defended(board, piece, square)


def can_be_taken_by_lower_piece(board: Board, piece: Piece, square: Square) -> bool:
    for attacker_square in board.attackers(not piece.color, square):
        attacker = board.piece_at(attacker_square)
        assert attacker
        if attacker.piece_type != chess.KING and values[attacker.piece_type] < values[piece.piece_type]:
            return True
    return False


def is_in_bad_spot(board: Board, square: Square) -> bool:
    # hanging or takeable by lower piece
    piece = board.piece_at(square)
    assert piece
    return bool(board.attackers(not piece.color, square)) and (
        is_hanging(board, piece, square) or can_be_taken_by_lower_piece(board, piece, square)
    )


def is_trapped(board: Board, square: Square) -> bool:
    if board.is_check() or board.is_pinned(board.turn, square):
        return False
    piece = board.piece_at(square)
    assert piece
    if piece.piece_type in [PAWN, KING]:
        return False
    if not is_in_bad_spot(board, square):
        return False
    for escape in board.legal_moves:
        if escape.from_square == square:
            capturing = board.piece_at(escape.to_square)
            if capturing and values[capturing.piece_type] >= values[piece.piece_type]:
                return False
            board.push(escape)
            if not is_in_bad_spot(board, escape.to_square):
                return False
            board.pop()
    return True


def attacker_pieces(board: Board, color: Color, square: Square) -> List[Piece]:
    return [p for p in [board.piece_at(s) for s in board.attackers(color, square)] if p]


def squares_are_collinear(sq1: Square, sq2: Square, sq3: Square) -> bool:
    r1, f1 = square_rank(sq1), square_file(sq1)
    r2, f2 = square_rank(sq2), square_file(sq2)
    r3, f3 = square_rank(sq3), square_file(sq3)
    if r1 == r2 == r3:
        return True
    if f1 == f2 == f3:
        return True
    if (r1 - f1) == (r2 - f2) == (r3 - f3):
        return True
    if (r1 + f1) == (r2 + f2) == (r3 + f3):
        return True
    return False


# ---------------------------------------------------------------------------
# cook.py (détecteurs de motifs retenus)
# ---------------------------------------------------------------------------


def advanced_pawn(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if is_very_advanced_pawn_move(node):
            return True
    return False


def double_check(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if len(node.board().checkers()) > 1:
            return True
    return False


def sacrifice(puzzle: _Puzzle) -> bool:
    # down in material compared to initial position, after moving
    diffs = [material_diff(n.board(), puzzle.pov) for n in puzzle.mainline]
    initial = diffs[0]
    for d in diffs[1::2][1:]:
        if d - initial <= -2:
            return not any(n.move.promotion for n in puzzle.mainline[::2][1:])
    return False


def x_ray(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        if not is_capture(node):
            continue
        prev_op_node = node.parent
        assert isinstance(prev_op_node, ChildNode)
        if prev_op_node.move.to_square != node.move.to_square or moved_piece_type(prev_op_node) == KING:
            continue
        prev_pl_node = prev_op_node.parent
        assert isinstance(prev_pl_node, ChildNode)
        if prev_pl_node.move.to_square != prev_op_node.move.to_square:
            continue
        if prev_op_node.move.from_square in SquareSet.between(node.move.from_square, node.move.to_square):
            return True
    return False


def fork(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][:-1]:
        if moved_piece_type(node) is not KING:
            board = node.board()
            if is_in_bad_spot(board, node.move.to_square):
                continue
            nb = 0
            for piece, square in attacked_opponent_squares(board, node.move.to_square, puzzle.pov):
                if piece.piece_type == PAWN:
                    continue
                if king_values[piece.piece_type] > king_values[moved_piece_type(node)] or (
                    is_hanging(board, piece, square)
                    and square not in board.attackers(not puzzle.pov, node.move.to_square)
                ):
                    nb += 1
            if nb > 1:
                return True
    return False


def hanging_piece(puzzle: _Puzzle) -> bool:
    to = puzzle.mainline[1].move.to_square
    captured = puzzle.mainline[0].board().piece_at(to)
    if puzzle.mainline[0].board().is_check() and (not captured or captured.piece_type == PAWN):
        return False
    if captured and captured.piece_type != PAWN:
        if is_hanging(puzzle.mainline[0].board(), captured, to):
            op_move = puzzle.mainline[0].move
            op_capture = puzzle.game.board().piece_at(op_move.to_square)
            if (
                op_capture
                and values[op_capture.piece_type] >= values[captured.piece_type]
                and op_move.to_square == to
            ):
                return False
            if len(puzzle.mainline) < 4:
                return True
            if material_diff(puzzle.mainline[3].board(), puzzle.pov) >= material_diff(
                puzzle.mainline[1].board(), puzzle.pov
            ):
                return True
    return False


def trapped_piece(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        square = node.move.to_square
        captured = node.parent.board().piece_at(square)
        if captured and captured.piece_type != PAWN:
            prev = node.parent
            assert isinstance(prev, ChildNode)
            if prev.move.to_square == square:
                square = prev.move.from_square
            if is_trapped(prev.parent.board(), square):
                return True
    return False


def discovered_attack(puzzle: _Puzzle) -> bool:
    if discovered_check(puzzle):
        return True
    for node in puzzle.mainline[1::2][1:]:
        if is_capture(node):
            between = SquareSet.between(node.move.from_square, node.move.to_square)
            assert isinstance(node.parent, ChildNode)
            if node.parent.move.to_square == node.move.to_square:
                return False
            prev = node.parent.parent
            assert isinstance(prev, ChildNode)
            if (
                prev.move.from_square in between
                and node.move.to_square != prev.move.to_square
                and node.move.from_square != prev.move.to_square
                and not is_castling(prev)
            ):
                return True
    return False


def discovered_check(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        checkers = board.checkers()
        if checkers and node.move.to_square not in checkers:
            return True
    return False


def attraction(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1:]:
        if node.turn() == puzzle.pov:
            continue
        # 1. player moves to a square
        first_move_to = node.move.to_square
        opponent_reply = next_node(node)
        # 2. opponent captures on that square
        if opponent_reply and opponent_reply.move.to_square == first_move_to:
            attracted_piece = moved_piece_type(opponent_reply)
            if attracted_piece in [KING, QUEEN, ROOK]:
                attracted_to_square = opponent_reply.move.to_square
                n2 = next_node(opponent_reply)
                if n2:
                    attackers = n2.board().attackers(puzzle.pov, attracted_to_square)
                    # 3. player attacks that square
                    if n2.move.to_square in attackers:
                        # 4. player checks on that square
                        if attracted_piece == KING:
                            return True
                        n3 = next_next_node(n2)
                        # 4. or player later captures on that square
                        if n3 and n3.move.to_square == attracted_to_square:
                            return True
    return False


def deflection(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        captured_piece = node.parent.board().piece_at(node.move.to_square)
        if captured_piece or node.move.promotion:
            capturing_piece = moved_piece_type(node)
            if captured_piece and king_values[captured_piece.piece_type] > king_values[capturing_piece]:
                continue
            square = node.move.to_square
            prev_op_move = node.parent.move
            assert prev_op_move
            grandpa = node.parent.parent
            assert isinstance(grandpa, ChildNode)
            prev_player_move = grandpa.move
            prev_player_capture = grandpa.parent.board().piece_at(prev_player_move.to_square)
            if (
                (
                    not prev_player_capture
                    or values[prev_player_capture.piece_type] < moved_piece_type(grandpa)
                )
                and square != prev_op_move.to_square
                and square != prev_player_move.to_square
                and (prev_op_move.to_square == prev_player_move.to_square or grandpa.board().is_check())
                and (
                    square in grandpa.board().attacks(prev_op_move.from_square)
                    or node.move.promotion
                    and square_file(node.move.to_square) == square_file(prev_op_move.from_square)
                    and node.move.from_square in grandpa.board().attacks(prev_op_move.from_square)
                )
                and (square not in node.parent.board().attacks(prev_op_move.to_square))
            ):
                return True
    return False


def exposed_king(puzzle: _Puzzle) -> bool:
    if puzzle.pov:
        pov = puzzle.pov
        board = puzzle.mainline[0].board()
    else:
        pov = not puzzle.pov
        board = puzzle.mainline[0].board().mirror()
    king = board.king(not pov)
    assert king is not None
    if chess.square_rank(king) < 5:
        return False
    squares = SquareSet.from_square(king - 8)
    if chess.square_file(king) > 0:
        squares.add(king - 1)
        squares.add(king - 9)
    if chess.square_file(king) < 7:
        squares.add(king + 1)
        squares.add(king - 7)
    for square in squares:
        if board.piece_at(square) == Piece(PAWN, not pov):
            return False
    for node in puzzle.mainline[1::2][1:-1]:
        if node.board().is_check():
            return True
    return False


def skewer(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        prev = node.parent
        assert isinstance(prev, ChildNode)
        capture = prev.board().piece_at(node.move.to_square)
        if capture and moved_piece_type(node) in ray_piece_types and not node.board().is_checkmate():
            between = SquareSet.between(node.move.from_square, node.move.to_square)
            op_move = prev.move
            assert op_move
            if op_move.to_square == node.move.to_square or op_move.from_square not in between:
                continue
            if king_values[moved_piece_type(prev)] > king_values[capture.piece_type] and is_in_bad_spot(
                prev.board(), node.move.to_square
            ):
                return True
    return False


def self_interference(puzzle: _Puzzle) -> bool:
    # intereference by opponent piece
    for node in puzzle.mainline[1::2][1:]:
        prev_board = node.parent.board()
        square = node.move.to_square
        capture = prev_board.piece_at(square)
        if capture and is_hanging(prev_board, capture, square):
            grandpa = node.parent.parent
            assert grandpa
            init_board = grandpa.board()
            defenders = init_board.attackers(capture.color, square)
            defender = defenders.pop() if defenders else None
            defender_piece = init_board.piece_at(defender) if defender else None
            if defender and defender_piece and defender_piece.piece_type in ray_piece_types:
                if node.parent.move and node.parent.move.to_square in SquareSet.between(square, defender):
                    return True
    return False


def interference(puzzle: _Puzzle) -> bool:
    # intereference by player piece
    for node in puzzle.mainline[1::2][1:]:
        prev_board = node.parent.board()
        square = node.move.to_square
        capture = prev_board.piece_at(square)
        assert node.parent.move
        if capture and square != node.parent.move.to_square and is_hanging(prev_board, capture, square):
            assert node.parent
            assert node.parent.parent
            assert node.parent.parent.parent
            init_board = node.parent.parent.parent.board()
            defenders = init_board.attackers(capture.color, square)
            defender = defenders.pop() if defenders else None
            defender_piece = init_board.piece_at(defender) if defender else None
            if defender and defender_piece and defender_piece.piece_type in ray_piece_types:
                interfering = node.parent.parent
                if interfering.move and interfering.move.to_square in SquareSet.between(square, defender):
                    return True
    return False


def intermezzo(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        if is_capture(node):
            capture_move = node.move
            capture_square = node.move.to_square
            op_node = node.parent
            assert isinstance(op_node, ChildNode)
            prev_pov_node = node.parent.parent
            assert isinstance(prev_pov_node, ChildNode)
            if op_node.move.from_square not in prev_pov_node.board().attackers(not puzzle.pov, capture_square):
                if prev_pov_node.move.to_square != capture_square:
                    prev_op_node = prev_pov_node.parent
                    assert isinstance(prev_op_node, ChildNode)
                    return (
                        prev_op_node.move.to_square == capture_square
                        and is_capture(prev_op_node)
                        and capture_move in prev_op_node.board().legal_moves
                    )
    return False


# the pinned piece can't attack a player piece
def pin_prevents_attack(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        for square, piece in board.piece_map().items():
            if piece.color == puzzle.pov:
                continue
            pin_dir = board.pin(piece.color, square)
            if pin_dir == chess.BB_ALL:
                continue
            for attack in board.attacks(square):
                attacked = board.piece_at(attack)
                if (
                    attacked
                    and attacked.color == puzzle.pov
                    and attack not in pin_dir
                    and (
                        values[attacked.piece_type] > values[piece.piece_type]
                        or is_hanging(board, attacked, attack)
                    )
                ):
                    return True
    return False


# the pinned piece can't escape the attack
def pin_prevents_escape(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        for pinned_square, pinned_piece in board.piece_map().items():
            if pinned_piece.color == puzzle.pov:
                continue
            pin_dir = board.pin(pinned_piece.color, pinned_square)
            if pin_dir == chess.BB_ALL:
                continue
            for attacker_square in board.attackers(puzzle.pov, pinned_square):
                if attacker_square in pin_dir:
                    attacker = board.piece_at(attacker_square)
                    assert attacker
                    if values[pinned_piece.piece_type] > values[attacker.piece_type]:
                        return True
                    if (
                        is_hanging(board, pinned_piece, pinned_square)
                        and pinned_square not in board.attackers(not puzzle.pov, attacker_square)
                        and [
                            m
                            for m in board.pseudo_legal_moves
                            if m.from_square == pinned_square and m.to_square not in pin_dir
                        ]
                    ):
                        return True
    return False


def attacking_f2_f7(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        square = node.move.to_square
        if node.parent.board().piece_at(node.move.to_square) and square in [chess.F2, chess.F7]:
            king = node.board().piece_at(chess.E8 if square == chess.F7 else chess.E1)
            return king is not None and king.piece_type == KING and king.color != puzzle.pov
    return False


def clearance(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        board = node.board()
        if not node.parent.board().piece_at(node.move.to_square):
            piece = board.piece_at(node.move.to_square)
            if piece and piece.piece_type in ray_piece_types:
                prev = node.parent.parent
                assert prev
                prev_move = prev.move
                assert prev_move
                assert isinstance(node.parent, ChildNode)
                if (
                    not prev_move.promotion
                    and prev_move.to_square != node.move.from_square
                    and prev_move.to_square != node.move.to_square
                    and not node.parent.board().is_check()
                    and (not board.is_check() or moved_piece_type(node.parent) != KING)
                ):
                    if prev_move.from_square == node.move.to_square or prev_move.from_square in SquareSet.between(
                        node.move.from_square, node.move.to_square
                    ):
                        if (
                            prev.parent
                            and not prev.parent.board().piece_at(prev_move.to_square)
                            or is_in_bad_spot(prev.board(), prev_move.to_square)
                        ):
                            return True
    return False


def collinear(puzzle: _Puzzle) -> bool:
    # 1. player moves a ray piece without capturing
    for node in puzzle.mainline[1::2]:
        moving_piece = moved_piece_type(node)
        if moving_piece not in ray_piece_types:
            continue
        prev_board = node.parent.board()
        if is_capture(node):
            continue
        from_sq = node.move.from_square
        to_sq = node.move.to_square
        for square in prev_board.attacks(from_sq):
            piece = prev_board.piece_at(square)
            if not piece or piece.color == puzzle.pov or piece.piece_type not in ray_piece_types:
                continue
            # 2. from, opponent piece, and destination are all on the same line
            if not squares_are_collinear(from_sq, square, to_sq):
                continue
            # 3. opponent piece can also move along this line type
            is_orthogonal = square_rank(from_sq) == square_rank(square) or square_file(from_sq) == square_file(square)
            if is_orthogonal and piece.piece_type == BISHOP:
                continue
            if not is_orthogonal and piece.piece_type == ROOK:
                continue
            # 4. capture was legal but player chose to stay on the line
            if chess.Move(from_sq, square) in prev_board.legal_moves:
                return True
    return False


def capturing_defender(puzzle: _Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        board = node.board()
        capture = node.parent.board().piece_at(node.move.to_square)
        assert isinstance(node.parent, ChildNode)
        if board.is_checkmate() or (
            capture
            and moved_piece_type(node) != KING
            and values[capture.piece_type] <= values[moved_piece_type(node)]
            and is_hanging(node.parent.board(), capture, node.move.to_square)
            and node.parent.move.to_square != node.move.to_square
        ):
            prev = node.parent.parent
            assert isinstance(prev, ChildNode)
            if not prev.board().is_check() and prev.move.to_square != node.move.from_square:
                assert prev.parent
                init_board = prev.parent.board()
                defender_square = prev.move.to_square
                defender = init_board.piece_at(defender_square)
                if (
                    defender
                    and defender_square in init_board.attackers(defender.color, node.move.to_square)
                    and not init_board.is_check()
                ):
                    return True
    return False


# ---------------------------------------------------------------------------
# cook.py (mats nommés)
# ---------------------------------------------------------------------------


def back_rank_mate(puzzle: _Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    back_rank = 7 if puzzle.pov else 0
    if board.is_checkmate() and square_rank(king) == back_rank:
        squares = SquareSet.from_square(king + (-8 if puzzle.pov else 8))
        if puzzle.pov:
            if chess.square_file(king) < 7:
                squares.add(king - 7)
            if chess.square_file(king) > 0:
                squares.add(king - 9)
        else:
            if chess.square_file(king) < 7:
                squares.add(king + 9)
            if chess.square_file(king) > 0:
                squares.add(king + 7)
        for square in squares:
            piece = board.piece_at(square)
            if piece is None or piece.color == puzzle.pov or board.attackers(puzzle.pov, square):
                return False
        return any(square_rank(checker) == back_rank for checker in board.checkers())
    return False


def anastasia_mate(puzzle: _Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if square_file(king) in [0, 7] and square_rank(king) not in [0, 7]:
        if square_file(node.move.to_square) == square_file(king) and moved_piece_type(node) in [QUEEN, ROOK]:
            if square_file(king) != 0:
                board.apply_transform(chess.flip_horizontal)
            king = board.king(not puzzle.pov)
            assert king is not None
            blocker = board.piece_at(king + 1)
            if blocker is not None and blocker.color != puzzle.pov:
                knight = board.piece_at(king + 3)
                if knight is not None and knight.color == puzzle.pov and knight.piece_type == KNIGHT:
                    return True
    return False


def hook_mate(puzzle: _Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if moved_piece_type(node) == ROOK and square_distance(node.move.to_square, king) == 1:
        for rook_defender_square in board.attackers(puzzle.pov, node.move.to_square):
            defender = board.piece_at(rook_defender_square)
            if defender and defender.piece_type == KNIGHT and square_distance(rook_defender_square, king) == 1:
                for knight_defender_square in board.attackers(puzzle.pov, rook_defender_square):
                    pawn = board.piece_at(knight_defender_square)
                    if pawn and pawn.piece_type == PAWN:
                        return True
    return False


def arabian_mate(puzzle: _Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if (
        square_file(king) in [0, 7]
        and square_rank(king) in [0, 7]
        and moved_piece_type(node) == ROOK
        and square_distance(node.move.to_square, king) == 1
    ):
        for knight_square in board.attackers(puzzle.pov, node.move.to_square):
            knight = board.piece_at(knight_square)
            if (
                knight
                and knight.piece_type == KNIGHT
                and (
                    abs(square_rank(knight_square) - square_rank(king)) == 2
                    and abs(square_file(knight_square) - square_file(king)) == 2
                )
            ):
                return True
    return False


def boden_or_double_bishop_mate(puzzle: _Puzzle) -> Optional[str]:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    bishop_squares = list(board.pieces(BISHOP, puzzle.pov))
    if len(bishop_squares) < 2:
        return None
    for square in [s for s in SquareSet(chess.BB_ALL) if square_distance(s, king) < 2]:
        if not all([p.piece_type == BISHOP for p in attacker_pieces(board, puzzle.pov, square)]):
            return None
    if (square_file(bishop_squares[0]) < square_file(king)) == (square_file(bishop_squares[1]) > square_file(king)):
        return "bodenMate"
    else:
        return "doubleBishopMate"


def dovetail_mate(puzzle: _Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if square_file(king) in [0, 7] or square_rank(king) in [0, 7]:
        return False
    queen_square = node.move.to_square
    if (
        moved_piece_type(node) != QUEEN
        or square_file(queen_square) == square_file(king)
        or square_rank(queen_square) == square_rank(king)
        or square_distance(queen_square, king) > 1
    ):
        return False
    for square in [s for s in SquareSet(chess.BB_ALL) if square_distance(s, king) == 1]:
        if square == queen_square:
            continue
        attackers = list(board.attackers(puzzle.pov, square))
        if attackers == [queen_square]:
            if board.piece_at(square):
                return False
        elif attackers:
            return False
    return True


def smothered_mate(puzzle: _Puzzle) -> bool:
    board = puzzle.game.end().board()
    king_square = board.king(not puzzle.pov)
    assert king_square is not None
    for checker_square in board.checkers():
        piece = board.piece_at(checker_square)
        assert piece
        if piece.piece_type == KNIGHT:
            for escape_square in [s for s in chess.SQUARES if square_distance(s, king_square) == 1]:
                blocker = board.piece_at(escape_square)
                if not blocker or blocker.color == puzzle.pov:
                    return False
            return True
    return False


# ---------------------------------------------------------------------------
# Mats nommés ajoutés (ARIA) — sur la position de mat finale, mêmes
# conventions que les détecteurs de cook.py (camp mat = `not puzzle.pov`).
# « Zone du roi » = case du roi + cases voisines. Les détecteurs exigent que
# seules les pièces du motif (de Nico) contrôlent cette zone, pour ne pas
# nommer un mat où d'autres pièces participent.
# ---------------------------------------------------------------------------


def _final(puzzle: _Puzzle) -> Tuple[Board, Square, ChildNode]:
    # Position de mat finale, case du roi mat, dernier nœud (coup matant).
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    return board, king, node


def _neighbors(king: Square) -> List[Square]:
    return [s for s in chess.SQUARES if square_distance(s, king) == 1]


def _zone_attacker_types(board: Board, pov: Color, king: Square) -> set:
    # Types des pièces de Nico qui attaquent la zone du roi.
    types = set()
    for square in [king, *_neighbors(king)]:
        for attacker in board.attackers(pov, square):
            types.add(board.piece_type_at(attacker))
    return types


def _checker_type(board: Board) -> Optional[chess.PieceType]:
    # Type de la pièce qui donne échec (un seul échec ; sinon None).
    checkers = list(board.checkers())
    return board.piece_type_at(checkers[0]) if len(checkers) == 1 else None


def _attacks_a_neighbor(board: Board, pov: Color, king: Square, piece_type: chess.PieceType) -> bool:
    # Une pièce de Nico de ce type contrôle au moins une case de fuite du roi.
    return any(
        board.piece_type_at(a) == piece_type for s in _neighbors(king) for a in board.attackers(pov, s)
    )


def balestra_mate(puzzle: _Puzzle) -> Optional[str]:
    # Arbalète : un fou donne le mat, la dame (non adjacente au roi) bloque les cases de fuite restantes.
    board, king, _ = _final(puzzle)
    if _checker_type(board) != BISHOP or _zone_attacker_types(board, puzzle.pov, king) != {BISHOP, QUEEN}:
        return None
    queens = board.pieces(QUEEN, puzzle.pov)
    if queens and all(square_distance(q, king) > 1 for q in queens):
        return "balestraMate"
    return None


def corner_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mat du coin : roi dans un coin, un cavalier donne le mat, une tour ou une dame ferme la fuite.
    board, king, _ = _final(puzzle)
    if square_file(king) not in [0, 7] or square_rank(king) not in [0, 7] or _checker_type(board) != KNIGHT:
        return None
    types = _zone_attacker_types(board, puzzle.pov, king)
    if types <= {KNIGHT, ROOK, QUEEN} and types & {ROOK, QUEEN}:
        return "cornerMate"
    return None


def morphys_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mat de Morphy : un fou donne le mat, une tour enferme le roi.
    board, king, _ = _final(puzzle)
    if _checker_type(board) == BISHOP and _zone_attacker_types(board, puzzle.pov, king) == {BISHOP, ROOK}:
        return "morphysMate"
    return None


def opera_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mat de l'opéra : une tour adjacente au roi donne le mat, défendue par un fou.
    board, king, node = _final(puzzle)
    rook = node.move.to_square
    if moved_piece_type(node) != ROOK or square_distance(rook, king) != 1 or rook not in board.checkers():
        return None
    if _zone_attacker_types(board, puzzle.pov, king) <= {ROOK, BISHOP} and any(
        board.piece_type_at(a) == BISHOP for a in board.attackers(puzzle.pov, rook)
    ):
        return "operaMate"
    return None


def pillsburys_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mat de Pillsbury : une tour donne le mat à distance, un fou enferme le roi.
    board, king, _ = _final(puzzle)
    if _checker_type(board) == ROOK and _zone_attacker_types(board, puzzle.pov, king) == {ROOK, BISHOP}:
        return "pillsburysMate"
    return None


def kill_box_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mise en boîte : une tour adjacente au roi donne le mat, défendue par la dame qui couvre le reste du carré 3×3.
    board, king, node = _final(puzzle)
    rook = node.move.to_square
    if moved_piece_type(node) != ROOK or square_distance(rook, king) != 1 or rook not in board.checkers():
        return None
    if _zone_attacker_types(board, puzzle.pov, king) <= {ROOK, QUEEN} and any(
        board.piece_type_at(a) == QUEEN for a in board.attackers(puzzle.pov, rook)
    ):
        return "killBoxMate"
    return None


def vukovic_mate(puzzle: _Puzzle) -> Optional[str]:
    # Mat de Vukovic : une tour adjacente au roi donne le mat, défendue par une pièce autre que le cavalier, qui ferme une fuite.
    board, king, node = _final(puzzle)
    rook = node.move.to_square
    if moved_piece_type(node) != ROOK or square_distance(rook, king) != 1 or rook not in board.checkers():
        return None
    if not _attacks_a_neighbor(board, puzzle.pov, king, KNIGHT):
        return None
    defenders = [board.piece_type_at(a) for a in board.attackers(puzzle.pov, rook)]
    if any(t != KNIGHT for t in defenders):
        return "vukovicMate"
    return None


def two_rooks_mate(puzzle: _Puzzle) -> Optional[str]:
    # Deux tours : seules deux tours contrôlent la zone ; « blindSwineMate » si elles sont sur la 7e rangée de Nico, sinon « twoRooksMate » (échelle).
    board, king, _ = _final(puzzle)
    rooks = board.pieces(ROOK, puzzle.pov)
    if _checker_type(board) != ROOK or len(rooks) < 2 or _zone_attacker_types(board, puzzle.pov, king) != {ROOK}:
        return None
    seventh = 6 if puzzle.pov == chess.WHITE else 1
    if sum(1 for r in rooks if square_rank(r) == seventh) >= 2:
        return "blindSwineMate"
    return "twoRooksMate"


def epaulette_mate(puzzle: _Puzzle) -> Optional[str]:
    # Épaulettes : la dame mate de face (même colonne ou rangée, à 2 cases), les deux cases latérales du roi sont occupées par ses propres pièces.
    board, king, _ = _final(puzzle)
    checkers = list(board.checkers())
    if _checker_type(board) != QUEEN:
        return None
    queen = checkers[0]
    if square_distance(queen, king) != 2:
        return None
    if square_file(queen) == square_file(king):
        sides = [king - 1, king + 1] if 0 < square_file(king) < 7 else []
    elif square_rank(queen) == square_rank(king):
        sides = [king - 8, king + 8] if 0 < square_rank(king) < 7 else []
    else:
        return None
    if sides and all(
        board.piece_at(s) is not None and board.piece_at(s).color != puzzle.pov for s in sides
    ):
        return "epauletteMate"
    return None


def swallowstail_mate(puzzle: _Puzzle) -> Optional[str]:
    # Guéridon : la dame, défendue, mate collée de face au roi ; les deux cases en diagonale derrière le roi sont occupées par ses propres pièces.
    board, king, _ = _final(puzzle)
    if _checker_type(board) != QUEEN:
        return None
    queen = list(board.checkers())[0]
    if square_distance(queen, king) != 1 or not board.attackers(puzzle.pov, queen):
        return None
    df = square_file(king) - square_file(queen)
    dr = square_rank(king) - square_rank(queen)
    if df and dr:
        return None
    # Direction « derrière le roi » (opposée à la dame) et les deux diagonales arrière.
    if df == 0:
        behind = [(square_file(king) - 1, square_rank(king) + dr), (square_file(king) + 1, square_rank(king) + dr)]
    else:
        behind = [(square_file(king) + df, square_rank(king) - 1), (square_file(king) + df, square_rank(king) + 1)]
    if not all(0 <= f < 8 and 0 <= r < 8 for f, r in behind):
        return None
    squares = [chess.square(f, r) for f, r in behind]
    if all(board.piece_at(s) is not None and board.piece_at(s).color != puzzle.pov for s in squares):
        return "swallowstailMate"
    return None


def triangle_mate(puzzle: _Puzzle) -> Optional[str]:
    # Triangle : dame et tour adjacentes au roi, sur une même rangée ou colonne à deux cases l'une de l'autre, formant un triangle avec lui.
    board, king, _ = _final(puzzle)
    if _checker_type(board) not in [QUEEN, ROOK] or _zone_attacker_types(board, puzzle.pov, king) != {QUEEN, ROOK}:
        return None
    for q in board.pieces(QUEEN, puzzle.pov):
        for r in board.pieces(ROOK, puzzle.pov):
            if square_distance(q, king) != 1 or square_distance(r, king) != 1:
                continue
            same_rank = square_rank(q) == square_rank(r) and abs(square_file(q) - square_file(r)) == 2
            same_file = square_file(q) == square_file(r) and abs(square_rank(q) - square_rank(r)) == 2
            if same_rank or same_file:
                return "triangleMate"
    return None


# Ordre de priorité des mats ajoutés (après ceux de cook.py) : les plus
# contraints d'abord, pour qu'un mat ne soit pas capté par un motif plus large.
_EXTRA_MATES = [
    balestra_mate,
    corner_mate,
    morphys_mate,
    opera_mate,
    pillsburys_mate,
    kill_box_mate,
    vukovic_mate,
    triangle_mate,
    two_rooks_mate,
    swallowstail_mate,
    epaulette_mate,
]
