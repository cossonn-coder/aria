# Sprint 44 — tronçon 02 : run live (exécuté par Nico)

Prérequis : tronçon 01 commité, `pytest tests/ -q` vert, `sudo systemctl restart aria.service`.
Journal : `sudo journalctl -u aria -f -o cat`.
Palace prod tel quel : il contient déjà la fiche « Paillis — Wikipédia » et 4 fiches
« inventaire.txt » (run live sprint 43). Messages copiables : `docs/sprint44/run_live/messages.txt`.

| # | Envoi sur Telegram | Attendu |
|---|---|---|
| 1 | `/oublie` | historique coupé |
| 2 | « que disait la page sur le paillage ? » | réponse sur le paillis depuis la fiche ; journal `document_recall source=https://fr.wikipedia.org/wiki/Paillage` |
| 3 | « relis le document sur les impôts » | une phrase « aucun document correspondant » ; journal `doc_reread NOT_FOUND` |
| 4 | « relis la page sur le paillage » | synthèse du paillis ; journal `doc_reread OK source=https://fr.wikipedia.org/wiki/Paillage` |
| 5 | « relis le document » | relecture d'un document (non-régression) ; journal `doc_reread OK` |
| 6 | « dans quel carton sont les guirlandes de Noël ? » | carton 115 ou proposition de relecture de l'inventaire (non-régression) ; journal `document_recall source=…inventaire.txt` |
| 7 | « salut » | réponse normale ; **pas** de ligne `document_recall` |

## Critère de succès

Étapes 2, 3, 4 conformes (ferment #146, #147) ; 5-7 sans régression ; aucun `ERROR` au journal.
