# Tronçon 03 — run live (Nico)

Messages à copier : `docs/sprint34/run_live_messages.txt`.

## Préparation

1. `ls -la ~/.aria/intents.json` (référence : 343 805 octets au 2026-10-23).
2. `sudo systemctl restart aria.service`
3. Dans un autre terminal : `sudo journalctl -u aria -f -o cat`

## Messages Telegram

1. `salut`
   - réponse courte normale ; journalctl sans `ImportError` / `ModuleNotFoundError` /
     traceback au démarrage ni sur le message.
2. `où en est ma plantation de tomates sur le balcon ?`
   - réponse normale ; journalctl : une ligne d'intent (rattachement ou création), pas
     `intent SKIPPED reason=namer_aucun`. Si le namer répond « aucun », renvoyer un autre
     message sur un projet existant : il faut un message qui porte un intent pour que le
     fichier soit réécrit.
3. `ls -la ~/.aria/intents.json`

## Critère de succès

- Service démarré, deux réponses normales, aucune erreur d'import.
- `intents.json` < 20 Ko après le message 2 (avant : 344 Ko).
