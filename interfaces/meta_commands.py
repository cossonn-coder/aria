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
import unicodedata
from datetime import datetime
from pathlib import Path

from chess_coach.player_model import game_opening_group, opening_stats
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
    "ouvertures": "Statistiques par ouverture (/ouvertures nom)",
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
NO_OPENINGS = "Aucune partie enregistrée : pas de statistiques d'ouverture."


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


# ── /ouvertures ──────────────────────────────────────────────────────────────

def openings_text(games: list[dict]) -> str:
    """Une ligne par (groupe, couleur), du plus joué au moins joué, puis les issues inconnues."""
    if not games:
        return NO_OPENINGS
    lines = []
    stats = opening_stats(games)
    for (group, color), s in sorted(stats.items(), key=lambda item: -item[1].games):
        lines.append(
            f"{group} ({_COLOR_FR[color]}) : {s.wins} V, {s.draws} N, {s.losses} D — "
            f"{s.win_rate * 100:.0f} % [{s.games} partie{'s' if s.games > 1 else ''}]"
        )
    unknown = sum(1 for g in games if g.get("outcome") not in ("win", "draw", "loss"))
    lines.append(f"Issue inconnue, non comptée : {unknown} fiche(s)")
    return "\n".join(lines)


# ── /ouvertures <nom> ────────────────────────────────────────────────────────

RECENT_GAMES = 5
# Issue → libellé des lignes de détail, dans l'ordre d'affichage.
_OUTCOME_LABELS = {"win": "victoires", "draw": "nulles", "loss": "défaites"}
_OUTCOME_LETTERS = {"win": "V", "draw": "N", "loss": "D"}


def _plain(text: str) -> str:
    """Texte sans accents ni casse, pour comparer un nom d'ouverture à une requête."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _decimal(value: float) -> str:
    """Une décimale, avec une virgule."""
    return f"{value:.1f}".replace(".", ",")


def _record(games: list[dict]) -> str:
    """« 8 V, 3 D — 73 % » : les catégories à zéro sont omises."""
    outcomes = [game["outcome"] for game in games]
    parts = ", ".join(
        f"{outcomes.count(outcome)} {letter}" for outcome, letter in _OUTCOME_LETTERS.items() if outcome in outcomes
    )
    return f"{parts} — {outcomes.count('win') / len(games) * 100:.0f} %"


def _per_outcome_line(title: str, games: list[dict], value, fmt) -> list[str]:
    """Ligne « titre : victoires x, défaites y » ; value(fiche) rend None si pas de donnée.
    Une issue sans donnée est omise ; sans aucune donnée, pas de ligne du tout."""
    parts = []
    for outcome, label in _OUTCOME_LABELS.items():
        values = [value(g) for g in games if g["outcome"] == outcome]
        values = [v for v in values if v is not None]
        if values:
            parts.append(f"{label} {fmt(sum(values) / len(values))}")
    return [f"{title} : {', '.join(parts)}"] if parts else []


def _win_at_move(game: dict, move_number: int) -> float | None:
    """win_before du coup de Nico au numéro donné ; None si la partie ne l'atteint pas."""
    for ply in json.loads(game.get("plies_json") or "[]"):
        if ply["color"] == game["nico_color"] and ply["move_number"] == move_number:
            return ply["win_before"]
    return None


def _game_date_key(game: dict) -> tuple[str, str]:
    """Clé de tri chronologique : date de partie, à défaut d'analyse ; puis timestamp."""
    timestamp = game.get("timestamp") or ""
    return (game.get("date") or timestamp[:10]).replace(".", "-"), timestamp


def _color_section(group: str, color: str, games: list[dict]) -> str:
    """Rapport d'une ouverture pour une couleur : une ligne absente si pas de donnée."""
    count = len(games)
    lines = [f"{group} ({_COLOR_FR[color]}) : {_record(games)} [{count} partie{'s' if count > 1 else ''}]"]
    plies = [g["n_plies"] / 2 for g in games if g.get("n_plies")]
    if plies:
        lines.append(f"Coups par partie en moyenne : {_decimal(sum(plies) / len(plies))}")
    lines += _per_outcome_line("Elo adverse moyen", games, lambda g: g.get("elo_opponent") or None, lambda v: f"{v:.0f}")
    for move_number in (10, 20):
        lines += _per_outcome_line(
            f"% de gain au coup {move_number}", games, lambda g: _win_at_move(g, move_number), _decimal,
        )
    if count > RECENT_GAMES:
        recent = sorted(games, key=_game_date_key)[-RECENT_GAMES:]
        lines.append(f"{RECENT_GAMES} dernières : {_record(recent)}")
    return "\n".join(lines)


def opening_report_text(games: list[dict], query: str) -> str:
    """Statistiques de l'ouverture désignée par query, une section par couleur, la plus jouée d'abord."""
    by_group: dict[str, list[dict]] = {}
    for game in games:
        if game.get("opening") and game.get("outcome") in _OUTCOME_LABELS:
            by_group.setdefault(game_opening_group(game), []).append(game)

    wanted = _plain(query)
    matches = [g for g in by_group if _plain(g) == wanted] or [g for g in by_group if wanted in _plain(g)]
    if not matches:
        return f"Aucune ouverture ne correspond à « {query} ». Liste : /ouvertures"
    if len(matches) > 1:
        return f"Plusieurs ouvertures correspondent : {', '.join(sorted(matches))}."

    by_color: dict[str, list[dict]] = {}
    for game in by_group[matches[0]]:
        by_color.setdefault(game["nico_color"], []).append(game)
    sections = sorted(by_color.items(), key=lambda item: -len(item[1]))
    return "\n\n".join(_color_section(matches[0], color, g) for color, g in sections)


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


# =========================================================
# /oublie (tronçon 03) — marqueur de coupure de la conversation
# =========================================================
# L'écriture passe par memory.writer.write_conversation_reset (appelée par
# le handler) ; rien n'est supprimé, la coupure se fait à la lecture.

COMMANDS["oublie"] = "Repartir d'une conversation vierge"

FORGET_TEXT = "🧹 Conversation oubliée. Les souvenirs restent."
