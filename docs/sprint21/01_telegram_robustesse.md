# Sprint 21 — tronçon 01 : robustesse réseau Telegram (#62, #63)

Lire avant : `CLAUDE.md`, `docs/sprint21/00_etat.md`. Diagnostic complet :
`docs/sprint21/audit_telegram_reseau.md` (facultatif, ce kickoff suffit).

## Objectif

Qu'un timeout réseau Telegram ne fasse plus ni crash au démarrage, ni
réponse perdue, ni trace ERROR complète ; et journaliser chaque update reçu
pour pouvoir diagnostiquer #63 (photo traitée deux fois) à sa prochaine
occurrence.

## Fichier à toucher

`interfaces/telegram_interface.py` (seul fichier de prod). python-telegram-bot
22.7. Le module n'a pas encore de logger : ajouter
`from logger import get_logger` / `log = get_logger(__name__)` (convention
projet, jamais `print()`).

## Comportement attendu

1. **Démarrage (Q2)** — `start()` : `self.app.run_polling()` devient
   `self.app.run_polling(bootstrap_retries=-1)`. PTB réessaie alors
   `initialize()` (get_me) indéfiniment avec son backoff au lieu de lever
   et de tuer le process.

2. **Envoi (Q3)** — dans `send()`, chaque appel `self.app.bot.send_message`
   / `send_photo` est réessayé sur `telegram.error.NetworkError` (dont
   `TimedOut` hérite) : 3 tentatives au total, `await asyncio.sleep` de 2 s
   puis 4 s entre elles. À chaque échec intermédiaire : `log.warning` une
   ligne (tentative n/3, type d'exception, chat_id). Après la 3e : on laisse
   remonter l'exception (l'error handler du point 3 la loguera).
   Pour `send_photo`, le fichier doit être rouvert à chaque tentative (un
   handle déjà lu ne se renvoie pas). Forme libre (petit helper privé
   prenant une fabrique de coroutine, ou boucle inline) — rester minimal.
   Doublon possible si Telegram a reçu le message mais que la réponse s'est
   perdue : accepté (décision Q3).

3. **Error handler (Q3)** — dans `start()`, `self.app.add_error_handler(...)`
   avec une coroutine `async def _on_error(self, update, context)` qui fait
   `log.warning("telegram error: %s: %s", type(err).__name__, err)` avec
   `err = context.error`, **sans** trace complète. Couvre les erreurs de
   `getUpdates` (Bad Gateway nocturne ~03:11) et les envois définitivement
   échoués. Plus de ligne « No error handlers are registered ».

4. **Log de réception (Q4)** — au début de `_handle_message` et de
   `_handle_photo`, une ligne `log.info` :
   `telegram_update update_id=<update.update_id> message_id=<update.message.message_id> type=text|photo`.
   Aucune déduplication.

Ne rien changer d'autre : locks, construction des Event, appel kernel,
découpage 4096 restent tels quels.

## Tests à ajouter (cas nominal)

Nouveau `tests/interfaces/test_telegram_interface.py` (+ `tests/interfaces/__init__.py`
vide, comme `tests/agents/`). pytest-asyncio 1.3.0 en mode strict
(`pytest.ini` sans `asyncio_mode`) → `@pytest.mark.asyncio`.

- `send()` texte : `app.bot.send_message` mocké (AsyncMock) qui lève
  `telegram.error.TimedOut` une fois puis réussit ; `asyncio.sleep` patché
  (pas d'attente réelle). Attendu : 2 appels, pas d'exception.

Construire l'interface sans réseau : `TelegramInterface(kernel=MagicMock(), token="x")`
puis assigner `iface.app = MagicMock()` (ne pas appeler `start()`).

Un seul test suffit (calibrage faible). Pas de test sur `run_polling`,
l'error handler ou le log de réception.

## Hors scope (NE PAS faire)

- Déduplication par `update_id` / `message_id` (#63 reste à confirmer).
- Changer les timeouts HTTPXRequest, l'IPv6 de la VM, `aria.service`.
- Corriger le découpage 4096 au milieu des mots (dette adjacente notée).
- Toucher `bot.py`, le kernel, les routers, la mémoire.

## Critère de fin

- `pytest tests/ -q` vert, nouveau test inclus.
- `grep -n "bootstrap_retries=-1\|add_error_handler\|telegram_update" interfaces/telegram_interface.py`
  → 4 occurrences (1 + 1 + 2 handlers).
- Commit local `feat(sprint21) tronçon 01: robustesse réseau Telegram (#62, #63)`.
