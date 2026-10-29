# Sprint 40 — audit des métacommandes Telegram (#131)

Relevé du 2026-10-29 sur `main` (`0083c63`). Commandes demandées par Nico : toutes celles
proposées à la clôture 39 — `/help`, `/reboot`, `/update`, `/status`, `/logs`, `/errors`,
`/llm`, `/board`, `/again`, `/intents`, `/parties`, `/oublie`.

## 1. Réception Telegram

- `interfaces/telegram_interface.py:76-90` (`start`) : deux handlers seulement,
  `MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message)` et
  `MessageHandler(filters.PHOTO, _handle_photo)`, plus `add_error_handler(_on_error)`.
  Aucun `CommandHandler` : tout `/xxx` est ignoré sans réponse.
- `post_init(self._remember_loop)` : seul crochet de démarrage, mémorise la boucle PTB.
  C'est l'endroit naturel pour `set_my_commands` et le message « de retour ».
- **Aucun filtre utilisateur** : `config.allowed_user_id` (`ALLOWED_USER_ID`, `.env`) n'est lu
  que par `submit_text` (chat de destination de l'échiquier). N'importe quel compte Telegram
  qui trouve le bot peut lui parler (LLM, écriture palace). Pour les métacommandes, un filtre
  `filters.User(user_id=config.allowed_user_id)` est indispensable (`/reboot`).
- `self.undelivered` (dernière réponse **non livrée** par chat_id, RAM) : existe ; rien ne garde
  la dernière réponse **livrée** → `/again` demande un `self.last_reply[chat_id]` posé dans `send`.
- `send(chat_id, message)` découpe à 4096 car. : les sorties longues (`/logs`) passent.

## 2. Arrêt et redémarrage

- `bot.py` : `telegram.start()` (bloquant, `run_polling(bootstrap_retries=-1)`), puis
  `logging.shutdown()` et `os._exit(0)` (#99, sprint 29).
- `aria.service` installé : `Restart=on-failure`, `RestartSec=10`, `User=nico`.
  → un code de sortie ≠ 0 suffit à faire relancer le service par systemd, **sans sudo**.
  `sudo -n` n'est NOPASSWD que pour `groq-bot` / `groq-watcher`.
- PTB 22.7 : `Application.stop_running()` arrête `run_polling` ; à l'arrêt, `Updater` appelle
  `_get_updates_cleanup` (`telegram/ext/_updater.py:395`) qui confirme les updates déjà lus →
  le `/reboot` n'est pas relivré au redémarrage (pas de boucle de reboot).
- Un traitement en cours (`asyncio.to_thread`) est tué par `os._exit` : la réponse en cours est
  perdue. Accepté (outil perso).

## 3. Mise à jour du code (`/update`)

- `origin` = `git@github.com:cossonn-coder/aria.git`. Le dépôt de prod **est** le dépôt de
  travail de Claude Code : le code arrive déjà sur disque par les commits locaux de
  `/sprint-auto`. `git pull` n'apporte quelque chose que si du code est poussé d'ailleurs.
- Risque : code cassé tiré puis reboot → crash au démarrage, relance toutes les 10 s, plus de
  Telegram pour réparer.

## 4. Lectures pour `/status`, `/parties`, `/intents`, `/llm`, `/logs`, `/errors`

- Palace : une seule collection chromadb sous `~/.mempalace/palace` ; les couches sont des
  valeurs de `wing` en métadonnée. `memory/mempalace_store.get_by_metadata(path, where, include)`
  sait compter par wing (`include=[]`). Règle 2 : la lecture passe par `MempalaceBridge`
  → nouvelle méthode de comptage à ajouter.
- Quarantaines : dossiers `*.drift-*` / `*.corrupt-*` à côté de la collection
  (relevé : un `.drift-20261029-082040`, un `.drift-20261023-…`, un `.corrupt-20261023-…`).
- `MempalaceBridge.load_chess_games()` (`mempalace_bridge.py:274`) : fiches triées par timestamp,
  métadonnées = résumé `chess_coach/summary.summarize` (`date`, `nico_color`, `opponent`,
  `elo_nico`, `elo_opponent`, `result`, `outcome`, `opening`, `eco`, `n_plies`…, plus
  la précision si présente dans le résumé).
- Le kernel (`core/kernel.py:120-150`) construit `LLMRouter`, `IntentEngine`, `MempalaceBridge`
  en **variables locales** : l'interface n'y a pas accès. Une instance `MempalaceBridge`
  dédiée (même construction : `store=search`, `get_by_metadata=get_by_metadata`) est sans état.
- Intents : `IntentEngine` les tient en RAM et les persiste à chaque `save` dans
  `~/.aria/intents.json` (`intent/intent_store.py`, champs `name`, `status`, `next_action`) :
  lecture fichier possible sans toucher l'engine.
- LLM : `LLMRouter._negative_cache` (RAM, inaccessible) ; mais le journal porte
  `[LLM] <provider> (<modèle>) a répondu.` et `[LLM] provider X skipped (cached 429 | 413 | payload)`
  (`llm/llm_router.py:232-242, 370, 413`) → `/llm` lisible depuis le journal.
- Journal : `journalctl -u aria -n N -o cat --no-pager` marche en `nico` sans sudo (vérifié).
  Le logger écrit sur stdout → priorité journald uniforme ; filtrer WARNING / ERROR / Traceback
  par texte, pas par `-p`.
- Échiquier : écoute `0.0.0.0:5002` (`config.board_port`) ; URL utilisée par Nico
  `http://192.168.1.124:5002` (docs sprint 35) — l'IP n'est nulle part dans la config.

## 5. `/oublie` (historique de conversation)

- Écriture : `memory/writer.write_conversation_turn` (wing `aria_conversation`, room = chat_id,
  type `conversation_turn`, role `user|assistant` validé).
- Lecture : `MempalaceBridge.load_conversation_history(key, n)` (filtre wing + room, tri par
  timestamp, n derniers), appelée par `LLMExecutionRouter` (`execution/routers/llm_router.py:156-171`)
  avec `n = max_history_turns * 2`.
- `memory/writer.py` n'a **aucune** fonction de suppression. Deux voies :
  (a) supprimer physiquement les tours (nouvelle fonction writer, `col.delete`) : irréversible,
  et la suppression chromadb touche l'index HNSW (cf. #105) ;
  (b) écrire un marqueur `conversation_reset` dans la room et faire ignorer par
  `load_conversation_history` tout ce qui le précède : réversible, aucune suppression.
- Dans les deux cas : **palace prod touché**. Les souvenirs épisodiques (`write_interaction`)
  ne sont pas concernés : `/oublie` vide le fil de conversation, pas la mémoire.

## 6. Règles d'architecture

- Métacommandes = pilotage du processus et consultation, pas de cognition : hors kernel
  (pas de classify / dispatch), pas de router appelé (« ne pas bypasser le kernel pour appeler
  un router » respecté), pas d'écriture conversationnelle des commandes elles-mêmes.
- Lectures palace via `MempalaceBridge` (règle 2) ; seule écriture éventuelle = `/oublie`
  via `memory/writer.py` (règle 1).
