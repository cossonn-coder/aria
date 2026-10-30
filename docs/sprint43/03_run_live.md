# Sprint 43 — tronçon 03 : run live (exécuté par Nico)

Prérequis : tronçons 01-02 commités, `pytest tests/ -q` vert, puis
`sudo systemctl restart aria.service`. Journal : `sudo journalctl -u aria -f -o cat`.

Fichier à envoyer : `docs/sprint43/run_live/inventaire.txt` (180 cartons, déjà créé en
conception ; réponses attendues : guirlandes de Noël = carton 115, perceuse sans fil =
carton 162, luge = carton 173). Messages copiables : `docs/sprint43/run_live/messages.txt`.

## Étapes et critères

| # | Envoi sur Telegram | Attendu |
|---|---|---|
| 1 | `inventaire.txt` sans légende | synthèse ; journal `document_write OK` |
| 2 | `/oublie` | historique coupé |
| 3 | « tu te souviens de l'inventaire que je t'ai envoyé ? » | oui, résumé fidèle depuis la fiche (pas de relecture) |
| 4 | « dans quel carton sont les guirlandes de Noël ? » | ARIA dit ne pas avoir le détail et termine par « Veux-tu que je relise « … » ? » (pas de numéro inventé) |
| 5 | « oui » | carton 115, garage, armoire métallique ; journal `doc_reread OK` |
| 6 | « relis l'inventaire, où est la perceuse ? » | carton 162, cellier ; journal `doc_reread OK` |
| 7 | une URL de page web (ex. https://fr.wikipedia.org/wiki/Paillage), puis `/oublie`, puis « que disait la page sur le paillage ? » | journal `document_write OK` à la lecture ; réponse depuis la fiche |
| 8 | « relis le document sur les impôts » (aucun document de ce sujet) | une phrase « aucun document correspondant », journal `doc_reread NOT_FOUND` |

## Critère de succès

Étapes 1-6 conformes, aucune trace `ERROR` dans le journal. Étape 4 : une réponse
qui invente un numéro de carton au lieu de proposer la relecture est un échec de la
consigne (à noter, ajustable). Étapes 7-8 : constat, non bloquant.
