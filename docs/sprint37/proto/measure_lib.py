import sys
sys.path.insert(0, "/home/nico/Nextcloud/projects/aria")
import torch
from config import config
from chess_coach.difficulty import _load
from maia2 import inference

def maia_values(fens, ELO=1300):
    """Pronostic Maia-2 du trait (0..1) pour chaque fen."""
    net, all_moves_dict, elo_dict = _load(config.maia_models_dir)
    boards, elos = [], []
    for fen in fens:
        b, e, _, _ = inference.preprocessing(fen, ELO, ELO, elo_dict, all_moves_dict)
        boards.append(b); elos.append(e)
    with torch.no_grad():
        t = torch.tensor(elos)
        _, _, v = net(torch.stack(boards), t, t)
    return ((v / 2 + 0.5).clamp(0, 1)).tolist()

