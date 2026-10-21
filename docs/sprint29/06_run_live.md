# Sprint 29 — Tronçon 06 : run live (exécuté par Nico)

Prérequis : tronçons 01-05 commités, `sudo systemctl restart aria.service`.
Messages à envoyer : `docs/sprint29/run_live_parties.txt` (3 parties déjà jouées au
run sprint 28 ; Nico peut les remplacer par ses parties récentes). Renvoyer une partie
remplace sa fiche (même hash) : elle gagne la clé `motifs` par l'analyse normale.

Journal : `sudo journalctl -u aria -f -o cat`

## À observer, par partie

| Quoi | Où | Succès |
|------|----|--------|
| Explication en légende | Telegram | chaque diagramme porte sa ligne factuelle + l'explication de sa position ; le texte final = ancre + « Niveau : » + Progression, sans « Position N » |
| Occasions explosives | Telegram + `chess_explosive` | jusqu'à 3 occasions, y compris après le coup 20 si présentes ; la réponse logique citée est un coup humain plausible avec sa probabilité, qui **perd** ; jamais présentée comme meilleur coup |
| Motifs | bloc Progression + `chess_progression OK` | au moins une ligne de motif (Fourchette, Clouage, Mats…) sur les 3 parties ; un mat affiche son nom |
| Global | Progression | cohérent (pas de chute vers 1300 due aux motifs vides) |
| Durée | `chess_analysis OK … duration=` | relevée (pas de budget : information, pas de critère) |
| Fiabilité | — | pas de test provoqué ; vérifier qu'aucune `[KERNEL]` / trace sans type n'apparaît |

## Fiabilité (optionnel, si l'occasion se présente)

Couper le réseau de la VM pendant une analyse, le rétablir, envoyer « ok » : la réponse
perdue arrive précédée de « ⚠️ Ma réponse précédente n'avait pas pu partir : », et le
journal porte une ligne ERROR à l'échec.

## Critère de clôture

Les quatre premières lignes du tableau OK sur au moins 2 parties. Écarts → dettes ou
tronçon correctif, arbitrés en conception.
