# Sprint 41 — tronçon 02 : `/board` envoie un bouton Mini App

Lire d'abord `CLAUDE.md`, `docs/sprint41/00_etat.md`, `docs/sprint41/audit_board_mobile.md` (§1, §3).

## Objectif

`/board` ouvre l'échiquier **dans Telegram** (Mini App) quand l'URL configurée est en HTTPS
(Tailscale `serve`, décision D4).

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `interfaces/telegram_interface.py` | `_cmd_board` (l. ~250) ; import `InlineKeyboardButton`, `InlineKeyboardMarkup`, `WebAppInfo` depuis `telegram` (ligne 15, PTB 22.7) |
| `tests/interfaces/test_telegram_interface.py` | deux tests |

`meta_commands.board_text()` et `config.board_url` (env `BOARD_URL`) inchangés.

## Comportement attendu

- `config.board_url` commence par `https://` → un message dont le texte est l'URL, avec un
  bouton inline « ♟ Ouvrir l'échiquier » de type `web_app=WebAppInfo(url=<url>)`. Envoi par
  `self._send_with_retry(chat_id, lambda: self.app.bot.send_message(..., reply_markup=...))`
  (même chemin d'envoi que `_deliver`, ne touche pas `last_reply`).
- Sinon (http, défaut actuel `http://192.168.1.124:5002`) → comportement actuel inchangé
  (`_deliver` du texte). Raison : l'API Telegram refuse un bouton `web_app` en http.
- Log `meta_command name=board` conservé.

## Tests (cas nominal)

Sur le modèle de `test_help_command_lists_commands` (`iface.app.bot.send_message = AsyncMock()`,
`_command_update()`, `monkeypatch` de `telegram_interface.config.board_url`) :
- URL https → `reply_markup` présent, son bouton a `web_app.url == url`.
- URL http → texte = URL, pas de `reply_markup`.

## Hors scope

- `MenuButtonWebApp` (bouton de menu permanent), `/board` dans `COMMANDS` (description inchangée).
- Authentification `initData` (tailnet seul, D4).
- Page HTML (tronçon 01).

## Critère de fin

Deux tests verts, `pytest tests/ -q` vert, commit local.
