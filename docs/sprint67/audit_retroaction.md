# Sprint 67 — audit : boucle de rétroaction 👍 / 😢 (dette 66-3)

Date : 2026-11-25, sur `main` au tag `sprint-66` (927389f).

## Besoin (Nico, 2026-11-25)

Réagir 👍 (j'aime) / 😢 (je n'aime pas) sur **chaque** message Telegram d'ARIA (échecs ou
non ; miniature = son Pourquoi, texte final = bilan). Retours positif / aucun / négatif
enregistrés dans le palace, traités ensemble en conception. But final (hors sprint) :
ARIA s'auto-améliore.

## Constats au code

### C1 — Les réactions ne sont pas reçues aujourd'hui

`interfaces/telegram_interface.py:149` :

```python
self.app.run_polling(bootstrap_retries=-1)
```

Sans `allowed_updates`, Telegram n'envoie pas les updates `message_reaction` (doc Bot API et
PTB `telegram/_update.py:118` : il faut lister explicitement `MESSAGE_REACTION`). Aucun
handler de réaction n'existe (`grep reaction` : zéro occurrence hors venv).

PTB installé : 22.7, `telegram.ext.MessageReactionHandler` disponible.

**Risque live** : la doc Bot API dit « le bot doit être administrateur du chat » ; en chat
privé, le bot est l'interlocuteur, les réactions y sont réputées reçues. Non vérifiable sur
la VM (le service tient le polling) : c'est la première chose que le run live démontre.

### C2 — Une réaction ne porte que l'identifiant du message

`MessageReactionUpdated` : `chat`, `message_id`, `user`, `date`, `old_reaction`,
`new_reaction`. Ni texte, ni demande d'origine. Pour savoir **sur quoi** porte le 👍 / 😢,
il faut avoir noté à l'envoi : `message_id` → texte envoyé (+ demande qui l'a provoqué).

### C3 — Les envois passent presque tous par `_send_with_retry`

`_send_with_retry(chat_id, make_call)` (l. 587) renvoie le `Message` de Telegram (donc
`message_id`, `text` ou `caption`). Y passent :

| Chemin | Lignes | Contenu |
|---|---|---|
| `_deliver` texte | 728-732 | réponse kernel, métacommandes, découpe par 4 096 car. |
| `_deliver` images_text | 676-685 | photos des miniatures, légende = Pourquoi (≤ 1 024 car.) |
| `_deliver` image | 701-708 | image générée + légende |
| `_deliver_html` | 642-648 | `/parties`, `/ouvertures <x>` |
| `_cmd_board` | 399-402 | lien de l'échiquier |

N'y passent **pas** : `_notice_after_delay` (« ⏳ Je travaille dessus », l. 579),
`_post_init` (« je reviens », l. 187), l'indicateur « écrit… ». Signaux techniques, rien à
juger.

`_send_with_retry` ne connaît pas la demande d'origine. Elle est connue dans
`_process_text` (texte), `_handle_photo` (légende), `_handle_document` (nom + légende), et
dans chaque `_cmd_<nom>` (la commande elle-même).

### C4 — Les tours de conversation ne portent pas l'id Telegram

`write_conversation_turn` (writer l. 324) est appelé par `llm_router.py:421-422` et
`image_router.py:111-112, 228-229` **avant** l'envoi : `message_id` inconnu à ce moment,
`doc_id = uuid4()`. Une réponse découpée en 2 messages = 1 tour, et les photos des
miniatures ne sont pas des tours. Rattacher une réaction à un tour existant serait fragile
(par horodatage) : il faut un enregistrement propre au message envoyé.

Le résultat du router ne porte pas non plus l'id de la fiche d'échecs (constat 66-3) :
inutile si le message envoyé est lui-même enregistré (texte + demande).

### C5 — Où ranger : pas dans `aria_episodic`

`aria_episodic` est lue en **similarité vectorielle** pour le contexte du LLM
(`mempalace_bridge.retrieve_memories`, l. 101-116, wing par défaut). Y mettre chaque
message envoyé polluerait la mémoire de travail d'ARIA avec ses propres réponses.
Un wing dédié (`aria_feedback`) se lit par filtre `wing + type`, comme `load_consignes`
(bridge l. 357) et `load_chess_games` (l. 325).

`/status` compte les documents par wing en dur (bridge l. 462 :
`aria_episodic, aria_semantic, aria_classifier, aria_conversation`) : un nouveau wing n'y
apparaît pas sans l'ajouter.

### C6 — Précédent d'écriture depuis l'interface

L'interface écrit déjà via `memory/writer.py` pour ses métacommandes (`write_consigne`,
`write_conversation_reset`, `update_chess_game_result`, l. 37-42). Règle 1 respectée si
l'écriture passe par une nouvelle fonction du writer (wing / room / type structurels, posés
après `extra`). Règle 5 (kernel) non concernée : la réaction ne passe pas par le kernel,
comme les métacommandes.

### C7 — Coût d'écriture

Un `upsert` par message envoyé (embedding du document par chromadb) : 1 à ~6 par réponse
[estimé, chess : photos + texte]. Un `update` de métadonnée par réaction (pas de
ré-embedding). Ordre de grandeur comparable aux 2 tours de conversation déjà écrits par
réponse.

## Conception proposée (à arbitrer)

1. `run_polling(allowed_updates=Update.ALL_TYPES, …)` + `MessageReactionHandler` filtré sur
   Nico.
2. À l'envoi, dans `_send_with_retry` : un document par message Telegram envoyé, wing
   `aria_feedback`, id déterministe `tg_<chat_id>_<message_id>`, texte = texte ou légende,
   métadonnées : `chat_id`, `message_id`, `kind` (text / photo), `request` (demande
   d'origine si connue), `reaction` = `""`, `timestamp`.
3. À la réaction : `update` de `reaction` (dernier emoji ou `""` si retirée) et
   `reacted_at` sur `tg_<chat_id>_<message_id>`. Silencieux côté Telegram.
4. Lecture : `bridge.load_feedback()` + un moyen de les traiter en conception.
