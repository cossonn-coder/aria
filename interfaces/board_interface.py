# aria/interfaces/board_interface.py
#
# Serveur de l'échiquier ARIA (sprint 35, tronçon 01, dette #94).
#
# Sert la page de l'échiquier, reçoit la position affichée et expose le
# résultat courant de l'analyse live (chess_coach.live). Un worker unique
# enchaîne les passes ×1, ×2, ×4, ×8 sur la dernière position reçue ; une
# nouvelle position abandonne la passe en cours. Le résultat de chaque position
# est gardé : y revenir le rend aussitôt et reprend aux passes restantes (sprint 49).
# Hors kernel : aucune écriture mémoire, aucun router, aucun LLM. Sprint 52 : lecture
# seule des fiches chess_game par une méthode du bridge injectée (historique /game).

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import chess
import chess.engine

from chess_coach import difficulty
from chess_coach.analysis import ENGINE_OPTIONS, _win, analyze_game, detect_color, parse_pgn
from chess_coach.level import accuracy_rank, performance
from chess_coach.live import FACTORS, EngineProxy, Superseded, analyse_pass
from chess_coach.openings import detect_opening, opening_group
from chess_coach.player_model import game_opening_group
from chess_coach.summary import _COLOR_FR, _effective_loss, _game_accuracy, _move_accuracy
from config import config
from interfaces.meta_commands import RECENT_GAMES, _game_date_key
from logger import get_logger

log = get_logger(__name__)

_INDEX = Path(__file__).parent / "board" / "index.html"


class BoardWorker:
    """Analyse live de la dernière position reçue, état partagé sous verrou.

    État : id (numéro de position), pass (passe en cours, ou dernière passe
    quand running est faux), passes, running, result (dernière passe terminée),
    explosive, forced, best, trap (piège cyan), strategy (stratégie rose), error.
    best et forced arrivent dès l'analyse de tête de la première passe.
    """

    def __init__(self, open_engine, models_dir: str, run_pass=analyse_pass):
        self._open_engine = open_engine
        self._models_dir = models_dir
        self._run_pass = run_pass
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._position = None
        # (fen, elo) → (résultat de la dernière passe terminée, numéro de cette passe).
        self._finished = {}
        self._state = self._initial(0)

    @staticmethod
    def _initial(position_id: int) -> dict:
        return {"id": position_id, "pass": 1, "passes": len(FACTORS), "running": position_id > 0,
                "result": "pending", "explosive": None, "forced": None, "best": None,
                "trap": None, "strategy": None, "error": None}

    def submit(self, fen: str, elo_white: int, elo_black: int) -> int:
        """Nouvelle position : remplace la précédente et réveille le worker."""
        with self._lock:
            position_id = self._state["id"] + 1
            # Maia reçoit l'Elo de l'adversaire du trait.
            elo = elo_black if chess.Board(fen).turn == chess.WHITE else elo_white
            self._position = (position_id, fen, elo)
            self._state = self._initial(position_id)
            if (fen, elo) in self._finished:
                outcome, number = self._finished[(fen, elo)]
                self._state.update(outcome)
                self._state.update({"pass": number, "running": number < len(FACTORS)})
        self._wake.set()
        return position_id

    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def _stale(self, position_id: int) -> bool:
        with self._lock:
            return self._state["id"] != position_id

    def _publish_head(self, position_id: int, head: dict):
        """Tête de passe dans l'état. Seulement avant le premier résultat : ensuite
        best reste celui de la passe des autres flèches (blocs sauvegardés de la page)."""
        with self._lock:
            if self._state["id"] == position_id and self._state["result"] == "pending":
                self._state.update(head)

    def run(self):
        """Boucle du worker : moteur ouvert à la première position, gardé ensuite."""
        engine = None
        while True:
            self._wake.wait()
            self._wake.clear()
            if engine is None:
                engine = self._open_engine()
            with self._lock:
                position_id, fen, elo = self._position
            self._analyse(engine, position_id, fen, elo)

    def _analyse(self, engine, position_id: int, fen: str, elo: int):
        """Passes restantes sur une position ; chacune remplace la précédente."""
        with self._lock:
            done = self._finished[(fen, elo)][1] if (fen, elo) in self._finished else 0
        for number, factor in enumerate(FACTORS[done:], start=done + 1):
            with self._lock:
                if self._state["id"] != position_id:
                    return
                self._state["pass"] = number
            proxy = EngineProxy(engine, factor, lambda: self._stale(position_id),
                                lambda head: self._publish_head(position_id, head))
            start = time.monotonic()
            try:
                outcome = self._run_pass(proxy, fen, elo, self._models_dir)
            except Superseded:
                log.info(f"board_analysis superseded id={position_id}")
                return
            except Exception as exc:
                log.exception(f"board_analysis error id={position_id} pass={number}")
                with self._lock:
                    if self._state["id"] == position_id:
                        self._state.update(running=False, error=str(exc))
                return
            with self._lock:
                # La passe Maia n'est pas interruptible : un résultat périmé est jeté.
                if self._state["id"] != position_id:
                    log.info(f"board_analysis superseded id={position_id}")
                    return
                self._state.update(outcome)
                self._state["running"] = number < len(FACTORS)
                self._finished[(fen, elo)] = (outcome, number)
            log.info(f"board_analysis id={position_id} pass={number} result={outcome['result']} "
                     f"duration={time.monotonic() - start:.1f}s")


