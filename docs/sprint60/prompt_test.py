import sys, time
from pathlib import Path
ROOT = Path("/home/nico/Nextcloud/projects/aria"); sys.path.insert(0, str(ROOT))
import chess
from llm.image_router import ImageRouter, _parse_grid
from chess_coach.board_reading import grid_to_fen

PROMPT = (
    "Cette image est une photo d'un échiquier physique, prise en perspective. "
    "Une pièce occupe la case sur laquelle repose sa BASE, pas les cases que sa tête recouvre. "
    "Les pièces posées HORS du plateau (pièces prises, à côté de l'échiquier) ne font pas partie de la position : "
    "ne les mets pas dans la grille. "
    "Lis les 8 rangées du plateau TELLES QU'AFFICHÉES, de la rangée du haut à celle du bas, "
    "chaque rangée de gauche à droite. Pour chaque case : lettre de pièce (K Q R B N P pour les blancs, "
    "k q r b n p pour les noirs) ou '.' si vide.\n"
    "Réponds par 8 lignes de 8 caractères, puis une 9e ligne qui commence par HORS: "
    "suivie des lettres des pièces posées hors du plateau (ou rien)."
)
TRUE = chess.Board("r1bqk2r/ppp2ppp/2p2n2/2b3B1/4P3/3P4/PPP2PPP/RN1QKB1R w - - 0 1")
r = ImageRouter()
for photo in sorted((ROOT / "docs/sprint60/corpus").glob("p1*.jpg")):
    t0 = time.time()
    try:
        text = r._dispatch(r.board_table[:1], "describe", image=str(photo), prompt=PROMPT)
    except RuntimeError as e:
        print(photo.stem, "ERREUR", e, flush=True); continue
    lines = text.splitlines()
    hors = next((l for l in lines if l.strip().upper().startswith("HORS")), "HORS: ?")
    rows = _parse_grid("\n".join(l for l in lines if not l.strip().upper().startswith("HORS")))
    if rows is None:
        print(f"{photo.stem:18s} {time.time()-t0:3.0f}s grille non conforme : {text!r}", flush=True); continue
    B = chess.Board(grid_to_fen(rows, None)[0])
    errs = [f"{chess.square_name(s)}:{(TRUE.piece_at(s) or '.')}→{(B.piece_at(s) or '.')}" for s in chess.SQUARES if B.piece_at(s) != TRUE.piece_at(s)]
    print(f"{photo.stem:18s} {time.time()-t0:3.0f}s {64-len(errs)}/64 {hors.strip()}  {' '.join(errs) if len(errs) < 12 else ''}", flush=True)
