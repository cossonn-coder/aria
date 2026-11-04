# Sprint 49 — état vivant (analyse stable, meilleur coup, miniatures, doublons)

**Phase** : conception figée le 2026-11-04, prête pour `/sprint-auto sprint 49`.
**Branche** : `feat/sprint49-analyse-stable` (depuis `main`).
**Audit** : `audit_analyse_stable.md`. L'étude AggroChess close sans code reste dans `audit_aggrochess.md`.

## Objectif

Une analyse reproductible et pas plus lente ; un meilleur coup immédiat et sans limite sur l'échiquier ; des miniatures qui montrent la variante et la chute d'évaluation ; aucune partie en double.

## Décisions arrêtées (Nico, 2026-11-04)

- Parties envoyées : nœuds fixes, demi-budget (0,59 M de nœuds par seconde demandée), 8 Stockfish à 1 thread. Reproductible [2 parties, 2 rejeux], vitesse équivalente, 5 sacrifices connus sur 6 [6 positions, 2 essais].
- Stable ne veut pas dire plus juste : la liste d'explosifs dépend du budget ; un manque peut rester figé (grec, #177). Accepté.
- Pas de recherche d'explosifs si 4 erreurs remplissent les places (#162), ni avant `first_move` (#160).
- Échiquier : flèche bleue immédiate depuis `/eval` ou `/game`, puis résultat de tête publié sans attendre la fin de passe. Les 4 limites du bleu supprimées. Case décochée à chaque nouvelle partie et chargement de PGN (conservé, sprint 39).
- Même coup qu'une autre flèche : bleu, sauf le seul coup qui reste vert.
- Échiquier : résultat gardé par position au retour. Pas de nœuds fixes en live : une flèche peut encore changer entre passes (#125 partielle).
- Miniatures : flèches numérotées 1, 2, 3 sur l'image ; ligne du meilleur coup ajoutée à la légende des `d` ; coup joué = meilleur coup : la bleue porte le n° 1. #109 hors périmètre.
- Miniatures : une erreur (`a`, `b`) montre la chute d'évaluation ; un seul coup (`c`) montre l'écart avec le 2e meilleur coup.
- Doublon : même partie (mêmes coups, en-têtes ignorés) = ni analyse, ni fiche, ni miniature, seulement un message « déjà envoyée ». Palace vérifié sur copie : 125 fiches, 0 doublon, aucune migration.

## Par défaut, sans veto à ce stade

- Évaluation des légendes en % de gain et pts, comme la courbe et la page.
- « Seul coup » traité sur les miniatures, pas sur l'échiquier.
- 2e meilleur coup non nommé (son nom n'est pas stocké).
- Deux parties réelles aux coups identiques comptent comme une seule (règle du hash existante).

## Carte des tronçons

- 01 parties envoyées stables (`01_parties_stables.md`) ✅ (ouverture des 8 moteurs en parallèle : à la suite, 31 à 41 s [2 mesures, machine chargée])
- 02 échiquier live (`02_echiquier_live.md`) ✅ (tête publiée à la première passe seulement : `best` reste celui des autres flèches ensuite)
- 03 miniatures (`03_miniatures.md`) ✅ (pastille sur la flèche, à la base de la pointe : prise et reprise sur la même case restent lisibles ; n° 1 bleu si coup joué = meilleur coup)
- 04 doublons (`04_doublons.md`) ⏳
- 05 run live par Nico (`05_run_live.md`, messages : `run_live_messages.txt`) ⏳

## Questions ouvertes

- (aucune)

## Dettes

Fermées si le run live confirme : #85, #108 (partie envoyée), #97 (renvoyer ne touche plus la fiche), #160, #162. #125 partielle.
Nouvelles, à inscrire à la clôture :
- Interruption de la recherche live pendant un appel moteur (jusqu'à 4,8 s à ×8 [calcul]).
- Texte LLM variable d'une analyse à l'autre.
- `/eval` et le worker donnent deux meilleurs coups de profondeurs différentes.
- Aucun moyen de réanalyser une partie déjà envoyée (après une amélioration de l'analyse).
Au tableau : `test_explosive_early_queen_nf6` (#85) n'existe plus.

## §REPRISE

Tronçons 01, 02 et 03 faits, 03 non commité à ce stade. Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳ (04, `04_doublons.md`). Prochaine étape : `/sprint-auto sprint 49`.