_maia_lock = threading.Lock()
_maia_started = False


def _load_maia_in_background():
    """Charge Maia une fois (cache difficulty._load, partagé avec l'analyse Telegram)."""
    global _maia_started
    with _maia_lock:
        if _maia_started:
            return
        _maia_started = True
    threading.Thread(target=difficulty._load, args=(config.maia_models_dir,), daemon=True).start()


def _mate(cp: int):
    """Mat forcé côté blancs depuis un cp blancs non borné (sprint 39).

    Un mat en N vaut ±(100000 − N) : +N = les blancs matent, −N = les noirs.
    |cp| == 100000 = position déjà matée → None (pas de repère sur la courbe).
    """
    if 90000 <= abs(cp) < 100000:
        return (100000 - abs(cp)) * (1 if cp > 0 else -1)
    return None


def game_wins(plies: list) -> dict:
    """Courbe d'une partie : % de gain des blancs, mat forcé et meilleur coup par position.

    plies : demi-coups d'analyze_game. N+1 valeurs par liste (sprint 38, étendu
    sprint 39). win_before / win_after sont du point de vue du trait : on les
    ramène au point de vue des blancs ; eval_before_cp / eval_after_cp le sont déjà.
    """
    wins = [p.win_before if p.color == "white" else 100 - p.win_before for p in plies]
    last = plies[-1]
    wins.append(last.win_after if last.color == "white" else 100 - last.win_after)
    mates = [_mate(p.eval_before_cp) for p in plies] + [_mate(last.eval_after_cp)]
    best = [p.best_san for p in plies] + [None]
    return {"wins": [round(w, 1) for w in wins], "mates": mates, "best": best}


def game_history(game, plies: list, playing: str, games: list) -> list[str]:
    """Lignes d'historique d'une partie chargée (sprint 52, tronçon 03).

    Camp de Nico par les en-têtes (pseudos), sinon le champ « Je joue » de la page ;
    camp inconnu → []. Ligne 1 : rang de sa précision parmi ses fiches. Ligne 2 :
    performance Elo dans l'ouverture détectée et cette couleur (total + 5 dernières).
    games : fiches chess_game (lecture seule, via le bridge).
    """
    color, source = detect_color(game.headers, "")
    if source == "default":
        color = playing
    if color not in _COLOR_FR:
        return []
    lines = []
    accuracy = _game_accuracy(plies, color)
    if accuracy is not None:
        rank, total = accuracy_rank(accuracy, games)
        which = "ta meilleure partie" if rank == 1 else f"ta {rank}e meilleure partie"
        lines.append(f"Précision {accuracy:.0f} % : {which} sur {total}")
    # Même règle que le bilan Telegram : pas de détection depuis une position de départ libre.
    detected = None if "FEN" in game.headers else detect_opening([m.uci() for m in game.mainline_moves()])
    if detected:
        group = opening_group(detected[1])
        same = [g for g in games if g.get("opening") and g.get("nico_color") == color
                and game_opening_group(g) == group]
        perf = performance(same)
        if perf:
            line = (f"{group} ({_COLOR_FR[color]}) : performance {perf[0]} "
                    f"[{perf[1]} partie{'s' if perf[1] > 1 else ''}]")
            recent = performance(sorted(same, key=_game_date_key)[-RECENT_GAMES:])
            if len(same) > RECENT_GAMES and recent:
                line += f" · {RECENT_GAMES} dernières : {recent[0]}"
            lines.append(line)
    return lines


def position_eval(fen: str) -> dict:
    """Évaluation d'une position seule (jeu libre, sprint 39) : un Stockfish par appel.

    win en % de gain des blancs, mate signé côté blancs, best en SAN.
    """
    board = chess.Board(fen)
    if board.is_game_over():
        # Position terminale : pas d'analyse ; le camp au trait est maté ou c'est nul.
        win = (0 if board.turn == chess.WHITE else 100) if board.is_checkmate() else 50
        return {"win": win, "mate": None, "best": None}
    with chess.engine.SimpleEngine.popen_uci(config.stockfish_path) as engine:
        engine.configure(ENGINE_OPTIONS)
        info = engine.analyse(board, chess.engine.Limit(time=0.15))
    score = info["score"].white()
    return {"win": round(_win(score.score(mate_score=100000)), 1), "mate": score.mate(),
            "best": board.san(info["pv"][0])}


