# Sprint 45 — tronçon 02 : run live (exécuté par Nico)

Prérequis : tronçon 01 commité, `pytest tests/ -q` vert, `sudo systemctl restart aria.service`.
Journal : `sudo journalctl -u aria -f -o cat`.
Messages copiables (un par ligne) : `docs/sprint45/run_live/messages.txt`.
Sujet : rotation des cultures plutôt que paillage — le palace contient déjà la fiche « Paillis — Wikipédia », qui pourrait passer avant le rapport aux étapes 4-5.

| # | Envoi sur Telegram | Attendu |
|---|---|---|
| 1 | `/oublie` | historique coupé |
| 2 | « fais une recherche sur la rotation des cultures au potager » | ⏳ puis rapport en français avec URL ; journal `web_research plan queries=3..5`, `web_research pages read=…`, `document_write OK … source=recherche:…`, `web_research OK` ; **pas** de `web_search OK` |
| 3 | `/oublie` | historique coupé |
| 4 | « que disait ma recherche sur la rotation des cultures ? » | réponse fidèle au rapport ; journal `document_recall source=recherche:…` |
| 5 | « relis la recherche sur la rotation des cultures » | relecture du rapport ; journal `doc_reread OK source=recherche:…` (libellé « du fichier » accepté) |
| 6 | « quel temps demain à Caen ? » | recherche rapide (non-régression) ; journal `web_search OK` une fois, pas de `web_research` |
| 7 | « salut » | réponse normale, pas de recherche |

À relever : durée de l'étape 2 (horodatage du message → réponse).

## Critère de succès

Étapes 2 et 4 conformes ; 5-7 sans régression ; aucun `ERROR` au journal.
