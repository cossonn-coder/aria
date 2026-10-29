# Sprint 40 — tronçon 02 : /status, /logs, /errors, /llm, /intents, /parties

Lire d'abord `CLAUDE.md`, `docs/sprint40/00_etat.md`, `docs/sprint40/audit_metacommandes.md`,
et le tronçon 01 (`01_socle_reboot.md`, fait) : même mécanique (`COMMANDS`, `CommandHandler`
filtré, log `meta_command name=…`).

## Objectif

Six commandes de consultation, en lecture seule.

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `interfaces/meta_commands.py` | Textes des 6 commandes + entrées `COMMANDS` |
| `interfaces/telegram_interface.py` | Handlers ; reçoit un `MempalaceBridge` (paramètre optionnel du constructeur) |
| `memory/mempalace_bridge.py` | Nouvelle méthode `count_by_wing() -> dict[str, int]` (via `get_by_metadata`, `include=[]`, une requête par wing connue : `aria_episodic`, `aria_semantic`, `aria_classifier`, `aria_conversation`) |
| `bot.py` | Construit un `MempalaceBridge(store=search, get_by_metadata=get_by_metadata)` (imports de `memory.mempalace_store`, comme `core/kernel.py`) et le passe à `TelegramInterface` |
| tests | Cas nominaux, sous-processus et bridge simulés |

## Comportement attendu

- **`/status`** : en ligne depuis (heure de démarrage du process + durée) ; commit court et
  branche (`git rev-parse --short HEAD`, `git branch --show-current`, cwd = racine projet) ;
  mémoire du process (`VmRSS` de `/proc/self/status`, en Mo) ; nombre d'entrées par wing
  (`count_by_wing`) ; nombre de dossiers de quarantaine `*.drift-*` / `*.corrupt-*` dans
  `config.mempalace_path`.
- **`/logs [N]`** : `journalctl -u aria -n N -o cat --no-pager`, N par défaut 30, plafonné à 200.
- **`/errors`** : sur les 2000 dernières lignes du journal, les 20 dernières contenant `WARNING`,
  `ERROR` ou `Traceback`. Aucune → « Aucune erreur récente. »
- **`/llm`** : sur les 2000 dernières lignes, les 10 dernières contenant `[LLM]` (réponses et
  providers sautés, cf. `llm/llm_router.py`).
- **`/intents`** : intents de `~/.aria/intents.json` (`intent.intent_store.STORE_PATH`) au
  statut `active` : `nom — prochaine action` (sans prochaine action : nom seul). Lecture JSON
  directe, sans `load_intents` (qui recalcule des embeddings).
- **`/parties`** : 5 dernières fiches de `bridge.load_chess_games()` (la liste est croissante) :
  date, couleur de Nico, adversaire (+ Elo si connu), issue en français, ouverture.
  Aucune → « Aucune partie enregistrée. »

Sous-processus (`journalctl`, `git`) : `subprocess.run(..., capture_output=True, text=True,
timeout=10)`. Appels bloquants courts : `asyncio.to_thread` côté handler.

## Tests (cas nominal)

- `count_by_wing` avec `get_by_metadata` factice → compte par wing.
- Une fonction de texte par commande avec entrées factices (sorties de journal, JSON d'intents,
  fiches de parties).
- `/logs 500` → N plafonné à 200.

## Hors scope

- Toute écriture. `/oublie` (tronçon 03). Toucher `core/kernel.py`, `LLMRouter`, `IntentEngine`.

## Critère de fin

`pytest tests/ -q` vert ; `grep -rn "mempalace_store" interfaces/` vide (lecture via le bridge).