def line_accuracy(wins: list, best: list, first: str) -> dict:
    """Précision de chaque coup d'une ligne et précision totale de chaque camp (sprint 39).

    wins : N+1 % de gain des blancs (positions de la ligne), best : N booléens (coup
    joué = meilleur coup), first : camp du premier coup. Même formule que le bilan
    Telegram (summary.py) : on reconstruit des demi-coups minimaux qu'elle sait lire.
    white[k] / black[k] = précision totale du camp sur les coups 0..k (None sans coup).
    """
    plies = []
    for i, is_best in enumerate(best):
        color = ("white", "black")[(i + (first == "black")) % 2]
        # win_before / win_after au point de vue du joueur qui joue le coup.
        before, after = (wins[i], wins[i + 1]) if color == "white" else (100 - wins[i], 100 - wins[i + 1])
        plies.append(SimpleNamespace(color=color, win_before=before, win_after=after,
                                     loss=max(0, before - after), quality="best" if is_best else "other"))
    return {
        "moves": [round(_move_accuracy(_effective_loss(p)), 1) for p in plies],
        "white": [_game_accuracy(plies[:k + 1], "white") for k in range(len(plies))],
        "black": [_game_accuracy(plies[:k + 1], "black") for k in range(len(plies))],
    }


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict):
        self._send(200, json.dumps(payload).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            _load_maia_in_background()
            self._send(200, _INDEX.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/state":
            self._json(self.server.worker.state())
        else:
            self._send(404, b"", "text/plain")

    def do_POST(self):
        if self.path not in ("/position", "/game", "/eval", "/send", "/accuracy"):
            self._send(404, b"", "text/plain")
            return
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/send":
            self._send_to_aria(data["pgn"])
            return
        if self.path == "/game":
            self._game(data["pgn"], data.get("playing", ""))
            return
        if self.path == "/accuracy":
            self._json(line_accuracy(data["wins"], data["best"], data["first"]))
            return
        if self.path == "/eval":
            start = time.monotonic()
            result = position_eval(data["fen"])
            log.info(f"board_eval duration={time.monotonic() - start:.2f}s")
            self._json(result)
            return
        position_id = self.server.worker.submit(data["fen"], int(data["elo_white"]), int(data["elo_black"]))
        self._json({"id": position_id})

    def _game(self, pgn: str, playing: str):
        """Courbe d'évaluation d'une partie PGN et historique de Nico ; requête synchrone dans son thread."""
        # parse_pgn exige une ligne d'en-tête : un PGN réduit aux coups en reçoit une minimale.
        game = parse_pgn(pgn) or parse_pgn('[Event "?"]\n' + pgn)
        if game is None:
            self._send(400, json.dumps({"error": "PGN illisible"}).encode(), "application/json")
            return
        start = time.monotonic()
        plies = analyze_game(game, "white", config.stockfish_path)
        curve = game_wins(plies)
        log.info(f"board_game plies={len(curve['wins']) - 1} duration={time.monotonic() - start:.1f}s")
        curve["history"] = self._history(game, plies, playing)
        self._json(curve)

    def _history(self, game, plies: list, playing: str) -> list[str]:
        """Historique de la partie ; [] sans lecteur de fiches ou si la lecture échoue
        (la courbe part quand même)."""
        load_games = self.server.load_games
        if load_games is None:
            return []
        try:
            games = load_games()
        except Exception as exc:
            log.warning(f"board_history load_games error={exc}")
            return []
        return game_history(game, plies, playing, games)

    def _send_to_aria(self, pgn: str):
        """Remet le PGN à ARIA comme un message de Nico (sprint 39) ; 503 si ARIA pas prêt."""
        log.info(f"board_send chars={len(pgn)}")
        submit_text = self.server.submit_text
        if submit_text is not None and submit_text(pgn):
            self._json({"sent": True})
        else:
            self._send(503, json.dumps({"error": "ARIA pas prêt"}).encode(), "application/json")

    def log_message(self, format, *args):
        # Requêtes /state toutes les secondes : hors journal du service.
        log.debug(format % args)


def make_server(port: int, worker: BoardWorker, submit_text=None, load_games=None) -> ThreadingHTTPServer:
    """Serveur HTTP lié à 0.0.0.0:port, adossé à worker.

    submit_text(texte) -> bool : fonction d'envoi à ARIA (route /send), injectée
    par bot.py ; l'échiquier ne voit pas le kernel.
    load_games() -> list[dict] : lecture seule des fiches chess_game (sprint 52),
    méthode du bridge injectée par bot.py ; aucune écriture mémoire.
    """
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    server.worker = worker
    server.submit_text = submit_text
    server.load_games = load_games
    return server


def _open_engine():
    engine = chess.engine.SimpleEngine.popen_uci(config.stockfish_path)
    engine.configure(ENGINE_OPTIONS)
    return engine


def start_board_server(submit_text=None, load_games=None):
    """Lance le worker et le serveur de l'échiquier dans des threads daemon."""
    worker = BoardWorker(_open_engine, config.maia_models_dir)
    server = make_server(config.board_port, worker, submit_text, load_games)
    threading.Thread(target=worker.run, daemon=True, name="board-worker").start()
    threading.Thread(target=server.serve_forever, daemon=True, name="board-server").start()
    log.info(f"Échiquier ARIA à l'écoute sur le port {config.board_port}")
