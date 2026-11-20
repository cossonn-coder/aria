# Sprint 65 — état du sprint

**Phase** : B figée (Nico, 2026-11-20 : « on suit tes recommandations, je valide »). Prêt pour `/sprint-auto sprint 65`.
**Audit** : `audit_parties_echiquier.md`.
**Sujet** : `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7).
**Branche** : `feat/sprint65-parties-echiquier`, depuis `main` @ `4f0d8ed`.

## Contexte hérité

- Sprint 64 clos (tag `sprint-64`), run live validé : `/parties` court par défaut (bilan du jour
  ou de la période, puis « 10 dernières »), `/parties details` complet ; filtres `rapide` /
  `blitz` (règle chess.com, blitz < 600 s) ; ouvertures triées par parties, % de victoires,
  nulles ; `/ouvertures` sans classement 5 meilleures / 5 pires. Détail : `docs/sprint64/00_etat.md`.
- Sprint 63 : run live `docs/sprint63/02_run_live.txt` toujours à jouer à la prochaine partie neuve.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 64)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. ~~63 : suivi Telegram avec moteur (62-2 + 61-1)~~ : code livré au sprint 63, run live non fait.
3. ~~64 : `/parties` sans échiquier (62-4, 62-5, 62-6)~~ : fait au sprint 64, run live validé.
4. **65 :** `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7).
5. Miniatures jouables dans l'échiquier (62-8).
6. Échiquier centré joueur du bas + réponses adverses (61-4 + 62-9).
7. Répertoire connu d'ARIA (61-5 + 61-10).
8. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
9. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

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
| 62-3 | Liens cliquables dans `/parties` | Meilleures et pires parties doivent s'ouvrir dans l'échiquier ARIA | **Sprint 65** |
| 62-7 | Réutiliser l'analyse Telegram | Partie ouverte depuis `/parties` : charger l'analyse existante, ne pas tout recalculer | **Sprint 65** |
| 62-8 | Miniatures dans l'échiquier ARIA | Jouer la variante depuis la position, explications comme dans les miniatures | — |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-11 | « pire coup » du résumé ignore le mat raté | Résumé : « pire coup 13.Be3 » alors que 10.Nxc7+ rate un mat (`summary.py:125`) | Après sprint 62 si Nico le veut |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 64-1 | Deux règles de cadence | `chess_coach/level._cadence` (Lichess, blitz < 480 s) ≠ `meta_commands.game_cadence` (chess.com, < 600 s) : 480–599 s classé différemment | Aligner si Nico le veut |
| 64-2 | « 1 dernières » | Bilan court de `/parties` avec une seule fiche : libellé au pluriel | Accorder au singulier |
| 65-1 | Charger une position FEN dans l'échiquier | Nico, 2026-11-20 : FEN collée (`r7/P4rbk/… w - - 2 25`) → « PGN illisible » ; `loadGame` n'accepte que des coups, pas de champ FEN | Champ ou collage FEN qui place la position et lance l'analyse live |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## Décisions arrêtées (Nico, 2026-11-20)

- **Parties cliquables** : toutes les lignes qui nomment une partie (`/parties details` ligne par
  partie + classement 🏆/📉, classement de `/parties <ouv.>` et `/ouvertures <nom>`).
- **Forme** : liens dans le texte vers la Mini App principale `https://t.me/<bot>?startapp=<hash>`,
  envoi HTML. Raison : toutes les lignes cliquables, ouverture dans Telegram. Prérequis : Mini App
  principale configurée dans BotFather (Nico, avant le run live).
- **Analyse rechargée (62-7)** : coups, courbe, meilleurs coups, historique lus dans la fiche,
  aucun `analyze_game`. Hors : repères de mat (pas d'`eval_cp` stocké, palace intact), texte du
  coach (étape 5, 62-8). L'analyse live par position reste active.
- **Hors sprint** : FEN dans l'échiquier → dette 65-1. Pseudo `BaguetteCopter` ajouté hors sprint
  sur `main` (`4f0d8ed`).

## Tronçons

| # | Tronçon | État |
|---|---|---|
| 01 | `01_echiquier_fiche.md` : route `/stored` + page qui ouvre une fiche par `start_param` | ✅ (634 tests verts) |
| 02 | `02_liens_parties.md` : lignes de partie en liens Mini App dans `/parties` et `/ouvertures <nom>` | ✅ (636 tests verts) |
| 03 | `03_run_live.txt` : run live (Nico) | ⏳ |

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis `03_run_live.txt`. Tronçons 01 et 02 faits.
01 : `board_interface.stored_game` + `POST /stored` (fiche → pgn, playing, wins, best, mates `None`,
history, sans moteur), `GET /` sur le chemin seul, page `openStored` au démarrage
(`start_param` / `tgWebAppStartParam`, prime sur `localStorage`).
02 : `meta_commands` — paramètre `link` (fiche → URL) dans `parties_text`, `parties_opening_text`,
`opening_report_text`, `_ranking_lines` ; avec `link`, texte échappé et lignes de partie en
`<a href>` ; sans `link`, sortie inchangée. `telegram_interface` : `_game_url`
(`https://t.me/<bot>?startapp=<hash>`) et `_deliver_html` (HTML, aperçu désactivé, découpe par
lignes ≤ 4096) pour `/parties` (toutes formes) et `/ouvertures <nom>` ; `/ouvertures` sans nom
reste en texte brut.
Prochaine étape : run live `03_run_live.txt` par Nico (prérequis : Mini App principale dans
BotFather). Dettes 62-3 et 62-7 : à fermer au run live.
