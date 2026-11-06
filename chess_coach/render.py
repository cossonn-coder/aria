# aria/chess_coach/render.py
#
# Rendu d'une position en PNG avec Pillow seul (pas de cairosvg : libcairo2
# absent). Glyphes Unicode U+265A-265F de DejaVu Sans, pleins pour les deux
# camps : remplis de blanc + contour noir pour les blancs, noirs pour les noirs.
# Flèche verte : le meilleur coup ; flèche orange optionnelle : le coup
# explosif d'une position de sorte d (sprint 27) ; flèche bleue optionnelle :
# le coup joué (sprint 46), à la couleur de sa gravité si c'est une erreur, flèche
# cyan pour un coup explosif piégeant (sprint 50). Variante du meilleur coup optionnelle : flèches
# numérotées 1, 2, 3 (sprint 49). Courbe du % de gain d'une partie (après le sprint 49).

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
TRAP_ARROW = (0, 229, 255, 190)
# Échelle fixe de gravité d'une erreur jouée : (perte en pts, couleur).
ERROR_SCALE = ((10, (255, 190, 205)), (25, (215, 20, 35)), (50, (0, 0, 0)))
ERROR_OPACITY = 235
ARROW_HEAD = SQUARE * 0.45
BADGE_RADIUS = 10

CURVE_SIZE = (640, 320)
CURVE_MARGIN = 50
CURVE_BG = (0, 0, 0)
CURVE_GRID = (70, 70, 70)
CURVE_TEXT = (190, 190, 190)
CURVE_LINE = (110, 110, 110)
CURVE_DOT = 3
# Anneau clair : un point noir (erreur de 50 pts et plus) reste visible sur le fond noir.
CURVE_DOT_RING = (200, 200, 200)
# Sprint 51 : point d'un coup meilleur en bleu (teinte de la flèche du coup joué), coup correct en blanc.
CURVE_BEST = PLAYED_ARROW[:3]
CURVE_CORRECT = (255, 255, 255)
CURVE_NEUTRAL = (150, 150, 150)

# Glyphe plein par type de pièce (même forme pour les deux couleurs).
_GLYPHS = {
    chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
    chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟",
}


def error_arrow(loss: float) -> tuple:
    """Couleur RGBA de la flèche d'une erreur : interpolation linéaire sur ERROR_SCALE,
    bornée à ses extrémités (sous 10 pts, la couleur de 10 ; dès 50 pts, le noir)."""
    (low, low_rgb), (mid, mid_rgb), (high, high_rgb) = ERROR_SCALE
    if loss < mid:
        start, end, a, b = low, mid, low_rgb, mid_rgb
    else:
        start, end, a, b = mid, high, mid_rgb, high_rgb
    t = min(max((loss - start) / (end - start), 0.0), 1.0)
    return (*(round(x + t * (y - x)) for x, y in zip(a, b)), ERROR_OPACITY)


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
                    best_line_uci: list | None = None, played_color: tuple = PLAYED_ARROW,
                    alt_color: tuple = ALT_ARROW) -> str:
    """Dessine la position `fen` en PNG (480 px) et retourne `out_path`.

    orientation == "black" retourne l'échiquier ; best_uci est tracé en flèche
    verte, alt_uci (coup explosif, facultatif) en flèche orange, played_uci (coup
    joué, facultatif) en flèche bleue. Coup joué = meilleur coup : seule la bleue reste.
    played_color et alt_color remplacent le bleu et l'orange (gravité d'une erreur, piège).
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
        _draw_arrow(overlay, chess.Move.from_uci(alt_uci), flipped, alt_color)
    if played_uci:
        _draw_arrow(overlay, chess.Move.from_uci(played_uci), flipped, played_color)
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
        color = played_color if number == 1 and played_uci == best_uci else ARROW
        _draw_badge(draw, badge_font, number, move, flipped, color)

    image.convert("RGB").save(out_path, "PNG")
    return out_path


def render_curve(wins: list, move_numbers: list, colors: list, out_path: str) -> str:
    """Dessine la courbe du % de gain en PNG (640 × 320 px) et retourne `out_path`.

    wins : N+1 valeurs de 0 à 100, une par position ; move_numbers : numéro de coup
    des N coups joués, pour graduer l'axe tous les 10 coups ; colors : N+1 couleurs RGB,
    une par point.
    """
    width, height = CURVE_SIZE
    image = Image.new("RGB", CURVE_SIZE, CURVE_BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 12)
    left, right, top, bottom = CURVE_MARGIN, width - CURVE_MARGIN / 2, CURVE_MARGIN / 2, height - CURVE_MARGIN

    def x_at(index: int) -> float:
        return left + index * (right - left) / (len(wins) - 1)

    def y_at(win: float) -> float:
        return bottom - win * (bottom - top) / 100

    for win in (0, 50, 100):
        draw.line([(left, y_at(win)), (right, y_at(win))], fill=CURVE_GRID, width=2 if win == 50 else 1)
        draw.text((left - 6, y_at(win)), f"{win} %", font=font, fill=CURVE_TEXT, anchor="rm")

    # Graduation au premier demi-coup de chaque dizaine de coups.
    for i, number in enumerate(move_numbers):
        if number % 10 == 0 and (i == 0 or move_numbers[i - 1] != number):
            draw.line([(x_at(i), top), (x_at(i), bottom)], fill=CURVE_GRID)
            draw.text((x_at(i), bottom + 12), str(number), font=font, fill=CURVE_TEXT, anchor="mm")

    points = [(x_at(i), y_at(win)) for i, win in enumerate(wins)]
    # Segments droits et un point par position : on lit chaque coup, sans effet lissé.
    draw.line(points, fill=CURVE_LINE, width=2)
    for (x, y), color in zip(points, colors):
        draw.ellipse([x - CURVE_DOT, y - CURVE_DOT, x + CURVE_DOT, y + CURVE_DOT],
                     fill=color, outline=CURVE_DOT_RING)

    image.save(out_path, "PNG")
    return out_path
