# Sprint 29 — Tronçon 01 : fiabilité (erreur kernel vide, réponse perdue)

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_sprint29.md` §4-5.

## Objectif

1. Une exception levée par un router laisse une trace exploitable dans le journal.
2. Une réponse que Telegram n'a pas pu livrer après les réessais n'est plus perdue
   en silence : elle part avant la réponse suivante, avec un avertissement.

## Fichiers à toucher

### `execution/execution_dispatcher.py`
- Ajouter le logger projet (`from logger import get_logger; log = get_logger(__name__)`).
- Dans le `except Exception as e` de `dispatch` : `log.exception(...)` avec le nom du
  router, et `"error": f"{type(e).__name__}: {e}"` (le type reste visible même si
  `str(e)` est vide, cas `TimeoutError` du 21/10).

### `core/kernel.py`
- Le module n'a pas de logger : l'ajouter (convention projet).
- `_normalize` : remplacer `print(f"[KERNEL] execution error: {error}")` par
  `log.error("kernel execution error: %s", error)` (dette #71). Message utilisateur inchangé.

### `interfaces/telegram_interface.py`
- Nouvel état d'instance : réponses non livrées par `chat_id` (dict en RAM, initialisé
  dans `__init__`). Perte au redémarrage acceptée (décision Nico).
- `send()` : si l'envoi échoue définitivement (`NetworkError` remontée par
  `_send_with_retry` après la dernière tentative), journaliser en **ERROR** et mémoriser
  le `message` (la réponse du kernel, telle quelle : str ou dict) pour ce `chat_id`.
  Ne plus laisser l'exception remonter jusqu'à `_on_error` pour ce cas.
- Au `send()` suivant pour ce `chat_id` : envoyer d'abord le texte
  « ⚠️ Ma réponse précédente n'avait pas pu partir : », puis la réponse mémorisée
  (même chemin d'envoi, donc photos + texte pour `images_text`), puis la réponse
  courante. Une seule réponse en attente par chat suffit (la plus récente écrase).
- Structure suggérée : renommer le corps actuel de `send` en méthode interne
  (`_deliver`) et faire de `send` l'enveloppe (livraison de l'attente, puis de la
  réponse courante, capture de l'échec). Garder le comportement existant de
  `_deliver` à l'identique.

## Tests à ajouter (cas nominal)

- `tests/execution/` ou existant : un router qui lève `TimeoutError()` → le dispatcher
  rend `error` contenant `"TimeoutError"` et loggue la trace (`caplog`, niveau ERROR).
- `tests/interfaces/test_telegram_interface.py` : `send_message` échoue 3 fois
  (`TimedOut`), `asyncio.sleep` patché → pas d'exception ; au `send` suivant, l'ordre
  des messages envoyés est : avertissement, réponse en attente, réponse courante.

## Hors-scope (NE PAS faire)

- Pas de réessais en tâche de fond, pas de persistance disque.
- Ne pas toucher au découpage 4096 (#66), ni à l'arrêt de l'envoi texte quand une photo
  échoue (dette notée), ni au blocage de la boucle par `handle_event` (dette notée).
- Pas de `try/except` supplémentaire ailleurs.

## Critère de fin

`pytest tests/ -q` vert ; plus aucun `print(` dans `core/kernel.py`.
