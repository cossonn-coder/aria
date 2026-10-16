# Sprint 25 — Tronçon 02 : run live (Nico)

Prérequis : tronçon 01 commité.

```
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## Message Telegram

Dans le chat habituel (historique déjà chargé, `conversation_history loaded
… messages=20`), envoyer une question conversationnelle, ex. :
`tu peux me rappeler où on en est sur docker ?`

## Attendu journalctl

- Une seule ligne `[LLM FALLBACK] groq failed: … 413 …` suivie du corps
  (`… ITPM): Limit 7000, Requested N …`).
- Lignes `groq_2` / `groq_3` : `skipped`, **aucun** `[LLM FALLBACK] groq_2 failed`
  ni `groq_3 failed`.
- `[LLM] deepseek (…) a répondu.` ~1-2 s après le 413 (contre ~4 s au run
  live 24-02).

## Critère de succès

Les trois points ci-dessus. Si Groq répond directement (pas de 413 :
historique trop léger), envoyer d'abord une ou deux questions appelant une
réponse longue, puis réessayer.
