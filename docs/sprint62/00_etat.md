# Sprint 62 — état du sprint

**Phase** : 0 (cible à arbitrer), rien de figé.
**Branche** : à créer depuis `main` après merge du sprint 61.

## Contexte hérité

- Sprint 61 clos (tag `sprint-61`) : pointe de combinaison (ligne « Pointe : » + défenses réfutées)
  et, hors kickoff, miniatures dès le coup 1 (planchers coup 4 / Göring 7 et seuil ouverture ≥ 20
  retirés ; règle du répertoire gardée). Détail : `docs/sprint61/00_etat.md`.

## Candidats (Nico choisit)

- Échiquier ARIA centré sur le joueur du bas (anticipation adverse, flèches numérotées) — prévu
  pour le sprint 62 dès le 2026-11-19.
- Répertoire connu d'ARIA : savoir ce que Nico joue et le prévenir quand il sort de la meilleure
  ligne de son répertoire, y compris quand sa ligne habituelle est mauvaise (5.d5, −21 pts, jamais
  jugé car dans le répertoire).

## Dettes

| # | Dette | Constat | Piste |
|---|---|---|---|
| 61-1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : faits de la position N absents | Router de suivi qui relance l'analyse de la position citée |
| 61-2 | Motif « fourchette » trompeur | `assign_motifs` tague Qxe7+ fourchette | Revoir l'usage des motifs dans le Pourquoi |
| 61-3 | Clouage relatif et mat hors pointe | Pointe limitée au gain matériel et au clouage absolu | Étendre si un cas réel le demande |
| 61-4 | Échiquier centré sur le joueur du bas | Demande Nico 2026-11-19 | Candidat sprint 62 |
| 61-5 | Répertoire connu d'ARIA | Demande Nico 2026-11-19 | Candidat sprint 62 |
| 61-6 | Phrase « négligé » du Pourquoi | Commente encore le départ (Be7), pas la pointe | Quand une pointe existe, (2) porte sur la pointe |
| 61-7 | Progression fausse à la réanalyse | `games=439` répété, bloc repris de la partie précédente | Recompter quand la fiche est remplacée |
| 61-8 | Bilan inverse le camp | « 5.d5 (−21 pts pour l'adversaire) », coup de Nico | Données du tournant plus explicites |
| 61-9 | Même ouverture, deux noms | Portsmouth Gambit / Wing Gambit Deferred après 3.b4 | Regrouper dans `opening_group` |
| 61-10 | Coups de répertoire jamais jugés | 5.d5 −21 pts sans miniature (`first_move=8`) | Lié à 61-5 |
| 61-11 | Texte LLM inventé | « pion d7 passé », « Be7!? sacrifie 3 pions » | Faits plus contraints |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## §REPRISE

Lire `CLAUDE.md`, ce fichier. Prochaine étape : `/conception sprint 62` (choix de la cible).
