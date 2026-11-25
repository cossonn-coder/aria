# Sprint 67 — tronçon 01 : recevoir et enregistrer les retours 👍 / 😢

À lire avant : `CLAUDE.md`, `docs/sprint67/00_etat.md` (décisions 1, 2, 6),
`docs/sprint67/audit_retroaction.md` (constats C1 à C6).

## Objectif

Chaque message qu'ARIA envoie sur Telegram est noté dans le palace (wing `aria_feedback`).
Une réaction de Nico (👍, 😢, ou toute autre) sur ce message met la fiche à jour. Une
réponse Telegram (« Répondre ») à un message d'ARIA qui commence par 👍 ou 😢 enregistre
réaction + commentaire.

## Fichiers à toucher (vérifiés au code)

### 1. `memory/writer.py` — deux fonctions (règle 1 : seul point d'écriture)

```python
def write_sent_message(chat_id: int, message_id: int, text: str, kind: str, request: str) -> None
def update_message_feedback(chat_id: int, message_id: int, reaction: str, comment: str | None = None) -> None
```

- `write_sent_message` : `upsert`, doc_id déterministe `f"tg_{chat_id}_{message_id}"`,
  document = `text` (ou `"(photo sans légende)"` si vide). Métadonnées :
  `chat_id`, `message_id`, `kind` (`"text"` ou `"photo"`), `request` (demande d'origine,
  `""` si inconnue), `reaction` = `""`, `comment` = `""`, `timestamp` = `_now_iso()`,
  puis structurels **après** tout le reste : `wing="aria_feedback"`, `room=str(chat_id)`,
  `type="sent_message"`. `_validate(meta)`. Même style que `write_consigne`.
- `update_message_feedback` : `col.update(ids=[doc_id], metadatas=[{...}])` avec
  `reaction`, `reacted_at` = `_now_iso()`, et `comment` seulement si non `None`.
  Même style que `update_chess_game_minis` (l. 195). Un message inconnu (envoyé avant le
  sprint) : on ne vérifie rien, chromadb ignore l'id absent.

### 2. `memory/mempalace_bridge.py`

- `load_feedback(self, since: str | None = None) -> list[dict]` : lecture non vectorielle
  par filtre `{"$and": [{"wing": "aria_feedback"}, {"type": "sent_message"}]}`, comme
  `load_consignes` (l. 357) — même garde `RuntimeError` si `get_by_metadata` absent.
  Retourne `[{**metadata, "id": doc_id, "text": document}]` trié par `timestamp`
  croissant ; si `since` (ISO), garde ceux dont `timestamp >= since` **ou**
  `reacted_at >= since` (un vieux message réagi récemment compte comme nouveau).
- `count_by_wing` (l. 444) : ajouter `"aria_feedback"` au tuple des wings (l. 462), pour
  que `/status` l'affiche (l'affichage itère déjà le dict, `meta_commands.py:495`).

### 3. `interfaces/telegram_interface.py`

a. **Réception des réactions** : `self.app.run_polling(bootstrap_retries=-1,
   allowed_updates=Update.ALL_TYPES)` (l. 149). Dans `_add_handlers`, ajouter
   `MessageReactionHandler(self._handle_reaction, user_id=config.allowed_user_id)`
   (import depuis `telegram.ext` ; PTB 22.7, signature vérifiée).

b. **`_handle_reaction`** : lit `update.message_reaction` (`chat.id`, `message_id`,
   `new_reaction`). Réaction = `new_reaction[-1].emoji` si `new_reaction` non vide et de
   type emoji (`ReactionTypeEmoji`), sinon `""` (retrait, ou emoji personnalisé). Appelle
   `update_message_feedback` via `asyncio.to_thread`. Log
   `log.info("feedback_reaction chat_id=%s message_id=%s reaction=%s", …)`. **Aucune**
   réponse Telegram.

