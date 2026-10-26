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
        # Mode évaluation : sans lui le dropout reste actif et les probabilités
        # varient d'un appel à l'autre (maia2.inference_each fait de même).
        net.eval()
        all_moves_dict, elo_dict, _ = inference.prepare()
        _model = (net, all_moves_dict, elo_dict)
    return _model


def _probabilities(positions: list, elo: int, models_dir: str) -> list:
    """P(coup) pour chaque couple (fen, uci), en une passe batchée."""
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
    """Remplit p.difficulty et p.played_p des coups de Nico après le coup 10 (les autres restent None).

    played_p = P(coup joué) (sprint 29, tronçon 12), calculée dans la même passe batchée.
    """
    started = time.monotonic()
    elo = nico_elo or DEFAULT_ELO
    targets = [p for p in plies if p.color == nico_color and p.move_number > _OPENING_MOVES]
    if not targets:
        return
    # Une passe : n couples (fen, meilleur coup) puis n couples (fen, coup joué).
    probs = _probabilities([(p.fen_before, p.best_uci) for p in targets]
                           + [(p.fen_before, p.uci) for p in targets], elo, models_dir)
    for p, prob, played in zip(targets, probs, probs[len(targets):]):
        p.difficulty = difficulty_from_p(prob, elo)
        p.played_p = played
    log.info("maia_difficulty OK n=%d duration=%.1fs", len(targets), time.monotonic() - started)


# Réponses humaines gardées : jusqu'à 90 % de probabilité cumulée, 6 au plus.
_REPLY_MASS = 0.9
_MAX_REPLIES = 6


def reply_distribution(fens: list, elo: int, models_dir: str) -> list:
    """Réponses les plus probables selon Maia-2 dans chaque position, en une passe batchée.

    elo_self = elo_oppo = elo. Rend, par fen, [(uci, p), …] trié par p
    décroissante, tronqué à 90 % cumulés (le coup qui franchit le seuil
    compris), 6 au plus ; p brutes (non renormalisées, somme ≤ 1).
    """
    import chess
    import torch
    from maia2 import inference

    net, all_moves_dict, elo_dict = _load(models_dir)
    # Inverse indice → UCI (dans le repère de Maia : trait aux blancs).
    index_to_uci = {idx: uci for uci, idx in all_moves_dict.items()}
    boards, elos, legals = [], [], []
    for fen in fens:
        board_in, elo_cat, _, legal = inference.preprocessing(fen, elo, elo, elo_dict, all_moves_dict)
        boards.append(board_in)
        elos.append(elo_cat)
        legals.append(legal)
    with torch.no_grad():
        elo_tensor = torch.tensor(elos)
        logits, _, _ = net(torch.stack(boards), elo_tensor, elo_tensor)
        probs = inference._masked_softmax(logits, torch.stack(legals))
    result = []
    for i, fen in enumerate(fens):
        black = chess.Board(fen).turn == chess.BLACK
        values, indices = torch.sort(probs[i], descending=True)
        replies, mass = [], 0.0
        for p, idx in zip(values.tolist(), indices.tolist()):
            uci = index_to_uci[idx]
            # Démiroir : Maia voit le plateau retourné quand c'est aux noirs.
            replies.append((inference.mirror_move(uci) if black else uci, p))
            mass += p
            if mass >= _REPLY_MASS or len(replies) == _MAX_REPLIES:
                break
        result.append(replies)
    return result


def position_values(fens: list, elo: int, models_dir: str) -> list:
    """Pronostic Maia-2 (tête de valeur) du camp au trait de chaque fen, en % (0-100).

    Une passe batchée, elo_self = elo_oppo = elo (sprint 37, tronçon 01). La
    sortie brute est déjà du point de vue du trait : pas de retournement selon
    la couleur (maia2.inference ne retourne que pour l'exprimer côté blancs).
    """
    import torch
    from maia2 import inference

    net, all_moves_dict, elo_dict = _load(models_dir)
    boards, elos = [], []
    for fen in fens:
        board_in, elo_cat, _, _ = inference.preprocessing(fen, elo, elo, elo_dict, all_moves_dict)
        boards.append(board_in)
        elos.append(elo_cat)
    with torch.no_grad():
        elo_tensor = torch.tensor(elos)
        _, _, values = net(torch.stack(boards), elo_tensor, elo_tensor)
    # Valeur dans [-1 ; 1] → probabilité de résultat du trait, en %.
    return [100 * v for v in (values / 2 + 0.5).clamp(0, 1).tolist()]
