# Sprint 66 — état du sprint

**Phase** : B figée (Nico, 2026-11-25 : « ok je valide »). Prochaine étape : `/sprint-auto sprint 66`.
**Audit** : `audit_miniatures_echiquier.md`.
**Sujet** : miniatures jouables dans l'échiquier ARIA (62-8).
**Branche** : `feat/sprint66-miniatures-echiquier`, depuis `main` @ `ea193c5`.

## Contexte hérité

- Sprint 65 clos (tag `sprint-65`), run live validé sur téléphone : lignes de partie de `/parties`
  et `/ouvertures <nom>` en liens Mini App (`https://t.me/<bot>?startapp=<hash>`, envoi HTML) ;
  l'échiquier ouvre la fiche par `start_param` via `POST /stored` (coups, courbe, meilleurs coups,
  historique lus dans la fiche, aucun `analyze_game`). Détail : `docs/sprint65/00_etat.md`.
- Mini App principale configurée dans BotFather (`BOARD_URL`, Tailscale Serve « tailnet only »).
- Sprint 63 : run live `docs/sprint63/02_run_live.txt` toujours à jouer à la prochaine partie neuve.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 65)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. ~~63 : suivi Telegram avec moteur (62-2 + 61-1)~~ : code livré au sprint 63, run live non fait.
3. ~~64 : `/parties` sans échiquier (62-4, 62-5, 62-6)~~ : fait au sprint 64, run live validé.
4. ~~65 : `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7)~~ : fait au sprint 65, run live validé.
5. **66 :** Miniatures jouables dans l'échiquier (62-8).
6. **67 (ajouté par Nico, 2026-11-25) :** boucle de rétroaction (66-3) : réactions 👍 / 😢 sur
   les messages Telegram, enregistrées dans le palace, traitées ensemble en conception.
7. Échiquier centré joueur du bas + réponses adverses (61-4 + 62-9).
8. Répertoire connu d'ARIA (61-5 + 61-10).
9. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
10. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

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
| 62-8 | Miniatures dans l'échiquier ARIA | Jouer la variante depuis la position, explications comme dans les miniatures | **Sprint 66** (tronçons 01-02) |
| 66-1 | Miniatures d'un PGN collé | `/game` ne refait pas l'analyse complète : pas de miniatures hors fiche | Retrouver la fiche par le hash des coups si Nico le veut |
| 66-2 | Miniatures des fiches anciennes | Fiches d'avant le sprint 66 sans `minis_json` | Réanalyse ~1 min/partie [6 runs] si Nico le veut |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-11 | « pire coup » du résumé ignore le mat raté | Résumé : « pire coup 13.Be3 » alors que 10.Nxc7+ rate un mat (`summary.py:125`) | Après sprint 62 si Nico le veut |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 64-1 | Deux règles de cadence | `chess_coach/level._cadence` (Lichess, blitz < 480 s) ≠ `meta_commands.game_cadence` (chess.com, < 600 s) : 480–599 s classé différemment | Aligner si Nico le veut |
| 64-2 | « 1 dernières » | Bilan court de `/parties` avec une seule fiche : libellé au pluriel | Accorder au singulier |
| 65-1 | Charger une position FEN (**sprint 66, tronçon 03**) dans l'échiquier | Nico, 2026-11-20 : FEN collée (`r7/P4rbk/… w - - 2 25`) → « PGN illisible » ; `loadGame` n'accepte que des coups, pas de champ FEN | Champ ou collage FEN qui place la position et lance l'analyse live |
| 65-2 | « partie introuvable » effacé | Échiquier : le message sur la ligne d'état est remplacé par l'analyse live après ~1 s (comme « PGN illisible ») | Garder le message affiché si Nico le veut |
| 65-3 | Échiquier inaccessible hors tailnet | Tailscale Serve « tailnet only » : seul le téléphone ouvre la Mini App, pas l'ordi de Nico | Tailscale sur l'ordi ; Funnel (public) seulement après arbitrage |
| 66-3 | Boucle de rétroaction | Nico, 2026-11-25 : 👍 = j'aime, 😢 = je n'aime pas, sur **chaque** message Telegram (échecs ou non ; miniature = son Pourquoi, texte final = bilan). Retours positif / aucun / négatif enregistrés dans le palace, traités ensemble en conception. But final : ARIA s'auto-améliore à chaque message (réécrit ses prompts, modifie son code si possible) ; système cognitif pas encore prêt. Constats : `run_polling` sans `allowed_updates` (réactions non reçues) ; une réaction ne porte que l'id du message → mémoriser à l'envoi message → réponse ; le résultat du router ne porte pas l'id de la fiche | **Sprint 67** ; mode de traitement en conception à décider au sprint 67 |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |


## Décisions arrêtées

- **Source (Nico, 2026-11-25)** : miniatures enregistrées dans la fiche (palace) à l'analyse
  Telegram, « tout enregistrer dans le palace […] c'est tout l'intérêt du système de mémoire ».
  Parties futures seulement.
- **But (Nico, 2026-11-25)** : rejouer la position d'une miniature comme une 2e chance de
  trouver le coup ; l'explication vient après l'essai.
- **Forme (Nico, 2026-11-25)** : onglet « Miniatures » ; tap entrée → position ; lignes jouables
  sur l'échiquier, ▶ pour avancer. PGN collé à la main : hors sprint (dette 66-1).

- **Pourquoi du LLM (Nico, 2026-11-25)** : enregistré ; miniatures posées par une mise à jour de
  la fiche après le LLM (`writer.update_chess_game_minis`, précédent `update_chess_game_opening`).
- **2e chance (Nico, 2026-11-25)** : position sans indice ; réussi = meilleur coup, coup explosif
  (sorte d) ou perte < seuil ; seuil réglable par curseur, défaut 10 pts ; raté → perte affichée,
  nouvel essai ; « Voir la solution » → légende, Pourquoi, suites jouables.
- **FEN (Nico, 2026-11-25)** : dette 65-1 traitée dans ce sprint, tronçon séparé, page seule.
- **Palace prod** : écriture additive (`minis_json` sur les fiches futures), aucune fiche
  existante modifiée, pas de rattrapage.

## Tronçons

| # | Tronçon | État |
|---|---|---|
| 01 | `01_miniatures_fiche.md` : `minis_json` écrit après le LLM, servi par `/stored` | ✅ (pytest 638 verts) |
| 02 | `02_onglet_miniatures.md` : onglet Miniatures, exercice 2e chance, solution, curseur | ⏳ |
| 03 | `03_fen.md` : FEN collée dans l'échiquier (65-1) | ⏳ |
| 04 | `04_run_live.txt` : run live (Nico, partie neuve) | ⏳ |

## §REPRISE

Tronçon 01 fait (non commité) : `writer.update_chess_game_minis`, `chess_router._mini` /
`_critical_mini` (miniatures construites avec les images, légendes finales recopiées après
`_split_entries` et la conversion, écrites si `write_chess_game` a réussi), clé `minis` de
`/stored`. Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳ (02).
Prochaine étape : `/sprint-auto sprint 66`.
