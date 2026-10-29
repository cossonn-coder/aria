# Sprint 40 — tronçon 01 : socle des métacommandes, filtre utilisateur, /help, /reboot, /board, /again

Lire d'abord `CLAUDE.md`, `docs/sprint40/00_etat.md`, `docs/sprint40/audit_metacommandes.md`.

## Objectif

Le bot ne répond qu'à Nico, et reconnaît ses premières métacommandes : `/help`, `/reboot`,
`/board`, `/again`.

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `interfaces/meta_commands.py` (nouveau) | Textes des commandes (fonctions pures quand c'est possible) et la liste `COMMANDS` (nom → description courte) qui sert à `/help` et à `set_my_commands`. Les tronçons 02-03 y ajouteront leurs commandes. |
| `interfaces/telegram_interface.py` | Filtre utilisateur, `CommandHandler`s, `post_init`, `last_reply`, demande de redémarrage |
| `bot.py` | Code de sortie 1 si redémarrage demandé |
| `config.py` | `board_url` (env `BOARD_URL`, défaut `http://192.168.1.124:5002`), section « Coach d'échecs » à côté de `board_port` |
| `tests/interfaces/test_telegram_interface.py`, `tests/test_bot.py`, nouveau `tests/interfaces/test_meta_commands.py` | Cas nominaux |

## Comportement attendu

1. **Filtre utilisateur** : `filters.User(user_id=config.allowed_user_id)` combiné aux deux
   `MessageHandler` existants (texte, photo) et à tous les `CommandHandler`. Un autre compte :
   aucune réponse, aucun appel kernel. `submit_text` (échiquier) inchangé.
2. **`CommandHandler` par commande** (handlers minces dans `TelegramInterface`, texte bâti par
   `meta_commands`). Les commandes ne passent **pas** par le kernel et ne sont **pas** écrites
   dans l'historique de conversation. Une ligne de log par commande : `meta_command name=<nom>`.
   Réponses envoyées par `self.send` (découpage 4096 déjà géré).
3. **`/help`** : une ligne par commande de `COMMANDS` (`/nom — description`).
4. **`post_init`** (`_remember_loop`, ou une fonction qui l'appelle) :
   - `set_my_commands` avec `COMMANDS` (auto-complétion Telegram) ;
   - si le fichier marqueur `~/.aria/reboot_pending` existe : envoyer « ✅ De retour. » à
     `config.allowed_user_id`, puis supprimer le marqueur. Log `meta_reboot back`.
5. **`/reboot`** : répond « 🔄 Redémarrage… (≈ 15 s) », écrit le marqueur, pose
   `self.restart_requested = True` (initialisé à `False` dans `__init__`), appelle
   `self.app.stop_running()`. Log `meta_reboot requested`.
   `bot.py` : après `telegram.start()`, `os._exit(1 if telegram.restart_requested else 0)`.
   systemd (`Restart=on-failure`) relance. PTB confirme les updates à l'arrêt (audit §2) :
   pas de boucle.
6. **`/board`** : renvoie `config.board_url`.
7. **`/again`** : renvoie la dernière réponse **du kernel** livrée à ce chat. `send()` pose
   `self.last_reply[chat_id] = message` après une livraison réussie (dict ou str, renvoyé tel
   quel par `send`). Les réponses aux métacommandes passent par `_deliver` directement ou par un
   chemin qui ne touche pas `last_reply` — au choix de l'implémentation, mais `/again` ne doit
   jamais renvoyer une sortie de commande. Rien en mémoire → « Rien à renvoyer. »

## Tests (cas nominal)

- Un message d'un autre user_id → kernel non appelé.
- `/help` contient chaque commande de `COMMANDS`.
- `/reboot` → marqueur écrit, `restart_requested` vrai, `stop_running` appelé (app factice).
- `bot.main` → `os._exit(1)` quand `restart_requested`, `0` sinon (adapter `tests/test_bot.py`).
- `post_init` avec marqueur → message « De retour » envoyé, marqueur supprimé.
- `/again` après une réponse kernel → même réponse renvoyée.
Chemin du marqueur surchargeable en test (constante module monkeypatchée).

## Hors scope

- Commandes des tronçons 02-03 (`/status`, `/logs`, `/errors`, `/llm`, `/intents`, `/parties`,
  `/oublie`). `/update` : retiré (décision Nico).
- Toucher `aria.service`, sudo, `core/kernel.py`.

## Critère de fin

`pytest tests/ -q` vert ; `grep -n "filters.User" interfaces/telegram_interface.py` couvre texte,
photo et commandes.