c. **Noter chaque envoi** : dans `_send_with_retry` (l. 587), quand `make_call()` rend un
   message (`return await make_call()` → garder le résultat), si ce résultat n'est pas
   `None` : `write_sent_message(chat_id, msg.message_id, msg.text or msg.caption or "",
   "photo" if msg.photo else "text", request)` via `asyncio.to_thread`, puis le
   renvoyer. Les mocks de test rendent souvent `None` : dans ce cas rien n'est noté.
   Ne pas toucher `_notice_after_delay` ni `_post_init` (exclus, décision 2).

d. **Demande d'origine** (`request`) : un dict `self.current_request = {}` par `chat_id`,
   posé à l'entrée de la prise en charge :
   - `_process_text` : le texte (couvre texte, PGN document, `submit_text` de l'échiquier) ;
   - `_handle_photo` : `update.message.caption or "(photo)"` ;
   - `_handle_document` (hors `.pgn`, déjà couvert par `_process_text`) :
     `f"(fichier {document.file_name}) {caption or ''}".strip()` ;
   - chaque `_cmd_<nom>` : plus simple = dans un seul endroit commun si possible ; sinon
     `update.message.text`. Au choix le plus simple, sans refactorer les commandes.
   `_send_with_retry` lit `self.current_request.get(chat_id, "")`. Un décalage rare entre
   deux messages très rapprochés est accepté (mono-utilisateur).

e. **Commentaire par réponse** (décision 6) : au début de `_handle_message`, **avant** la
   logique des fragments PGN : si `update.message.reply_to_message` existe, vient du bot
   (`reply_to_message.from_user.id == context.bot.id`) et que le texte commence par
   `👍` ou `😢` → `update_message_feedback(chat_id, reply_to_message.message_id,
   emoji, comment=reste_du_texte.strip())`, log `feedback_comment …`, puis accusé
   `"📝 Retour noté."` envoyé par `self.app.bot.send_message` **direct** (pas
   `_deliver` : l'accusé n'est pas un message à juger), et `return`. Sinon, chemin
   actuel inchangé (une réponse sans emoji en tête part au kernel comme aujourd'hui).

## Tests à ajouter (cas nominal)

**Piège** : avec (c), tous les tests existants de `tests/interfaces/test_telegram_interface.py`
qui envoient un message appelleraient le vrai writer s'ils reçoivent un `Message`. Ajouter
dans ce fichier une fixture `autouse` qui patche
`interfaces.telegram_interface.write_sent_message` et `…update_message_feedback`
(`MagicMock`). Jamais d'écriture dans le palace prod depuis les tests.

- writer (`tests/memory/test_writer.py`, fixture `fake_col` existante) : `write_sent_message`
  → id `tg_42_7`, wing `aria_feedback`, type `sent_message`, `reaction == ""` ;
  `update_message_feedback` → `col.update` avec `reaction` et `comment`.
- interface : un envoi texte qui rend un faux message (`message_id=7`, `text="ok"`,
  `photo=None`) appelle `write_sent_message(42, 7, "ok", "text", <demande>)` ;
  `_handle_reaction` avec `new_reaction=[ReactionTypeEmoji("😢")]` appelle
  `update_message_feedback(42, 7, "😢")` ; une réponse « 😢 trop long » à un message du
  bot appelle `update_message_feedback(…, "😢", comment="trop long")` et **pas** le kernel.
- bridge : `load_feedback(since=…)` filtre et trie (fake `get_by_metadata`).

## Hors scope (ne PAS faire)

- Pas de rattachement aux tours `aria_conversation` ni aux fiches d'échecs.
- Ne pas écrire dans `aria_episodic`.
- Pas de réponse à une réaction emoji ; pas de commande `/retours`.
- Ne pas modifier `write_conversation_turn`, les routers, le kernel.
- Pas de traitement d'une réponse sans emoji en tête (reste au kernel).

## Critère de fin

`pytest tests/ -q` vert ; les tests ci-dessus présents ; `grep -n allowed_updates
interfaces/telegram_interface.py` montre `Update.ALL_TYPES`.
