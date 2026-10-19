# aria/chess_coach/difficulty.py
#
# Difficulté des coups de Nico par Maia-2 (sprint 28, tronçon 01).
#
# P = probabilité, selon Maia-2 (modèle rapid, elo_self = elo_oppo = R), que
# Nico joue le meilleur coup Stockfish dans la position. La difficulté est
# l'Elo auquel ce coup serait trouvé une fois sur deux :
#     difficulté = R − 400 · log10(P / (1 − P))
# Calculée seulement pour les coups de Nico après le coup 10 (Maia n'est pas
# fiable en ouverture). Une seule passe batchée par partie.
# Module pur : aucun import mémoire / LLM / exécution.

import math
import time

from logger import get_logger

log = get_logger(__name__)

# Elo de Nico à défaut d'en-tête PGN.
DEFAULT_ELO = 1300
# Maia jugé non fiable jusqu'à ce coup inclus.
_OPENING_MOVES = 10
_P_MIN, _P_MAX = 0.01, 0.99

# Modèle chargé une fois par process, à la première analyse (la VM a 4 Go).
_model = None


def _load(models_dir: str):
    """Charge paresseusement le modèle Maia-2 rapid et ses dictionnaires."""
    global _model
    if _model is None:
        from maia2 import inference, model
        net = model.from_pretrained(type="rapid", device="cpu", save_root=models_dir)
        all_moves_dict, elo_dict, _ = inference.prepare()
        _model = (net, all_moves_dict, elo_dict)
    return _model


def _probabilities(positions: list, elo: int, models_dir: str) -> list:
    """P(meilleur coup) pour chaque (fen, best_uci), en une passe batchée."""
    import chess
    import torch
    from maia2 import inference

    net, all_moves_dict, elo_dict = _load(models_dir)
    boards, elos, legals, best_idx = [], [], [], []
    for fen, best_uci in positions:
        board_in, elo_cat, _, legal = inference.preprocessing(fen, elo, elo, elo_dict, all_moves_dict)
        # Maia voit le plateau retourné quand c'est aux noirs de jouer.
        if chess.Board(fen).turn == chess.BLACK:
            best_uci = inference.mirror_move(best_uci)
        boards.append(board_in)
        elos.append(elo_cat)
        legals.append(legal)
        best_idx.append(all_moves_dict[best_uci])
    with torch.no_grad():
        elo_tensor = torch.tensor(elos)
        logits, _, _ = net(torch.stack(boards), elo_tensor, elo_tensor)
        probs = inference._masked_softmax(logits, torch.stack(legals))
    return [probs[i, idx].item() for i, idx in enumerate(best_idx)]


def difficulty_from_p(p: float, elo: int) -> int:
    """Formule Elo : P = 0,5 → difficulté = elo ; P bornée à [0,01 ; 0,99]."""
    p = min(_P_MAX, max(_P_MIN, p))
    return round(elo - 400 * math.log10(p / (1 - p)))


def assign_difficulty(plies: list, nico_color: str, nico_elo: int | None, models_dir: str) -> None:
    """Remplit p.difficulty des coups de Nico après le coup 10 (les autres restent None)."""
    started = time.monotonic()
    elo = nico_elo or DEFAULT_ELO
    targets = [p for p in plies if p.color == nico_color and p.move_number > _OPENING_MOVES]
    if not targets:
        return
    probs = _probabilities([(p.fen_before, p.best_uci) for p in targets], elo, models_dir)
    for p, prob in zip(targets, probs):
        p.difficulty = difficulty_from_p(prob, elo)
    log.info("maia_difficulty OK n=%d duration=%.1fs", len(targets), time.monotonic() - started)
