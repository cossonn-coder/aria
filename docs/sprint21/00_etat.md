# Sprint 21 — état de conception

**Phase** : CLOS (2026-10-16). Run live 02 conforme (A, B, C).
**Branche** : `feat/sprint21-telegram-reseau` (créée depuis `main` @ `2b34f3b`).

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_telegram_robustesse.md` — bootstrap_retries, retry send, error handler, log réception | ✅ `7c2c072` (262 verts) |
| 02 | `02_run_live.md` — coupure iptables (Nico) | ✅ conforme (A, B, C) |

## Décisions arrêtées

- Q1 — Cible : #62 + #63 robustesse Telegram (constaté en run live, périmètre = `interfaces/telegram_interface.py`).

- Q2 — Démarrage : `run_polling(bootstrap_retries=-1)` (retries infinis PTB au lieu du crash).
- Q3 — Envoi : retry sur `NetworkError` dans `send()` (3 tentatives, attentes 2 s puis 4 s ; doublon possible accepté) + `add_error_handler` qui logue une ligne WARNING.
- Q4 — #63 : log INFO de réception (`update_id`, `message_id`), pas de dédup ; #63 reste « instrumentée, à confirmer ».
- Découpage envisagé : 1 tronçon de code (Q2-Q4, test nominal du retry de `send()`) + run live (coupure `iptables`).

## Questions ouvertes

(aucune)

## Dettes

- Fermée : #62 (run live 02 conforme).
- Ouverte : #63 (instrumentée, « à confirmer » — ne se reproduit pas sur commande).
- Nouvelles, hors scope : `aria.service` versionné pointe `/home/nico/projects/aria` (installé : Nextcloud) ; découpage 4096 de `send()` coupe au milieu des mots (commentaire faux) ; IPv6 VM → Telegram injoignable (piste si timeouts persistent).

## Run live 02 (2026-10-16)

Scénarios A (démarrage sans réseau), B (envoi pendant coupure), C (log
de réception photo) conformes selon Nico. #62 fermée.

## §REPRISE

Sprint clos, tag `sprint-21`. Suite : `docs/sprint22/context_kickoff_sprint_22.md`,
`/conception sprint 22`.
