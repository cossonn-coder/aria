# Audit sprint 21 — robustesse réseau Telegram (#62, #63)

Date : 2026-10-15. Code au commit `2b34f3b` (tag `sprint-20`).
python-telegram-bot **22.7** (venv).

## 1. Code concerné (intégral)

Seul fichier : `interfaces/telegram_interface.py` (163 lignes). Appelé par
`bot.py` (`TelegramInterface(kernel, token).start()`). Aucun test existant
sur ce module (`grep -rn telegram_interface tests/` → vide).

Points clés :

- `start()` l.40-53 : `ApplicationBuilder().token(...).build()`, deux
  `MessageHandler` (texte, photo), puis `self.app.run_polling()` **sans
  argument** → `bootstrap_retries=0` (défaut PTB 22.7, vérifié par
  `inspect.signature`), timeouts HTTPXRequest par défaut (connect 5 s,
  read 5 s, write 5 s, media_write 20 s).
- Aucun `add_error_handler`.
- `_handle_message` / `_handle_photo` : lock par user, `kernel.handle_event`,
  puis `await self.send(chat_id, result)` hors lock.
- `send()` l.115-163 : appels directs `bot.send_photo` / `bot.send_message`,
  aucune gestion d'erreur réseau.
- Aucun log à la réception d'un update (ni `update_id`, ni `message_id`).

## 2. #62 — timeouts réseau

### 2.a Crash au démarrage (constaté 2026-10-15 23:15:12)

```
23:15:07 [INFO] __main__ — Telegram interface prête
23:15:12 [ERROR] telegram.ext — Network Retry Loop (Bootstrap Initialize Application):
         Timed out: Timed out. Failed run number 0 of 0. Aborting.
  ... bot.initialize() → get_me() → httpx.ConnectTimeout → telegram.error.TimedOut
```

Chaîne : `run_polling()` → `Application.initialize()` → `bot.get_me()` →
ConnectTimeout (5 s). Avec `bootstrap_retries=0`, PTB abandonne au premier
échec → exception → process mort → systemd (`Restart=on-failure`,
`RestartSec=10`) relance : nouveau PID 241051 à 23:15:47. Coût : ~35 s
d'indisponibilité [n=1] + ~12 s de rechargement du kernel.

Cause : **`bootstrap_retries=0`**. Paramètre PTB prévu pour ça
(`-1` = réessais infinis avec backoff interne).

### 2.b Réponse perdue à l'envoi (constaté 23:17:33 → 23:17:38)

```
23:17:33 [INFO] llm_router — pipeline done → 208 chars      (« il fait beau »)
23:17:38 [ERROR] telegram.ext.Application — No error handlers are registered, logging exception.
         ... httpx.ConnectTimeout → telegram.error.TimedOut
```

`send()` → `send_message` → ConnectTimeout 5 s → exception remonte du
handler → PTB la logue faute d'error handler → réponse jamais envoyée.
Le pipeline a déjà écrit en mémoire (`conversation_write OK`) : ARIA
« croit » avoir répondu, l'utilisateur n'a rien reçu.

### 2.c Bruit nocturne (même cause : pas d'error handler)

`journalctl` depuis le 2026-10-01 : `No error handlers are registered` à
~03:11 les 03, 04, 08, 09, 15 octobre, `telegram.error.NetworkError: Bad
Gateway`. Ce sont des erreurs de `getUpdates` (maintenance Telegram) ; PTB
reprend seul le polling, mais logue une trace complète en ERROR. Pas de
perte fonctionnelle.

### 2.d Réseau de la VM (hypothèse, hors code)

`api.telegram.org` résout en IPv4 et IPv6 ; depuis la VM, IPv4 connecte en
0,04 s, **IPv6 échoue** (curl -6 : FAIL). anyio fait du happy-eyeballs, donc
l'IPv6 cassé ne devrait pas suffire à expliquer un ConnectTimeout de 5 s.
Non établi ; noté comme piste si les timeouts persistent après le sprint.

## 3. #63 — photo analysée deux fois (23:16:01 / 23:16:18)

```
23:15:58 Telegram interface prête          (PID 241051, après le crash)
23:16:01 [VISION] deepseek a répondu.
23:16:10 image_write OK / 23:16:16 conversation_write OK
23:16:18 [VISION] deepseek a répondu.      ← 2e traitement
23:16:21 image_write OK / 23:16:26 conversation_write OK
```

Faits :
- Un seul fichier dans `received_images/` pour cette période
  (`AgACAgQAAxkBAAIDimrQ…jpg`, mtime 23:16:16) : les deux traitements ont
  téléchargé le **même `file_id`**, le 2e a écrasé le 1er. Indice d'un même
  message Telegram traité deux fois, sans le prouver (un renvoi depuis le
  cache client peut réutiliser le fichier).
- Le 1er process (240276) est mort dans `get_me`, avant tout `getUpdates` :
  il n'a pas consommé l'update.
- Les deux traitements sont séquentiels (lock par user) dans le même
  process : les deux updates étaient en file d'attente côté Telegram au
  démarrage.
- Aucun log de réception → impossible de trancher entre (a) même
  `update_id` livré deux fois, (b) deux messages distincts (double envoi
  client pendant l'indisponibilité, réseau instable).

Conclusion : cause non établissable sur l'existant. Il manque un log de
réception (`update_id`, `message_id`). Une déduplication par `update_id`
ne servirait que dans le cas (a) ; sans savoir lequel, elle est spéculative.

## 4. Règles d'architecture

Tout se passe dans l'interface : aucune écriture/lecture mémoire, kernel
inchangé, routers inchangés. Pas de palace prod touché → calibrage faible.

## 5. Dettes adjacentes constatées (hors scope)

- `aria.service` du repo pointe `/home/nico/projects/aria` alors que le
  service tourne depuis `~/Nextcloud/projects/aria` (traceback). Le fichier
  versionné n'est pas celui installé.
- `send()` découpe à 4096 caractères au milieu des mots alors que le
  commentaire l.156 dit l'inverse.
