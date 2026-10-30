# Sprint 43 — tronçon 04 : réparation du palace + run live (exécuté par Nico)

Prérequis : tronçons 01-03 commités, `pytest tests/ -q` vert, correctif du fork présent dans
`~/Nextcloud/projects/mempalace-fork` (commit « fix: avoid false HNSW metadata quarantine » en tête
de `git -C ~/Nextcloud/projects/mempalace-fork log -1 --oneline`). Journal :
`sudo journalctl -u aria -f -o cat`.

## Étape 0 — réparation du palace (une fois)

Pourquoi : depuis le 2026-10-23, environ 510 vecteurs sont absents de l'index HNSW
(`docs/sprint43/audit_quarantaine_hnsw.md`). `migrate_embedder.py` en mpnet→mpnet les
ré-encode depuis sqlite (testé sur copie : 690/690, ~4 min). Ordre impératif : correctif du fork
(tronçon 03) **avant** la réparation.

Commandes d'une ligne, dans l'ordre : `docs/sprint43/run_live/reparation.txt`.
Attendu : log final `✓ Migration réussie … | N entrées | dim 768 → 768` (N ≥ 690), puis au
redémarrage aucune ligne `Quarantined invalid HNSW metadata` (une ligne `.drift-*` sur l'ancien
segment est possible et sans effet).

Fichier à envoyer ensuite : `docs/sprint43/run_live/inventaire.txt` (180 cartons ; réponses
attendues : guirlandes de Noël = carton 115, perceuse sans fil = carton 162, luge = carton 173).
Messages copiables : `docs/sprint43/run_live/messages.txt`.

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
| 9 | `sudo systemctl restart aria.service`, puis `/oublie`, puis le message de l'étape 3 | même réponse qu'à l'étape 3 : la mémoire survit au redémarrage |

## Critère de succès

Étapes 0-6 et 9 conformes ; dans le journal, aucune trace `ERROR`, aucune ligne
`Quarantined invalid HNSW metadata`, aucune ligne `retrieve_memories error`. Étape 4 : une réponse
qui invente un numéro de carton au lieu de proposer la relecture est un échec de la consigne (à
noter, ajustable). Étapes 7-8 : constat, non bloquant.

Hors portée du run live : la non-récidive de la quarantaine après la prochaine persistance de
l'index (~1 000 écritures). Elle est vérifiée sur copie (audit §3, E1-E3) et par les tests du fork.
