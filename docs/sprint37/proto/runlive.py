# Prototype hors prod : positions des runs live où cyan (≥ 20 %, +15 pts, perte ≤ 15) et rose ≠ meilleur apparaissent, avec la suite de coups depuis le départ.
import io, re, sys, glob
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
for path in sorted(glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint2*/*.txt") + glob.glob("/home/nico/Nextcloud/projects/aria/docs/sprint3*/*.txt")):
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
found = 0
for gi, g in enumerate(games):
    board = g.board()
    for move in g.mainline_moves():
        board.push(move)
        if board.is_game_over() or board.fullmove_number < 8:
            continue
        ref = engine.analyse(board, chess.engine.Limit(time=0.5), multipv=8)
        wins = {i["pv"][0]: _win_of(i) for i in ref}
        win_best = _win_of(ref[0]); best = ref[0]["pv"][0]
        shaped = [m for m in _by_shape(board) if m not in wins]
        if shaped:
            for i in engine.analyse(board, chess.engine.Limit(time=0.5), root_moves=shaped, multipv=len(shaped)):
                wins.setdefault(i["pv"][0], _win_of(i))
        cands = []
        for m, w in wins.items():
            a = board.copy(stack=False); a.push(m)
            if win_best - w <= 15 and not a.is_game_over():
                cands.append((m, a))
        vals = [1 - v for v in maia_values([a.fen() for _, a in cands], ELO)]
        rose = cands[max(range(len(cands)), key=lambda k: vals[k])][0]
        # Cyan : au plus 6 candidats, coups de forme d'abord puis perte croissante.
        order = sorted(cands, key=lambda c: (c[0] not in shaped and not board.gives_check(c[0]) and not board.is_capture(c[0]), win_best - wins[c[0]]))[:6]
        dists = reply_distribution([a.fen() for _, a in order], ELO, config.maia_models_dir)
        cyan = None
        for (m, a), d in zip(order, dists):
            replies, _ = _human_replies(engine, a, d)
            p = sum(r["p"] for r in replies if r["win"] >= win_best + 15)
            if p >= 0.2 and (cyan is None or p > cyan[1]):
                cyan = (m, p)
        if cyan or rose != best:
            prefix = chess.pgn.Game().from_board(board).accept(chess.pgn.StringExporter(headers=False, variations=False, comments=False))
            print(f"partie {gi} | trait {'blancs' if board.turn else 'noirs'} {win_best:.0f} % | meilleur {board.san(best)} | "
                  f"rose {board.san(rose)} | cyan {board.san(cyan[0]) + f' {100*cyan[1]:.0f} %' if cyan else '-'}\n  {prefix}", flush=True)
            if cyan:
                found += 1
        if found >= 4:
            break
    if found >= 4:
        break
engine.quit()
