# Tronçon 02 — run live (Nico)

Messages à copier : `docs/sprint32/run_live_messages.txt`.

## Préparation

1. `sudo systemctl restart aria.service`
2. Dans un autre terminal : `sudo journalctl -u aria -f -o cat`

## Messages Telegram

1. Message 1 du fichier : la partie AaronDias16.
   - analyse comme avant (images + texte).
2. Après la réponse, `salut`.
   - réponse de salutation normale, **pas** de « Prochaine action : … » ;
   - journalctl : **aucune** ligne `payload 3xx xxx chars` ni `payload 1xx xxx chars` ;
     un seul appel de réponse (`deepseek` ou `groq` … `a répondu.`) après le classifier.
3. `ok merci pour les tomates cerises`.
   - pas de « Prochaine action : … ».

## Critère de succès

Aucun « Prochaine action » sur les messages 2 et 3 ; sur le `salut`, plus de double appel
DeepSeek de 319 000 / 161 000 car. Noter la durée réception → `pipeline done` du `salut`
(sprint 31 : 13 s).
