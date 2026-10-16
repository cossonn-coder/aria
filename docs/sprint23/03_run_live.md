# Sprint 23 — Tronçon 03 : run live (exécuté par Nico)

Prérequis : tronçons 01 et 02 commités sur `feat/sprint23-lecture-url`,
`TAVILY_API_KEY` et `DEEPSEEK_API_KEY` présents dans `.env`.

## Préparation

```
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## Scénarios (messages Telegram exacts, dans cet ordre)

Tailles mesurées en conception (`format: "text"`, 2026-10-16) : Abeille
32 428 car., Normandie 153 685 car.

| # | Message | Attendu Telegram | Attendu journalctl |
|---|---------|------------------|--------------------|
| A | `https://fr.wikipedia.org/wiki/Abeille_domestique` | Résumé de la page, URL citée, pas de proposition de suite | `url_read OK … page_chars=32428 start=0 end=32428 digest_tokens=…` ; provider DeepSeek (pas `groq`) pour la synthèse |
| B | `que dit cette page sur la reproduction ? https://fr.wikipedia.org/wiki/Abeille_domestique` | Réponse centrée sur la reproduction | `url_read OK …` |
| C | `https://fr.wikipedia.org/wiki/Normandie` | « J'ai lu les caractères 0 à ~100 000 sur 153 685 », synthèse, proposition de lire la suite | `url_read OK … start=0 end=<≤100000>` |
| D | `oui` | Synthèse de la suite (fin de la page), plus de proposition | `url_read OK … start=<end de C> end=153685` |
| E | `et la gastronomie normande, ça en parlait ?` | Réponse appuyée sur les synthèses (historique), sans relecture | **aucune** ligne `url_read` |
| F | `https://example.invalid/page` | Une phrase : page illisible | `url_read FAILED …` |
| G | `oui` | Réponse conversationnelle normale | **aucune** ligne `url_read` (CONFIRMATION) |

## Critère de succès

A, C, D, F, G conformes. B : réponse orientée par la question. E : informatif
(dépend de ce que la synthèse a retenu), non bloquant. Relever toute ligne
`url_read digest hit max_tokens` (calibrage de la taille de synthèse) et la
fin de tranche de C (doit tomber en fin de paragraphe : vérifiable dans le
log `end=`).

Retour à Claude : verdicts A-G + extraits journalctl pertinents.
