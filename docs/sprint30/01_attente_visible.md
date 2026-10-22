# Tronçon 01 — attente visible pendant le traitement (#103) + photo en échec sautée (#104)

Lire d'abord : `CLAUDE.md`, `docs/sprint30/00_etat.md`, `docs/sprint30/audit_fiabilite_analyse.md` §#103.

## Constat

- `core/kernel.py` `AriaKernel.handle_event` est `async` mais appelle en synchrone
  `self.cognitive_engine.classify(event)` puis `self.execution_dispatcher.dispatch(exec_op)` :
  la boucle asyncio de PTB est bloquée 65-123 s par analyse de partie, rien ne peut être
  envoyé pendant ce temps.
- `interfaces/telegram_interface.py` `_deliver`, cas `images_text` : une photo dont l'envoi
  échoue définitivement (`NetworkError` après `_send_with_retry`) lève, et le texte qui suit
  n'est jamais envoyé (#104).

## Objectif

1. **Déblocage** : dans `handle_event`, `classify` et `dispatch` tournent dans un thread
   (`await asyncio.to_thread(...)`). Le reste de la séquence est inchangé (le kernel séquence,
   ne décide rien : règle 5). Le code métier n'utilise pas asyncio (vérifié au grep), aucune
   autre adaptation attendue.
2. **Signal d'attente** (décision Nico, 00_etat Q2 bis) dans `TelegramInterface`, autour de
   l'`await self.kernel.handle_event(event)` de `_handle_message` **et** `_handle_photo` :
   - indicateur natif Telegram « écrit… » : `self.app.bot.send_chat_action(chat_id=…,
     action=ChatAction.TYPING)` (`from telegram.constants import ChatAction`), renvoyé toutes
     les ~4 s tant que le traitement n'est pas fini (il s'efface seul après 5 s côté Telegram ;
     ce n'est pas un message, rien ne s'empile) ;
   - si le traitement dépasse 10 s : **un seul** message texte
     `⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes.` (constante de module) ;
     jamais répété pour le même traitement ; aucun message si la réponse arrive avant 10 s.
   - à la fin (réponse prête ou exception), la tâche d'attente est annulée avant l'envoi de
     la réponse.
   - Un échec d'envoi de l'indicateur ou du message d'attente (`TelegramError`) est journalisé
     en WARNING une ligne et n'interrompt ni l'attente ni le traitement.
   - Constantes de module pour les délais (4 s, 10 s), dans le style de `SEND_ATTEMPTS`.
3. **#104** : dans `_deliver` cas `images_text`, un envoi de photo en échec définitif
   (`NetworkError`) est journalisé en WARNING (chemin + type d'erreur) et sauté ; les photos
   suivantes puis le texte partent quand même.

Forme libre (tâche asyncio, helper privé…) tant que le comportement ci-dessus est tenu et
que le code reste simple.

## Tests (cas nominal, `pytest-asyncio` comme `tests/interfaces/test_telegram_interface.py`)

- Kernel : `handle_event` rend le même résultat qu'avant (les tests existants
  `asyncio.run(kernel.handle_event(...))` doivent rester verts) ; un test qui vérifie que
  `dispatch` s'exécute hors du thread de la boucle (ex. `threading.get_ident()` capturé dans un
  dispatcher simulé ≠ thread principal).
- Interface, traitement long simulé (kernel dont `handle_event` attend au-delà du seuil ;
  délais patchés courts pour rester rapide) : le message d'attente est envoyé **exactement une
  fois**, `send_chat_action` au moins une fois, puis la réponse.
- Interface, traitement court : aucun message d'attente.
- `images_text` avec une photo en échec définitif : le texte est quand même envoyé.

Attention : les tests existants patchent `interfaces.telegram_interface.asyncio.sleep` ;
ne pas les casser.

## Hors-scope

- Pas d'estimation calculée (nombre de coups, etc.) : texte fixe.
- Pas de changement du verrou par utilisateur, ni du découpage 4096 (#66), ni de `send()`.
- Pas de modification des routers ni du dispatcher.
- Arrêt du service pendant une analyse : il attendra la fin de l'analyse comme aujourd'hui,
  ne pas chercher à l'accélérer.

## Critère de fin

`pytest tests/ -q` vert. À valider en live (tronçon 03).
