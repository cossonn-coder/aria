# aria/interfaces/board_interface.py
#
# Serveur de l'échiquier ARIA (sprint 35, tronçon 01, dette #94).
#
# Sert la page de l'échiquier, reçoit la position affichée et expose le
# résultat courant de l'analyse live (chess_coach.live). Un worker unique
# enchaîne les passes ×1, ×2, ×4, ×8 sur la dernière position reçue ; une
# nouvelle position abandonne la passe en cours.
# Hors kernel : aucune écriture mémoire, aucun router, aucun LLM.

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import chess
import chess.engine

from chess_coach import difficulty
from chess_coach.analysis import ENGINE_OPTIONS
from chess_coach.live import FACTORS, EngineProxy, Superseded, analyse_pass
from config import config
from logger import get_logger

log = get_logger(__name__)

_INDEX = Path(__file__).parent / "board" / "index.html"


class BoardWorker:
    """Analyse live de la dernière position reçue, état partagé sous verrou.

    État : id (numéro de position), pass (passe en cours, ou dernière passe
    quand running est faux), passes, running, result (dernière passe terminée),
    explosive, forced, best, trap (piège cyan), strategy (stratégie rose), error.
    """

    def __init__(self, open_engine, models_dir: str, run_pass=analyse_pass):
        self._open_engine = open_engine
        self._models_dir = models_dir
        self._run_pass = run_pass
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._position = None
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
        self._wake.set()
        return position_id

    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def _stale(self, position_id: int) -> bool:
        with self._lock:
            return self._state["id"] != position_id

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
        """Passes successives sur une position ; chacune remplace la précédente."""
        for number, factor in enumerate(FACTORS, start=1):
            with self._lock:
                if self._state["id"] != position_id:
                    return
                self._state["pass"] = number
            proxy = EngineProxy(engine, factor, lambda: self._stale(position_id))
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
        if self.path != "/position":
            self._send(404, b"", "text/plain")
            return
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        position_id = self.server.worker.submit(data["fen"], int(data["elo_white"]), int(data["elo_black"]))
        self._json({"id": position_id})

    def log_message(self, format, *args):
        # Requêtes /state toutes les secondes : hors journal du service.
        log.debug(format % args)


def make_server(port: int, worker: BoardWorker) -> ThreadingHTTPServer:
    """Serveur HTTP lié à 0.0.0.0:port, adossé à worker."""
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    server.worker = worker
    return server


def _open_engine():
    engine = chess.engine.SimpleEngine.popen_uci(config.stockfish_path)
    engine.configure(ENGINE_OPTIONS)
    return engine


def start_board_server():
    """Lance le worker et le serveur de l'échiquier dans des threads daemon."""
    worker = BoardWorker(_open_engine, config.maia_models_dir)
    server = make_server(config.board_port, worker)
    threading.Thread(target=worker.run, daemon=True, name="board-worker").start()
    threading.Thread(target=server.serve_forever, daemon=True, name="board-server").start()
    log.info(f"Échiquier ARIA à l'écoute sur le port {config.board_port}")
