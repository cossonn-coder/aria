# Sprint 22 — Tronçon 03 : run live (exécuté par Nico)

Prérequis : tronçons 01 et 02 commités sur `feat/sprint22-web-search`,
`TAVILY_API_KEY=tvly-…` présent dans `.env`.

## Préparation

```
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## Scénarios (messages Telegram exacts)

| # | Message | Attendu Telegram | Attendu journalctl |
|---|---------|------------------|--------------------|
| A | `cherche sur le web le score du dernier match du Stade Malherbe Caen` | Réponse factuelle terminée par des URL | `web_search OK provider=tavily results=…` |
| B | `Qui a inventé le moteur Stirling ?` puis `source ?` | 2ᵉ réponse : sources sur le moteur Stirling (requête = sujet précédent) | 1er message : pas de `web_search` ; 2ᵉ : `web_search OK … query='…Stirling…'` |
| C | `quel temps fera-t-il demain à Caen ?` | Prévision avec source | classifier LLM → `web_search`, puis `web_search OK` |
| D | `rappelle-moi où en est mon projet potager` | Réponse mémoire habituelle | **aucune** ligne `web_search` |

## Critère de succès

A, B, D conformes. C conforme ou, si le LLM classe autrement, noté comme
calibrage de prompt (non bloquant). Toute ligne `web_search FAILED` : relever
l'erreur (format Tavily vérifié en conception, chercher ailleurs : clé, réseau).

Retour à Claude : verdicts A-D + extraits journalctl pertinents.
