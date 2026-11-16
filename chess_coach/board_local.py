# aria/chess_coach/board_local.py
#
# Lecteur local d'échiquier, secours de Gemini (sprint 59, tronçon 02).
#
# Périmètre : captures d'écran d'échiquier numérique, plateau seul ou au milieu
# d'une capture plein écran. Deux étapes, sans réseau ni OpenCV :
#   1. repérage du plateau : les 7 lignes intérieures de la grille 8×8 sont des
#      bords nets, également espacés, aussi longs que le plateau ; on les cherche
#      dans les profils de bords par colonne et par rangée, puis on vérifie que
#      les cases alternent bien clair/foncé (quelques cases surlignées tolérées) ;
#   2. reconnaissance : chaque case, ramenée en 32×32, rognée et privée de son
#      fond, est classée par plus proche voisin parmi les cases des captures de
#      référence (data/board_refs/).
# Même sortie que ImageRouter.read_board : 8 chaînes de 8 caractères, telles
# qu'affichées. Module pur : aucun import mémoire, LLM ou réseau.

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from logger import get_logger

log = get_logger(__name__)

_REFS_DIR = Path(__file__).parent / "data" / "board_refs"
_CELL = 32            # côté d'une case normalisée, en pixels
_EDGE_THRESHOLD = 40  # écart RGB cumulé entre deux pixels voisins pour compter un bord
_MIN_SQUARE = 8       # plus petite case cherchée, en pixels
_MAX_ODD_SQUARES = 4  # cases tolérées hors alternance (dernier coup surligné : 2 cases)
_MARGIN = 3           # marge rognée autour d'une case normalisée (coordonnées dessinées)
_BACKGROUND_DIST = 90  # écart RGB cumulé sous lequel un pixel compte comme fond de case (mesuré)


