# Sprint 40 — tronçon 04 : run live des métacommandes (Nico)

1. `sudo systemctl restart aria.service`
2. `sudo journalctl -u aria -f -o cat | grep -E "meta_|Traceback|conversation_history"`

| # | Action (Telegram) | Ce qu'on doit voir |
|---|---|---|
| 1 | Taper `/` | les commandes proposées par Telegram avec leur description |
| 2 | `/help` | la liste des commandes |
| 3 | `/status` | en ligne depuis, commit `feat/sprint40…`, mémoire en Mo, entrées par wing, quarantaines |
| 4 | `/logs`, puis `/logs 5` | 30 lignes, puis 5 |
| 5 | `/errors`, `/llm` | erreurs récentes (ou « Aucune ») ; dernières lignes `[LLM]` |
| 6 | `/intents`, `/parties` | intents actifs ; 5 dernières parties |
| 7 | `/board` | lien cliquable, la page s'ouvre (réseau local) |
| 8 | `salut`, puis `/again` | la réponse à `salut` renvoyée telle quelle |
| 9 | `je m'appelle Zorglub ce soir`, `/oublie`, puis `comment je m'appelle ce soir ?` | après `/oublie` : journal `conversation_history loaded … messages=0` ; ARIA ne cite pas Zorglub par l'historique (elle peut le retrouver par un souvenir épisodique : accepté) |
| 10 | `/reboot` | « Redémarrage… », puis ≈ 15 s plus tard « ✅ De retour. » ; un seul redémarrage (pas de boucle) |
| 11 | (facultatif) depuis un autre compte Telegram, écrire au bot | aucune réponse |

Échec d'un critère → noter le scénario et ce qu'ARIA a répondu.
