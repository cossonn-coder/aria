# Tronçon 02 — run live (Nico)

## Préparation

1. `sudo systemctl restart aria.service`
2. Dans un autre terminal : `sudo journalctl -u aria -f -o cat`

## Messages Telegram

1. `salut` (1er message après redémarrage).
   - pas de ⏳ ;
2. Une partie : « Message 5 » de `docs/sprint29/run_live_11_parties.txt` (AaronDias16).
   - « écrit… » puis un seul ⏳ (vers 20 s), puis images + texte comme avant.
3. Après la réponse, `salut`.
   - journalctl : `[LLM] provider groq skipped (payload … chars > 12000)` (et groq_2, groq_3),
     **aucune** ligne `413` ;
   - DeepSeek répond ; pas de ⏳ ;
4. `tu te souviens de la partie que je viens de t'envoyer ?`
   - mêmes attentes que 3 ; réponse qui cite la partie (l'historique complet est conservé).

## Critère de succès

Aucun 413 Groq sur les messages 3 et 4, aucun ⏳ sur les messages 1, 3 et 4, un ⏳ sur la
partie. Noter la durée réception → `pipeline done` des messages 3 et 4 (attendu < 10 s).
