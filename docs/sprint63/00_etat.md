# Sprint 63 — état du sprint

**Phase** : close (Nico, 2026-11-20 : « clos ce sprint », clôture sans run live). Tag `sprint-63`.
**Sujet** : suivi Telegram avec moteur (62-2 + 61-1).
**Branche** : `feat/sprint63-suivi-moteur`, depuis `main` @ `9308221`.
**Audit** : `audit_suivi_moteur.md`.

## Contexte hérité

- Sprint 62 clos (tag `sprint-62`) : un mat raté en ≤ 7 coups est toujours commenté, en tête du
  budget, avec la suite jusqu'au mat et la légende « mat en N manqué ». Détail : `docs/sprint62/00_etat.md`.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 62)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. **63 :** suivi Telegram avec moteur (62-2 + 61-1).
3. `/parties` sans échiquier : tri (62-4), rapide/blitz (62-5), `details` (62-6).
4. `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7).
5. Miniatures jouables dans l'échiquier (62-8).
6. Échiquier centré joueur du bas + réponses adverses (61-4 + 62-9).
7. Répertoire connu d'ARIA (61-5 + 61-10).
8. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
9. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

## Constats d'audit (résumé)

- Le suivi part en REASONING sans moteur ; l'historique coupe chaque tour à 1 500 car. : les
  blocs « Position N » de l'analyse n'arrivent jamais au LLM.
- Le PGN complet et la numérotation « Position N — coup n / joué X » sont intacts dans le tour
  `user` de l'analyse en historique : relisibles par le bridge.
- Précédent direct : relance `CHESS_BOARD_MOVE` du sprint 59 (SAN + marqueur d'historique →
  Stockfish → diagramme + texte du code).

## Décisions arrêtées (Nico, 2026-11-20)

- **1a Déclencheur** : moteur seulement si le message cite une position (« position N »,
  « coup N », SAN) et qu'une analyse figure dans l'historique récent (10 tours). Sans citation :
  circuit actuel. Raison : pas de devinette ni de balayage coûteux ; le mat raté est déjà
  commenté depuis le sprint 62.
- **2a Rédaction mixte** : ligne + diagramme écrits par le code, puis réponse LLM courte nourrie
  des seuls faits de la position. Raison : 61-1 est une question ouverte (« ce schéma »).
- **3a Coup proposé** : un SAN légal non joué est évalué à côté du coup joué ; SAN sans numéro →
  première position de Nico où il est légal, en remontant depuis la fin.

## Tronçons

| # | Tronçon | État |
|---|---|---|
| 01 | `01_suivi_moteur.md` : détection, router de suivi, moteur, diagramme, LLM sur faits | ✅ (627 verts ; regex SAN `_SAN_MOVE_RE` importée du classifieur) |
| 02 | `02_run_live.txt` : run live (Nico) | ⏭ non fait (clôture sans live, Nico 2026-11-20) |

## Dettes

| # | Dette | Constat | Piste |
|---|---|---|---|
| 61-1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : faits de la position N absents | Code livré au sprint 63 ; reste ouverte jusqu'à un run live (`02_run_live.txt`) |
| 61-2 | Motif « fourchette » trompeur | `assign_motifs` tague Qxe7+ fourchette | Revoir l'usage des motifs dans le Pourquoi |
| 61-3 | Clouage relatif et mat hors pointe | Pointe limitée au gain matériel et au clouage absolu | Étendre si un cas réel le demande |
| 61-4 | Échiquier centré sur le joueur du bas | Demande Nico 2026-11-19 | Étape 6 de la feuille de route |
| 61-5 | Répertoire connu d'ARIA | Demande Nico 2026-11-19 | Étape 7 de la feuille de route |
| 61-6 | Phrase « négligé » du Pourquoi | Commente encore le départ (Be7), pas la pointe | Quand une pointe existe, (2) porte sur la pointe |
| 61-7 | Progression fausse à la réanalyse | `games=439` répété, bloc repris de la partie précédente | Recompter quand la fiche est remplacée |
| 61-8 | Bilan inverse le camp | « 5.d5 (−21 pts pour l'adversaire) », coup de Nico | Données du tournant plus explicites |
| 61-9 | Même ouverture, deux noms | Portsmouth Gambit / Wing Gambit Deferred après 3.b4 | Regrouper dans `opening_group` |
| 61-10 | Coups de répertoire jamais jugés | 5.d5 −21 pts sans miniature (`first_move=8`) | Lié à 61-5 |
| 61-11 | Texte LLM inventé | « pion d7 passé », « Be7!? sacrifie 3 pions » | Faits plus contraints |
| 62-2 | Suivi Telegram invente la position | « j'avais mat en 2 » → « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp | Code livré au sprint 63 ; reste ouverte jusqu'à un run live (`02_run_live.txt`) |
| 63-1 | Revendication sans position citée | « j'avais mat en 2 » seul reste au LLM sans moteur (décision 1a) | Balayage des coups de Nico si un cas réel le demande |
| 62-3 | Liens cliquables dans `/parties` | Meilleures et pires parties doivent s'ouvrir dans l'échiquier ARIA | — |
| 62-4 | Tri des ouvertures | `/parties` et `/ouvertures` : tri par nombre de parties, puis % de victoires, puis égalité | — |
| 62-5 | `/parties rapide` et `/parties blitz` | Séparer par cadence (`TimeControl` du PGN) | — |
| 62-6 | `/parties details` | Liste cliquable des parties ; sans `details` : V/D du jour et des 10 dernières | — |
| 62-7 | Réutiliser l'analyse Telegram | Partie ouverte depuis `/parties` : charger l'analyse existante, ne pas tout recalculer | — |
| 62-8 | Miniatures dans l'échiquier ARIA | Jouer la variante depuis la position, explications comme dans les miniatures | — |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-11 | « pire coup » du résumé ignore le mat raté | Résumé : « pire coup 13.Be3 » alors que 10.Nxc7+ rate un mat (`summary.py:125`) | Après sprint 62 si Nico le veut |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## §REPRISE

Sprint clos sans run live. Le protocole `02_run_live.txt` reste à jouer à la prochaine
partie neuve ; 61-1 et 62-2 se ferment sur ce live. Suite : `docs/sprint64/00_etat.md`.
