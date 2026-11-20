# Sprint 64 — état du sprint

**Phase** : close (Nico, 2026-11-20 : « le run live est validé »). Tag `sprint-64`.
**Sujet** : `/parties` sans échiquier : tri (62-4), rapide/blitz (62-5), `details` (62-6).
**Branche** : `feat/sprint64-parties`, depuis `main` @ `9ab136f`.
**Audit** : `audit_parties.md`.

## Contexte hérité

- Sprint 63 clos (tag `sprint-63`) sans run live : une question de suivi qui cite une position
  (« position N », « coup N », SAN) après une analyse en historique passe par `CHESS_FOLLOWUP` :
  Stockfish sur coup joué / meilleur / proposé, ligne + diagramme écrits par le code, LLM sur
  les seuls faits. Le run live `docs/sprint63/02_run_live.txt` reste à jouer à la prochaine
  partie neuve ; 61-1 et 62-2 se ferment sur ce live.
- Écarts sprint 63 : le router importe la regex privée `_SAN_MOVE_RE` du classifieur ; pour le
  coup joué, les faits suivent la ligne moteur, pas la réponse réellement jouée.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 63)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. ~~63 : suivi Telegram avec moteur (62-2 + 61-1)~~ : code livré au sprint 63, run live non fait.
3. **64 :** `/parties` sans échiquier : tri (62-4), rapide/blitz (62-5), `details` (62-6).
4. `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7).
5. Miniatures jouables dans l'échiquier (62-8).
6. Échiquier centré joueur du bas + réponses adverses (61-4 + 62-9).
7. Répertoire connu d'ARIA (61-5 + 61-10).
8. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
9. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

## Décisions arrêtées (Nico, 2026-11-20)

- **Tri 62-4** : nombre de parties, puis % de victoires, puis nombre de nulles (le plus d'abord).
  `/ouvertures` garde la plus jouée en bas. Raison : demande « puis égalité » = les nulles.
- **Cadence 62-5** : règle chess.com, durée = base + 40 × incrément ; blitz < 600 s ≤ rapide.
  Mots `rapide` / `blitz` sur `/parties` et `/ouvertures`, combinables avec ouverture et
  période. Fiches sans cadence exclues des deux filtres.
- **`details` 62-6** : sans `details`, bilan court (« Aujourd'hui » ou période, puis
  « 10 dernières », + performance). Avec `details` : sortie complète actuelle, une ligne par
  partie quelle que soit la période. Non cliquable : lien vers l'échiquier = étape 4 (62-3).

- **`/ouvertures` sans classement** (Nico, 2026-11-20, après le tronçon 01) : plus de liste
  des 5 meilleures / 5 pires ; le classement reste dans `/parties details`.

## Tronçons

| # | Tronçon | État |
|---|---|---|
| 01 | `01_parties.md` : arguments, tri, cadence, `/parties` court / `details` | ✅ (631 tests verts) |
| 02 | `02_run_live.txt` : run live (Nico) | ✅ (validé 2026-11-20) |

## Dettes

| # | Dette | Constat | Piste |
|---|---|---|---|
| 61-1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : faits de la position N absents | Code livré au sprint 63 ; reste ouverte jusqu'au run live `docs/sprint63/02_run_live.txt` |
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
| 62-2 | Suivi Telegram invente la position | « j'avais mat en 2 » → « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp | Code livré au sprint 63 ; reste ouverte jusqu'au run live `docs/sprint63/02_run_live.txt` |
| 63-1 | Revendication sans position citée | « j'avais mat en 2 » seul reste au LLM sans moteur (décision 1a) | Balayage des coups de Nico si un cas réel le demande |
| 62-3 | Liens cliquables dans `/parties` | Meilleures et pires parties doivent s'ouvrir dans l'échiquier ARIA | — |
| 62-4 | Tri des ouvertures | `/parties` et `/ouvertures` : tri par nombre de parties, puis % de victoires, puis égalité | **Fermée** (sprint 64, run live validé) |
| 62-5 | `/parties rapide` et `/parties blitz` | Séparer par cadence (`TimeControl` du PGN) | **Fermée** (sprint 64, run live validé) |
| 62-6 | `/parties details` | Liste cliquable des parties ; sans `details` : V/D du jour et des 10 dernières | **Fermée** (sprint 64, run live validé) |
| 62-7 | Réutiliser l'analyse Telegram | Partie ouverte depuis `/parties` : charger l'analyse existante, ne pas tout recalculer | — |
| 62-8 | Miniatures dans l'échiquier ARIA | Jouer la variante depuis la position, explications comme dans les miniatures | — |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-11 | « pire coup » du résumé ignore le mat raté | Résumé : « pire coup 13.Be3 » alors que 10.Nxc7+ rate un mat (`summary.py:125`) | Après sprint 62 si Nico le veut |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 64-1 | Deux règles de cadence | `chess_coach/level._cadence` (Lichess, blitz < 480 s) ≠ `meta_commands.game_cadence` (chess.com, < 600 s) : 480–599 s classé différemment | Aligner si Nico le veut |
| 64-2 | « 1 dernières » | Bilan court de `/parties` avec une seule fiche : libellé au pluriel | Accorder au singulier |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## §REPRISE

Sprint clos (tag `sprint-64`). Suite : `docs/sprint65/00_etat.md`.
