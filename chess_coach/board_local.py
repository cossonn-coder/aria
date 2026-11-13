# aria/chess_coach/board_local.py
#
# Lecteur local d'échiquier, secours de Gemini (sprint 59, tronçon 02).
#
# Périmètre : captures d'écran d'échiquier numérique, plateau seul ou au milieu
# d'une capture plein écran. Deux étapes, sans réseau ni OpenCV :
#   1. repérage du plateau : les 7 lignes intérieures de la grille 8×8 sont des
#      bords nets, également espacés, aussi longs que le plateau ; on les cherche
#      dans les profils de bords par colonne et par rangée, puis on vérifie que
#      les cases alternent bien clair/foncé ;
#   2. reconnaissance : chaque case, ramenée en 32×32, est classée par plus
#      proche voisin parmi les cases des captures de référence (data/board_refs/).
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


def _square_edges(first: float, spacing: float, size: int) -> np.ndarray:
    """9 bornes des cases (en pixels) à partir des lignes intérieures, bornées à l'image."""
    # Les lignes détectées sont le dernier pixel avant le bord : la case suivante commence à +1.
    edges = first + 1 + spacing * np.arange(-1, 8)
    return np.clip(np.rint(edges), 0, size).astype(int)


def _locate(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Bornes (xs, ys) des 8×8 cases du plateau, ou None si aucun plateau."""
    cols, rows = _line_profiles(rgb)
    x0, sx, x_score = _find_lines(cols)
    y0, sy, y_score = _find_lines(rows)
    # Chaque ligne intérieure doit couvrir au moins la moitié du plateau (les
    # pièces peuvent en masquer une partie), et les cases doivent être carrées.
    if x_score < 4 * sy or y_score < 4 * sx or abs(sx - sy) > 2:
        return None
    xs = _square_edges(x0, sx, rgb.shape[1])
    ys = _square_edges(y0, sy, rgb.shape[0])
    if not _alternates(rgb, xs, ys):
        return None
    return xs, ys


def _alternates(rgb: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> bool:
    """Vrai si les coins des cases (hors pièce) alternent deux couleurs nettement distinctes."""
    corners = np.array([
        rgb[ys[r] + (ys[r + 1] - ys[r]) // 8, xs[c] + (xs[c + 1] - xs[c]) // 8]
        for r in range(8) for c in range(8)
    ], dtype=float)
    parity = np.array([(r + c) % 2 for r in range(8) for c in range(8)])
    even, odd = corners[parity == 0], corners[parity == 1]
    contrast = np.abs(even.mean(axis=0) - odd.mean(axis=0)).sum()
    spread = max(np.abs(even - even.mean(axis=0)).sum(axis=1).max(),
                 np.abs(odd - odd.mean(axis=0)).sum(axis=1).max())
    return contrast > _EDGE_THRESHOLD and spread < contrast / 2


def _cells(rgb: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """64 cases en vecteurs (32×32×3), rangée du haut d'abord, de gauche à droite."""
    image = Image.fromarray(rgb.astype(np.uint8))
    return np.array([
        np.asarray(
            image.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])).resize((_CELL, _CELL)),
            dtype=float,
        ).ravel()
        for r in range(8) for c in range(8)
    ])


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
