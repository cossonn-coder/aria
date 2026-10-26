# Prototype hors prod : l'orange (coup explosif) et le rose (pronostic Maia max, perte ≤ 15) coïncident-ils ?
import io, re, sys, glob, random
sys.path.insert(0, "/home/nico/Nextcloud/projects/aria")
sys.path.insert(0, "/tmp/claude-1000/-home-nico-Nextcloud-projects-aria/e1b15485-9bc0-4cf0-8900-f6aa60fb3fe5/scratchpad/proto")
import chess, chess.engine, chess.pgn
from config import config
from chess_coach.analysis import ENGINE_OPTIONS
from chess_coach.explosive import _win_of, _search_position
from measure_lib import maia_values

ELO = 1300
games, seen = [], set()
for path in glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint2*/*.txt") + glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint3*/*.txt"):
    for chunk in re.split(r"=====.*?=====", open(path).read()):
        if "1." not in chunk:
            continue
        g = chess.pgn.read_game(io.StringIO(chunk))
        if g is None or len(list(g.mainline_moves())) < 10:
            continue
        key = " ".join(m.uci() for m in g.mainline_moves())
        if key not in seen:
            seen.add(key); games.append(g)
engine = chess.engine.SimpleEngine.popen_uci(config.stockfish_path)
engine.configure(ENGINE_OPTIONS)
window = []
for g in games:
    board = g.board()
    for move in g.mainline_moves():
        board.push(move)
        if board.is_game_over() or board.fullmove_number < 6:
            continue
        w = _win_of(engine.analyse(board, chess.engine.Limit(time=0.1)))
        if 35 <= w <= 85:
            window.append(board.fen())
random.seed(2)
sample = random.sample(window, min(30, len(window)))
print("positions fenêtre", len(window), "échantillon", len(sample))
n_orange = same = 0
for fen in sample:
    board = chess.Board(fen)
    explosive = _search_position(engine, board, "", "", ELO, config.maia_models_dir)
    ref = engine.analyse(board, chess.engine.Limit(time=0.5), multipv=8)
    win_best = _win_of(ref[0])
    cands = [i["pv"][0] for i in ref if win_best - _win_of(i) <= 15]
    afters = []
    for m in cands:
        a = board.copy(stack=False); a.push(m); afters.append(a.fen())
    vals = [1 - v for v in maia_values(afters, ELO)]
    rose = cands[max(range(len(cands)), key=lambda k: vals[k])]
    best = ref[0]["pv"][0]
    o = explosive.san if explosive else "-"
    r = board.san(rose)
    tag = ""
    if explosive:
        n_orange += 1
        if explosive.uci == rose.uci():
            same += 1; tag = "  ← ÉGAUX"
    print(f"orange {o:7} rose {r:7} meilleur {board.san(best):7}{tag}")
engine.quit()
print(f"\npositions avec orange : {n_orange}/{len(sample)} ; orange = rose : {same}/{n_orange}")
