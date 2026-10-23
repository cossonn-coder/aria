# Tronçon 02 — run live (Nico)

Messages à copier : `docs/sprint33/run_live_messages.txt`.

## Préparation

1. `sudo systemctl restart aria.service`
2. Dans un autre terminal : `sudo journalctl -u aria -f -o cat`

## Messages Telegram

1. Message 1 du fichier : la partie AaronDias16.
   - analyse comme avant (images + texte) ; `conversation_history SKIPPED reason=skip_history`.
2. Après la réponse, `salut`.
   - journalctl : `conversation_history loaded … chars=` ≤ 6 000 ;
   - **aucune** ligne `provider groq skipped (payload …)` ;
   - la réponse vient de Groq : `[LLM] groq (…) a répondu.` après le classifier, sans 413.
3. `pourquoi mon 12e coup était une erreur ?`
   - réponse sur la partie AaronDias16 (12…dxe6), cohérente avec l'analyse du message 1.

## Critère de succès

Sur le `salut`, Groq répond (plus de saut pour payload), `chars=` ≤ 6 000. La question de
suivi reste sur la bonne partie et ne contredit pas l'analyse. Noter la durée réception →
`pipeline done` du `salut` (sprint 32 : 6 s).
