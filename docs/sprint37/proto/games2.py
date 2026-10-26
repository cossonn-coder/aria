# Prototype hors prod : rose (pronostic Maia) et cyan (piège de retournement) sur les positions perdantes des parties des runs live.
import io, re, sys, glob, random
sys.path.insert(0, "/home/nico/Nextcloud/projects/aria")
sys.path.insert(0, "/tmp/claude-1000/-home-nico-Nextcloud-projects-aria/e1b15485-9bc0-4cf0-8900-f6aa60fb3fe5/scratchpad/proto")
import chess, chess.engine, chess.pgn
from config import config
from chess_coach.analysis import ENGINE_OPTIONS
from chess_coach.explosive import _win_of, _human_replies, _by_shape
from chess_coach.difficulty import reply_distribution
from measure_lib import maia_values

ELO = 1300
games, seen = [], set()
for path in glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint2*/*.txt") + glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint3*/*.txt"):
    text = open(path).read()
    for chunk in re.split(r"=====.*?=====", text):
        if "1." not in chunk:
            continue
        g = chess.pgn.read_game(io.StringIO(chunk))
        if g is None or len(list(g.mainline_moves())) < 10:
            continue
        key = " ".join(m.uci() for m in g.mainline_moves())
        if key not in seen:
            seen.add(key); games.append(g)
print("parties", len(games))

engine = chess.engine.SimpleEngine.popen_uci(config.stockfish_path)
engine.configure(ENGINE_OPTIONS)
losing = []
for g in games:
    board = g.board()
    for move in g.mainline_moves():
        board.push(move)
        if board.is_game_over() or board.fullmove_number < 8:
            continue
        w = _win_of(engine.analyse(board, chess.engine.Limit(time=0.1)))
        if 3 <= w < 35:
            losing.append((w, board.fen()))
print("positions perdantes", len(losing))
random.seed(1)
sample = random.sample(losing, min(16, len(losing)))
stats = []
extra = {}
for w0, fen in sample:
    board = chess.Board(fen)
    ref = engine.analyse(board, chess.engine.Limit(time=1), multipv=8)
    wins = {i["pv"][0]: _win_of(i) for i in ref}
    shaped = [m for m in _by_shape(board) if m not in wins]
    if shaped:
        for i in engine.analyse(board, chess.engine.Limit(time=1), root_moves=shaped, multipv=len(shaped)):
            wins.setdefault(i["pv"][0], _win_of(i))
    moves = [m for m in wins if not board.copy(stack=False).is_game_over()]
    afters = []
    for m in moves:
        a = board.copy(stack=False); a.push(m); afters.append(a)
    keep = [(m, a) for m, a in zip(moves, afters) if not a.is_game_over()]
    moves, afters = [m for m, _ in keep], [a for _, a in keep]
    vals = [100 * (1 - v) for v in maia_values([a.fen() for a in afters], ELO)]
    dists = reply_distribution([a.fen() for a in afters], ELO, config.maia_models_dir)
    best = max(moves, key=lambda m: wins[m])
    rows = {}
    for m, a, v, d in zip(moves, afters, vals, dists):
        replies, _ = _human_replies(engine, a, d)
        swing = sum(r["p"] for r in replies if r["win"] >= 35)
        g10 = sum(r["p"] for r in replies if r["win"] >= wins[best] + 10)
        g15 = sum(r["p"] for r in replies if r["win"] >= wins[best] + 15)
        top = max(replies, key=lambda r: r["win"] if r["p"] >= 0.2 else -1)
        rows[m] = (board.san(m), wins[m], v, swing, g10, g15, wins[best] - wins[m])
    rose = max(rows.values(), key=lambda r: r[2])
    for idx, label in ((4, "+10"), (5, "+15")):
        c = max(rows.values(), key=lambda r: r[idx])
        print(f"  cyan{label} {c[0]:6} proba {100*c[idx]:3.0f} %  perte SF {c[6]:.1f}")
        extra.setdefault(label, []).append((round(100 * c[idx]), round(c[6], 1)))
    cyan = max(rows.values(), key=lambda r: r[3])
    b = rows[best]
    print(f"\n{fen}\n  SF meilleur {b[0]:6} SF {b[1]:4.1f} Maia {b[2]:4.1f} retourn. {100*b[3]:3.0f} %"
          f"\n  rose  {rose[0]:6} SF {rose[1]:4.1f} Maia {rose[2]:4.1f}  (écart Maia +{rose[2]-b[2]:.1f})"
          f"\n  cyan  {cyan[0]:6} SF {cyan[1]:4.1f} Maia {cyan[2]:4.1f} retourn. {100*cyan[3]:3.0f} %  ({len(rows)} candidats)")
    stats.append((rose[2] - b[2], cyan[3], rose[0] == b[0], b[3]))
engine.quit()
print("\nécarts rose vs meilleur :", sorted(round(s[0], 1) for s in stats))
print("retournement du cyan (%) :", sorted(round(100 * s[1]) for s in stats))
print("cyan relatif (proba %, perte SF) :", {k: sorted(v) for k, v in extra.items()})
print("rose = meilleur coup :", sum(s[2] for s in stats), "/", len(stats))
