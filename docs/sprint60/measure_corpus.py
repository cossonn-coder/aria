"""
Mesure du corpus du sprint 60 : lit chaque photo de docs/sprint60/corpus/
avec la lecture prod (ImageRouter.read_board → grid_to_fen), compare à la FEN vraie
case par case. Usage : venv/bin/python docs/sprint60/measure_corpus.py [filtre]
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import chess  # noqa: E402
from llm.image_router import ImageRouter  # noqa: E402
from chess_coach.board_reading import grid_to_fen  # noqa: E402

TRUTH = {
    "p1": "r1bqk2r/ppp2ppp/2p2n2/2b3B1/4P3/3P4/PPP2PPP/RN1QKB1R",
    "p2": "r1bq1rk1/pp1nbppp/2p1p3/3n2B1/2BP4/2N1PN2/PP3PPP/2RQK2R",
    "p3": "8/5k1p/3n2p1/1p1P1p2/1P3P2/3BK3/6P1/8",
}

router = ImageRouter()
filt = sys.argv[1] if len(sys.argv) > 1 else ""
for photo in sorted((ROOT / "docs/sprint60/corpus").glob(f"*{filt}*.jpg")):
    true = chess.Board(TRUTH[photo.stem[:2]] + " w - - 0 1")
    t0 = time.time()
    rows = router.read_board(str(photo))
    dt = time.time() - t0
    if rows is None:
        print(f"{photo.stem:22s} {dt:4.0f}s  aucune grille")
        continue
    fen, bottom = grid_to_fen(rows, None)
    read = chess.Board(fen)
    errs = []
    for sq in chess.SQUARES:
        a, b = true.piece_at(sq), read.piece_at(sq)
        if a != b:
            errs.append(f"{chess.square_name(sq)}:{a.symbol() if a else '.'}→{b.symbol() if b else '.'}")
    print(f"{photo.stem:22s} {dt:4.0f}s  bas={bottom:5s} {64 - len(errs)}/64  {' '.join(errs)}")
    print("    " + " ".join(rows))
