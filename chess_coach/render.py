# aria/chess_coach/render.py
#
# Rendu d'une position en PNG avec Pillow seul (pas de cairosvg : libcairo2
# absent). Glyphes Unicode U+265A-265F de DejaVu Sans, pleins pour les deux
# camps : remplis de blanc + contour noir pour les blancs, noirs pour les noirs.
# Flèche verte : le meilleur coup ; flèche orange optionnelle : le coup
# explosif d'une position de sorte d (sprint 27) ; flèche bleue optionnelle :
# le coup joué (sprint 46). Variante du meilleur coup optionnelle : flèches
# numérotées 1, 2, 3 (sprint 49).

import math

import chess
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

SQUARE = 56
MARGIN = 16
SIZE = 8 * SQUARE + 2 * MARGIN  # 480 px

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
BORDER = (60, 60, 60)
COORD = (230, 230, 230)
ARROW = (21, 120, 27, 190)
ALT_ARROW = (230, 120, 20, 190)
PLAYED_ARROW = (30, 90, 220, 190)
ARROW_HEAD = SQUARE * 0.45
BADGE_RADIUS = 10

# Glyphe plein par type de pièce (même forme pour les deux couleurs).
_GLYPHS = {
    chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
    chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟",
}


def _square_origin(square: int, flipped: bool) -> tuple[int, int]:
    """Coin haut-gauche de la case en pixels, selon l'orientation."""
    file, rank = chess.square_file(square), chess.square_rank(square)
    col = 7 - file if flipped else file
    row = rank if flipped else 7 - rank
    return MARGIN + col * SQUARE, MARGIN + row * SQUARE


def _square_center(square: int, flipped: bool) -> tuple[float, float]:
    x, y = _square_origin(square, flipped)
    return x + SQUARE / 2, y + SQUARE / 2


def _draw_arrow(overlay: Image.Image, move: chess.Move, flipped: bool, color=ARROW) -> None:
    """Flèche (trait + pointe triangulaire) du centre de la case de départ à l'arrivée."""
    draw = ImageDraw.Draw(overlay)
    x1, y1 = _square_center(move.from_square, flipped)
    x2, y2 = _square_center(move.to_square, flipped)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = ARROW_HEAD
    # Le trait s'arrête à la base de la pointe pour ne pas la déborder.
    bx, by = x2 - head * math.cos(angle), y2 - head * math.sin(angle)
    draw.line([(x1, y1), (bx, by)], fill=color, width=int(SQUARE * 0.16))
    spread = head * 0.6
    left = (bx + spread * math.sin(angle), by - spread * math.cos(angle))
    right = (bx - spread * math.sin(angle), by + spread * math.cos(angle))
    draw.polygon([(x2, y2), left, right], fill=color)


def _draw_badge(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, number: int,
                move: chess.Move, flipped: bool, color) -> None:
    """Pastille numérotée à la base de la pointe : sur la flèche, près de l'arrivée.

    Placée sur la flèche et non sur la case : une prise et sa reprise visent la
    même case, leurs pastilles ne se recouvrent pas.
    """
    x1, y1 = _square_center(move.from_square, flipped)
    x2, y2 = _square_center(move.to_square, flipped)
    angle = math.atan2(y2 - y1, x2 - x1)
    cx, cy = x2 - ARROW_HEAD * math.cos(angle), y2 - ARROW_HEAD * math.sin(angle)
    r = BADGE_RADIUS
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color[:3], outline=(255, 255, 255), width=2)
    draw.text((cx, cy), str(number), font=font, fill=(255, 255, 255), anchor="mm")


def render_position(fen: str, orientation: str, best_uci: str, out_path: str,
                    alt_uci: str | None = None, played_uci: str | None = None,
                    best_line_uci: list | None = None) -> str:
    """Dessine la position `fen` en PNG (480 px) et retourne `out_path`.

    orientation == "black" retourne l'échiquier ; best_uci est tracé en flèche
    verte, alt_uci (coup explosif, facultatif) en flèche orange, played_uci (coup
    joué, facultatif) en flèche bleue. Coup joué = meilleur coup : seule la bleue reste.
    best_line_uci (variante du meilleur coup, facultative, best_uci en tête) : ses
    coups suivants en flèches vertes, tous numérotés à partir de 1.
    """
    board = chess.Board(fen)
    flipped = orientation == "black"
    image = Image.new("RGBA", (SIZE, SIZE), BORDER)
    draw = ImageDraw.Draw(image)
    piece_font = ImageFont.truetype(FONT_PATH, int(SQUARE * 0.82))
    coord_font = ImageFont.truetype(FONT_PATH, 11)

    for square in chess.SQUARES:
        x, y = _square_origin(square, flipped)
        light = (chess.square_file(square) + chess.square_rank(square)) % 2 == 1
        draw.rectangle([x, y, x + SQUARE - 1, y + SQUARE - 1], fill=LIGHT if light else DARK)

    # Coordonnées : colonnes en bas, rangées à gauche, dans la marge.
    for i in range(8):
        file_label = "abcdefgh"[7 - i if flipped else i]
        rank_label = str(i + 1 if flipped else 8 - i)
        draw.text((MARGIN + i * SQUARE + SQUARE / 2, SIZE - MARGIN / 2), file_label,
                  font=coord_font, fill=COORD, anchor="mm")
        draw.text((MARGIN / 2, MARGIN + i * SQUARE + SQUARE / 2), rank_label,
                  font=coord_font, fill=COORD, anchor="mm")

    # Flèche sous les pièces, en surimpression semi-transparente.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    if played_uci != best_uci:
        _draw_arrow(overlay, chess.Move.from_uci(best_uci), flipped)
    line = [chess.Move.from_uci(uci) for uci in best_line_uci or []]
    for move in line[1:]:
        _draw_arrow(overlay, move, flipped)
    if alt_uci:
        _draw_arrow(overlay, chess.Move.from_uci(alt_uci), flipped, ALT_ARROW)
    if played_uci:
        _draw_arrow(overlay, chess.Move.from_uci(played_uci), flipped, PLAYED_ARROW)
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    for square, piece in board.piece_map().items():
        cx, cy = _square_center(square, flipped)
        if piece.color == chess.WHITE:
            draw.text((cx, cy), _GLYPHS[piece.piece_type], font=piece_font, anchor="mm",
                      fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        else:
            draw.text((cx, cy), _GLYPHS[piece.piece_type], font=piece_font, anchor="mm",
                      fill=(0, 0, 0), stroke_width=1, stroke_fill=(90, 90, 90))

    # Pastilles au-dessus des pièces ; le n° 1 prend la couleur de sa flèche.
    badge_font = ImageFont.truetype(FONT_PATH, 13)
    for number, move in enumerate(line, 1):
        color = PLAYED_ARROW if number == 1 and played_uci == best_uci else ARROW
        _draw_badge(draw, badge_font, number, move, flipped, color)

    image.convert("RGB").save(out_path, "PNG")
    return out_path
