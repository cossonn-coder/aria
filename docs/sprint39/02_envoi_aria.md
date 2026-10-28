# Sprint 39 — tronçon 02 : bouton « Envoyer à ARIA » (côté serveur et Telegram)

Lire d'abord `CLAUDE.md` et `00_etat.md` (décision lot 2 #130, audit complémentaire).

## Objectif

Une requête `POST /send {pgn}` du serveur de l'échiquier fait traiter le PGN par ARIA
**exactement comme un message texte de Nico sur Telegram** : kernel, `chess_router`,
fiche `chess_game` (palace prod, via `memory/writer.py`), réponse envoyée dans le chat
de Nico. L'échiquier ne voit ni le kernel ni la mémoire : il reçoit seulement une
fonction d'envoi.

## Fichiers

- `interfaces/telegram_interface.py` : point d'entrée externe.
- `interfaces/board_interface.py` : route `/send`, fonction d'envoi injectée.
- `bot.py` : branchement.
- `tests/interfaces/test_telegram_interface.py`, `tests/interfaces/test_board_interface.py`.

## Comportement attendu

1. **`TelegramInterface`** :
   - `self.loop = None` dans `__init__` ; dans `start()`, mémoriser la boucle PTB via
     `ApplicationBuilder().token(...).post_init(<coroutine>)` (PTB 22.7 : `post_init`
     existe, vérifié) qui stocke `asyncio.get_running_loop()`.
   - `submit_text(text) -> bool`, appelable depuis un autre thread : `False` si la
     boucle n'existe pas encore ; sinon `asyncio.run_coroutine_threadsafe(<traitement>,
     self.loop)` et `True`. Ne pas attendre la fin du traitement.
   - Traitement : même séquence que `_handle_message` (l. 94) — verrou
     `user_locks[user_id]`, `Event.create(EventType.TEXT, user_id, text,
     {"chat_id": chat_id})`, `_handle_with_waiting(chat_id, event)`, puis
     `send(chat_id, result)` — avec `user_id = str(config.allowed_user_id)` et
     `chat_id = config.allowed_user_id` (chat privé : chat_id = user_id ;
     `ALLOWED_USER_ID` renseigné dans `.env`). Factoriser avec `_handle_message` si
     c'est plus simple, sans changer son comportement.
   - Log `telegram_external source=board chars=…` à la réception. Une exception du
     traitement ne doit pas disparaître en silence (le future de
     `run_coroutine_threadsafe` l'avalerait) : la journaliser (`log.exception` ou
     callback du future), une seule fois.
2. **`board_interface.py`** :
   - `make_server(port, worker, submit_text=None)` range la fonction sur le serveur ;
     `start_board_server(submit_text)` la transmet.
   - `POST /send {pgn}` : `submit_text(pgn)` vrai → 200 `{"sent": true}` ; faux ou
     absent → 503 `{"error": "ARIA pas prêt"}`. Log `board_send chars=…`.
   - Aucune lecture / écriture mémoire, aucun import kernel / router dans ce fichier.
3. **`bot.py`** : `start_board_server(telegram.submit_text)` (l'échiquier démarre
   avant `telegram.start()` : un envoi avant la boucle PTB rend 503, accepté).

## Tests (cas nominal)

- Telegram : `iface.loop` = boucle du test, `kernel.handle_event` AsyncMock rendant un
  texte, `iface.send` AsyncMock ; `submit_text("…PGN…")` appelé depuis un thread
  (`asyncio.to_thread`) → `True` ; après traitement, `handle_event` reçu avec
  `content` = le texte et `send` appelé avec `config.allowed_user_id` (monkeypatch).
  Et `submit_text` sans boucle → `False`.
- Board : `make_server(0, worker, submit_text=fake)` → `/send` 200 et `fake` reçoit le
  PGN ; sans fonction → 503.

## Hors scope

- Pas de nouvelle écriture mémoire, pas d'appel direct à `chess_router` ni au kernel
  depuis l'échiquier.
- Pas d'envoi proactif générique (#68), pas de filtrage `allowed_user_id` des messages
  entrants.
- Pas de modification de `chess_router`, du classifier, du prompt AnalystAgent.

## Critère de fin

`pytest tests/ -q` vert. Le run live (tronçon 04) valide l'arrivée sur Telegram et
`chess_game_write OK` au journal.