def _line_profiles(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nombre de pixels de bord par colonne (bords verticaux) et par rangée (horizontaux)."""
    dx = np.abs(np.diff(rgb, axis=1)).sum(axis=2) > _EDGE_THRESHOLD
    dy = np.abs(np.diff(rgb, axis=0)).sum(axis=2) > _EDGE_THRESHOLD
    return dx.sum(axis=0), dy.sum(axis=1)


def _find_lines(profile: np.ndarray) -> tuple[float, float, float]:
    """
    Meilleure suite de 7 lignes également espacées dans un profil de bords.

    Le score d'une suite est la plus faible de ses 7 lignes (tolérance ±1 px) :
    il faut que TOUTES les lignes intérieures soient longues, ce qu'une bordure
    d'interface isolée ne fournit pas.

    Returns:
        (position de la 1re ligne, espacement, score).
    """
    n = len(profile)
    # Tolérance ±1 px : l'espacement réel n'est pas forcément entier.
    padded = np.pad(profile, 1)
    dilated = np.maximum(np.maximum(padded[:-2], padded[1:-1]), padded[2:])
    starts = np.arange(n)
    best = (0.0, 0.0, 0.0)
    for spacing in np.arange(_MIN_SQUARE, n / 7, 0.5):
        idx = np.rint(starts[:, None] + spacing * np.arange(7)).astype(int)
        valid = idx[:, -1] < n
        if not valid.any():
            continue
        scores = dilated[idx[valid]].min(axis=1)
        i = int(scores.argmax())
        if scores[i] > best[2]:
            best = (float(starts[valid][i]), float(spacing), float(scores[i]))
    first, spacing, score = best
    if score == 0:
        return best
    # Affinage : pic réel de chaque ligne près de sa position prévue, puis droite
    # ajustée sur les 7 pics (le pas de 0,5 px dériverait sur 8 cases agrandies).
    predicted = np.rint(first + spacing * np.arange(7)).astype(int)
    peaks = [p - 1 + int(padded[p:p + 3].argmax()) for p in predicted]
    spacing, first = np.polyfit(np.arange(7), peaks, 1)
    return float(first), float(spacing), score


def _square_edges(first: float, spacing: float, size: int) -> np.ndarray | None:
    """
    9 bornes des cases (en pixels) à partir des lignes intérieures, bornées à
    l'image ; None si le plateau déborde de l'image de plus d'un pixel.
    """
    # Les lignes détectées sont le dernier pixel avant le bord : la case suivante commence à +1.
    edges = np.rint(first + 1 + spacing * np.arange(-1, 8))
    if edges[0] < -1 or edges[-1] > size + 1:
        return None
    return np.clip(edges, 0, size).astype(int)


def _locate(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Bornes (xs, ys) des 8×8 cases du plateau, ou None si aucun plateau."""
    cols, rows = _line_profiles(rgb)
    x0, sx, x_score = _find_lines(cols)
    y0, sy, y_score = _find_lines(rows)
    # Chaque ligne intérieure doit couvrir au moins la moitié du plateau (les
    # pièces peuvent en masquer une partie), et les cases doivent être carrées.
    if x_score < 4 * sy or y_score < 4 * sx or abs(sx - sy) > 2:
        return None
    # Le bord extérieur du plateau, très contrasté sur un fond sombre, peut être
    # pris pour une ligne intérieure : la fenêtre trouvée est alors décalée d'une
    # case. On essaie aussi les fenêtres décalées d'une case et on garde celle
    # dont les cases alternent le mieux (une colonne hors plateau = 8 cases fausses).
    best = None
    for dx in (0, 1, -1):
        xs = _square_edges(x0 + dx * sx, sx, rgb.shape[1])
        if xs is None:
            continue
        for dy in (0, 1, -1):
            ys = _square_edges(y0 + dy * sy, sy, rgb.shape[0])
            if ys is None:
                continue
            odd = _odd_squares(rgb, xs, ys)
            if best is None or odd < best[0]:
                best = (odd, xs, ys)
    if best is None or best[0] > _MAX_ODD_SQUARES:
        return None
    return best[1], best[2]


def _corner_colors(rgb: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Couleur du coin haut-droit de chaque case, hors pièce et hors coordonnées dessinées."""
    # Coin haut-droit : chess.com dessine les chiffres en haut à gauche et les
    # lettres en bas à droite ; les pièces sont centrées.
    return np.array([
        rgb[ys[r] + (ys[r + 1] - ys[r]) // 8, xs[c + 1] - 1 - (xs[c + 1] - xs[c]) // 8]
        for r in range(8) for c in range(8)
    ], dtype=float)


def _odd_squares(rgb: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> int:
    """
    Nombre de cases qui ne suivent pas l'alternance clair/foncé (64 si pas de damier).

    Chaque case est comparée à la couleur médiane de sa parité : la médiane
    ignore les quelques cases surlignées, qu'on compte ici comme aberrantes.
    """
    corners = _corner_colors(rgb, xs, ys)
    parity = np.array([(r + c) % 2 for r in range(8) for c in range(8)])
    medians = np.array([np.median(corners[parity == k], axis=0) for k in (0, 1)])
    contrast = np.abs(medians[0] - medians[1]).sum()
    if contrast <= _EDGE_THRESHOLD:
        return 64
    gaps = np.abs(corners - medians[parity]).sum(axis=1)
    return int((gaps >= contrast / 2).sum())


def _cells(rgb: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """
    64 cases en vecteurs, rangée du haut d'abord, de gauche à droite.

    Chaque case est ramenée en 32×32, rognée d'une marge (coordonnées dessinées
    dans les coins), puis ses pixels proches du fond de la case sont mis à zéro :
    une case vide vaut alors zéro quelle que soit sa couleur (claire, foncée ou
    surlignée), et une pièce ne garde que ses propres pixels.
    """
    image = Image.fromarray(rgb.astype(np.uint8))
    backgrounds = _corner_colors(rgb, xs, ys)
    vectors = []
    for i, (r, c) in enumerate((r, c) for r in range(8) for c in range(8)):
        cell = np.asarray(
            image.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])).resize((_CELL, _CELL)),
            dtype=float,
        )[_MARGIN:-_MARGIN, _MARGIN:-_MARGIN]
        cell[np.abs(cell - backgrounds[i]).sum(axis=2) < _BACKGROUND_DIST] = 0
        vectors.append(cell.ravel())
    return np.array(vectors)


def _load_rgb(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(int)


@lru_cache(maxsize=1)
def _references() -> tuple[np.ndarray, np.ndarray]:
    """Cases de référence et leurs étiquettes, depuis chaque couple image + grille du dossier."""
    vectors, labels = [], []
    for grid_path in sorted(_REFS_DIR.glob("*.txt")):
        image_path = next(
            p for p in (grid_path.with_suffix(".jpg"), grid_path.with_suffix(".png")) if p.exists()
        )
        rgb = _load_rgb(image_path)
        xs, ys = _locate(rgb)
        vectors.append(_cells(rgb, xs, ys))
        labels.extend("".join(grid_path.read_text().split()))
    return np.vstack(vectors), np.array(labels)


def read_board(path) -> list[str] | None:
    """
    Lit localement la grille d'une capture d'écran d'échiquier.

    Args:
        path: chemin local de l'image.

    Returns:
        8 chaînes de 8 caractères (rangée du haut d'abord ; KQRBNP blancs,
        kqrbnp noirs, '.' vide), ou None si aucun plateau n'est repéré.
    """
    rgb = _load_rgb(path)
    found = _locate(rgb)
    if found is None:
        log.info("[BOARD_LOCAL] aucun plateau repéré.")
        return None
    ref_vectors, ref_labels = _references()
    cells = _cells(rgb, *found)
    # Distance euclidienne au carré de chaque case à chaque référence.
    distances = ((cells[:, None, :] - ref_vectors[None, :, :]) ** 2).sum(axis=2)
    letters = ref_labels[distances.argmin(axis=1)]
    return ["".join(letters[r * 8:(r + 1) * 8]) for r in range(8)]
