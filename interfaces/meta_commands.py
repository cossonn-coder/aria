# aria/interfaces/meta_commands.py
#
# Métacommandes Telegram (sprint 40, #131).
#
# Responsabilité : bâtir le texte des réponses aux commandes /xxx.
# Les handlers Telegram (minces) vivent dans TelegramInterface ; les
# commandes ne passent pas par le kernel et ne sont pas écrites dans
# l'historique de conversation.

import json
import subprocess
from datetime import datetime
from pathlib import Path

from chess_coach.summary import _COLOR_FR, _OUTCOME_FR
from config import config
from intent.intent_store import STORE_PATH

# Nom → description courte. Sert à /help et à set_my_commands
# (auto-complétion Telegram). Les tronçons 02-03 y ajoutent leurs commandes.
COMMANDS = {
    "help": "Liste des commandes",
    "reboot": "Redémarre ARIA",
    "board": "Lien de l'échiquier",
    "again": "Renvoie ma dernière réponse",
}

REBOOT_TEXT = "🔄 Redémarrage… (≈ 15 s)"
BACK_TEXT = "✅ De retour."
NOTHING_TO_RESEND = "Rien à renvoyer."


def help_text() -> str:
    """Une ligne par commande : « /nom — description »."""
    return "\n".join(f"/{name} — {description}" for name, description in COMMANDS.items())


def board_text() -> str:
    """URL de l'échiquier ARIA."""
    return config.board_url


# =========================================================
# CONSULTATIONS (tronçon 02) — lecture seule
# =========================================================
# Chaque commande se coupe en deux : une lecture (sous-processus, fichier,
# bridge) et une fonction de texte pure, testée sur des entrées factices.
# Les lectures sont bloquantes et courtes : le handler les passe par
# asyncio.to_thread.

COMMANDS.update({
    "status": "État d'ARIA (uptime, commit, mémoire)",
    "logs": "Dernières lignes du journal (/logs N)",
    "errors": "Avertissements et erreurs récents",
    "llm": "Derniers appels LLM",
    "intents": "Intents actifs",
    "parties": "Dernières parties d'échecs",
})

# Racine du projet : cwd des appels git.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Heure de démarrage du process : ce module est importé au lancement du bot.
STARTED_AT = datetime.now()

LOGS_DEFAULT = 30
LOGS_MAX = 200
JOURNAL_SCAN = 2000
ERRORS_SHOWN = 20
LLM_SHOWN = 10
PARTIES_SHOWN = 5

NO_ERRORS = "Aucune erreur récente."
NO_LLM = "Aucun appel LLM récent."
NO_INTENTS = "Aucun intent actif."
NO_PARTIES = "Aucune partie enregistrée."


def _run(args: list[str]) -> str:
    """Sous-processus court, sortie standard en texte."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=10, cwd=PROJECT_ROOT)
    return result.stdout


def journal_lines(n: int) -> list[str]:
    """Les n dernières lignes du journal du service aria."""
    return _run(["journalctl", "-u", "aria", "-n", str(n), "-o", "cat", "--no-pager"]).splitlines()


# ── /logs ────────────────────────────────────────────────────────────────────

def logs_count(args: list[str]) -> int:
    """N de « /logs N » : 30 par défaut, plafonné à 200."""
    if args and args[0].isdigit():
        return min(int(args[0]), LOGS_MAX)
    return LOGS_DEFAULT


def logs_text(lines: list[str]) -> str:
    return "\n".join(lines) or "Journal vide."


# ── /errors, /llm ────────────────────────────────────────────────────────────

def errors_text(lines: list[str]) -> str:
    """Les 20 dernières lignes WARNING / ERROR / Traceback."""
    hits = [l for l in lines if "WARNING" in l or "ERROR" in l or "Traceback" in l]
    return "\n".join(hits[-ERRORS_SHOWN:]) or NO_ERRORS


def llm_text(lines: list[str]) -> str:
    """Les 10 dernières lignes [LLM] (réponses, providers sautés)."""
    hits = [l for l in lines if "[LLM]" in l]
    return "\n".join(hits[-LLM_SHOWN:]) or NO_LLM


# ── /intents ─────────────────────────────────────────────────────────────────

def read_intents() -> dict:
    """JSON brut des intents (sans load_intents, qui recalcule des embeddings)."""
    if not STORE_PATH.exists():
        return {}
    return json.loads(STORE_PATH.read_text())


def intents_text(data: dict) -> str:
    """« nom — prochaine action » pour chaque intent actif."""
    lines = []
    for intent in data.values():
        if intent.get("status") != "active":
            continue
        name = intent.get("name", "")
        next_action = intent.get("next_action")
        lines.append(f"{name} — {next_action}" if next_action else name)
    return "\n".join(lines) or NO_INTENTS


# ── /parties ─────────────────────────────────────────────────────────────────

def parties_text(games: list[dict]) -> str:
    """5 dernières fiches (liste croissante) : date, couleur, adversaire, issue, ouverture."""
    if not games:
        return NO_PARTIES
    lines = []
    for game in reversed(games[-PARTIES_SHOWN:]):
        opponent = game.get("opponent") or "?"
        if game.get("elo_opponent"):
            opponent += f" ({game['elo_opponent']})"
        lines.append(" · ".join([
            game.get("date") or "date inconnue",
            _COLOR_FR.get(game.get("nico_color"), "?"),
            f"contre {opponent}",
            _OUTCOME_FR.get(game.get("outcome"), "issue inconnue"),
            game.get("opening") or "ouverture inconnue",
        ]))
    return "\n".join(lines)


# ── /status ──────────────────────────────────────────────────────────────────

def _rss_mb() -> int:
    """VmRSS du process, en Mo."""
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) // 1024
    return 0


def _quarantine_count() -> int:
    """Dossiers de quarantaine .drift-* / .corrupt-* du palace."""
    palace = Path(config.mempalace_path)
    return len(list(palace.glob("*.drift-*"))) + len(list(palace.glob("*.corrupt-*")))


def read_status(bridge) -> dict:
    """Rassemble les données de /status (git, mémoire, palace)."""
    return {
        "started_at": STARTED_AT,
        "now": datetime.now(),
        "commit": _run(["git", "rev-parse", "--short", "HEAD"]).strip(),
        "branch": _run(["git", "branch", "--show-current"]).strip(),
        "rss_mb": _rss_mb(),
        "counts": bridge.count_by_wing(),
        "quarantine": _quarantine_count(),
    }


def status_text(status: dict) -> str:
    uptime = status["now"] - status["started_at"]
    hours, rest = divmod(int(uptime.total_seconds()), 3600)
    lines = [
        f"En ligne depuis {status['started_at']:%d/%m %H:%M} ({hours} h {rest // 60:02d})",
        f"Commit {status['commit']} sur {status['branch']}",
        f"Mémoire du process : {status['rss_mb']} Mo",
    ]
    lines += [f"{wing} : {count}" for wing, count in status["counts"].items()]
    lines.append(f"Quarantaine : {status['quarantine']} dossier(s)")
    return "\n".join(lines)
