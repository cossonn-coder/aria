# Sprint 18 — tronçon 03 : run live (Nico)

Pas de reset mémoire.

## Protocole

```
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

Sur Telegram :

1. `je voudrais faire un petit potager d'herbes aromatiques sur ma fenêtre`
2. `lesquelles poussent bien à l'intérieur ?`
3. `tu me disais quoi déjà sur l'emplacement ?`
4. Une photo (plante, objet, n'importe quoi), **sans légende**.
5. Une photo avec la légende `c'est quoi ?` (mode enrichi : vision puis
   chaîne REASONING).

## Critères de succès

- journalctl : pour chaque appel, `[LLM] groq (qwen/qwen3.8-27b) a répondu.`
  (ou `deepseek`/`anthropic` si groq est en 429), **aucun
  `[LLM FALLBACK] … 404`**, aucune trace de mistral/openrouter/cerebras.
- Messages 1-3 : réponses cohérentes, le message 3 rappelle le 1.
- Photo 4 : description qui correspond à la photo.
- Photo 5 : réponse à la question, log `[IMAGE ENRICHED]`.
- Latence ressentie : nettement inférieure au run sprint 17
  (environ 6-8 s perdues par appel [n=4 messages]).

À remonter : extraits journalctl et réponses Telegram.
