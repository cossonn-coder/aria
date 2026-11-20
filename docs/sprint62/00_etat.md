# Sprint 62 — état du sprint

**Phase** : A (audit 62-1 fait, arbitrages en cours), rien de figé.
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
- Chantier `/parties` + échiquier ARIA (demande Nico 2026-11-20, lignes 62-3 à 62-9) : volumineux,
  à découper sur plusieurs sprints.

## Feuille de route (proposée, à valider)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. **62 : mat raté** (62-1). Audit : `audit_mat_rate.md`.
2. Suivi Telegram avec moteur (62-2 + 61-1).
3. `/parties` sans échiquier : tri (62-4), rapide/blitz (62-5), `details` (62-6).
4. `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7).
5. Miniatures jouables dans l'échiquier (62-8).
6. Échiquier centré joueur du bas + réponses adverses (61-4 + 62-9).
7. Répertoire connu d'ARIA (61-5 + 61-10).
8. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
9. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

## Questions ouvertes (sprint 62)

- Portée : mat en ≤ 3 coups de Nico ? (reco : oui)
- Priorité : mat raté en tête du budget, toujours retenu ? (reco : oui)
- Légende : « mat en N manqué » au lieu de « −13 pts » ; qualité et stats inchangées ? (reco : oui)

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
| 62-1 | Mat raté noyé dans les imprécisions | Partie 2026-11-20 (Modern) : après 9...fxe6, 10.Bb5+ c6 11.Nf6# (Stockfish #+2) ; joué 10.Nxc7+ (+467). `_win` borne à `_CP_CLAMP=1000` → mat = 97,5 %, +467 = 84,8 % : perte 12,7 pts, simple imprécision, éclipsée par 13.Be3 (−31) et 19.gxh5 (−30) | Mat forcé raté = toujours une position commentée, quelle que soit la perte en pts |
| 62-2 | Suivi Telegram invente la position | Même partie, « j'avais mat en 2 » → « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp, dame noire échangée au coup 6. Le LLM répond sans échiquier ni moteur | Lié à 61-1 : le suivi relance le moteur sur la position citée |
| 62-3 | Liens cliquables dans `/parties` | Meilleures et pires parties doivent s'ouvrir dans l'échiquier ARIA | — |
| 62-4 | Tri des ouvertures | `/parties` et `/ouvertures` : tri par nombre de parties, puis % de victoires, puis égalité | — |
| 62-5 | `/parties rapide` et `/parties blitz` | Séparer par cadence (`TimeControl` du PGN) | — |
| 62-6 | `/parties details` | Liste cliquable des parties ; sans `details` : V/D du jour et des 10 dernières | — |
| 62-7 | Réutiliser l'analyse Telegram | Partie ouverte depuis `/parties` : charger l'analyse existante, ne pas tout recalculer | — |
| 62-8 | Miniatures dans l'échiquier ARIA | Jouer la variante depuis la position, explications comme dans les miniatures | — |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## §REPRISE

Lire `CLAUDE.md`, ce fichier. Prochaine étape : réponses de Nico aux 3 questions ouvertes, puis kickoff 62-1 (`audit_mat_rate.md`).
