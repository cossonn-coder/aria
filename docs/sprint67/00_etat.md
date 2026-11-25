# Sprint 67 — état du sprint

**Phase** : B figée (OK Nico 2026-11-25). Prochaine étape : `/sprint-auto sprint 67`.
**Sujet** : boucle de rétroaction 👍 / 😢 sur les messages Telegram (66-3).
**Branche** : `feat/sprint67-retroaction` (depuis `main`, tag `sprint-66`).

## Décisions arrêtées (Nico, 2026-11-25)

1. **Chaque message envoyé est noté** dans un wing dédié `aria_feedback` (texte + demande d'origine) ; une réaction met la fiche à jour. Raison : distinguer 👍 / 😢 / aucun, survivre aux redémarrages ; pas dans `aria_episodic` (lue en similarité pour le contexte LLM).
2. **Périmètre** : toutes les sorties passées par `_send_with_retry` (réponses, photos de miniatures, métacommandes, échiquier) ; exclus : « ⏳ Je travaille dessus », « je reviens », « écrit… ».
3. **Exploitation** : nouveau skill `/amelioration` qui lit un rapport des retours et propose des axes de travail à lancer en `/conception`. Ne modifie rien.
4. **Démarrage** : un hook SessionStart (projet aria) lance un script sans LLM qui n'affiche qu'une ligne « N nouveaux retours dont K 😢 → /amelioration », rien s'il n'y a rien.
5. **Déjà traité** : chaque passage de `/amelioration` écrit `docs/amelioration/AAAA-MM-JJ.md` ; le suivant repart de la date du dernier rapport. Claude Code ne fait que **lire** le palace (pas d'écriture hors du service : risque de corruption à deux process).
6. **Commentaire** dans ce sprint : répondre (« Répondre » Telegram) à un message d'ARIA par un texte qui commence par 👍 ou 😢 enregistre réaction + commentaire sur ce message, au lieu de partir dans la conversation.

## Tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_reactions.md` | Réactions reçues, chaque envoi noté dans `aria_feedback`, commentaire par réponse 👍/😢, `/status` || ✅ (644 tests ; écart : `MessageReactionHandler` exige `message_reaction_types=MESSAGE_REACTION_UPDATED` avec `user_id` ; commandes notées par un `MessageHandler` COMMAND en groupe -1) |
| 02 | `02_amelioration.md` | `scripts/feedback_report.py`, hook SessionStart, skill `/amelioration` (ces deux derniers locaux : `.claude/` gitignoré) | ⏳ |
| 03 | `03_run_live.txt` | Run live par Nico (risque n°1 : réactions reçues en chat privé ?) | ⏳ |

Dettes : 66-3 fermée par ce sprint une fois le run live validé. Nouvelle dette possible :
`.claude/` gitignoré en entier (skills et hooks non versionnés) — à arbitrer si Nico veut les versionner.

## Questions ouvertes

(aucune)

## Contexte hérité

- Sprint 66 clos (tag `sprint-66`), run live validé sur téléphone : miniatures enregistrées dans la
  fiche (`minis_json`, écrites après le LLM par `writer.update_chess_game_minis`) et servies par
  `POST /stored` ; onglet « Miniatures » de l'échiquier, exercice « 2e chance » sans indice,
  solution (légende + suites jouables), curseur de seuil, glissement suivante / précédente ;
  FEN collée dans le champ PGN. Détail : `docs/sprint66/00_etat.md`.
- Sprint 63 : run live `docs/sprint63/02_run_live.txt` toujours à jouer à la prochaine partie neuve.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 66)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. ~~63 : suivi Telegram avec moteur (62-2 + 61-1)~~ : code livré au sprint 63, run live non fait.
3. ~~64 : `/parties` sans échiquier (62-4, 62-5, 62-6)~~ : fait au sprint 64, run live validé.
4. ~~65 : `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7)~~ : fait au sprint 65, run live validé.
5. ~~66 : miniatures jouables dans l'échiquier (62-8)~~ : fait au sprint 66, run live validé.
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
| 61-4 | Échiquier centré sur le joueur du bas | Demande Nico 2026-11-19 | Étape 7 de la feuille de route |
| 61-5 | Répertoire connu d'ARIA | Demande Nico 2026-11-19 | Étape 8 de la feuille de route |
| 61-6 | Phrase « négligé » du Pourquoi | Commente encore le départ (Be7), pas la pointe | Quand une pointe existe, (2) porte sur la pointe |
| 61-7 | Progression fausse à la réanalyse | `games=439` répété, bloc repris de la partie précédente | Recompter quand la fiche est remplacée |
| 61-8 | Bilan inverse le camp | « 5.d5 (−21 pts pour l'adversaire) », coup de Nico | Données du tournant plus explicites |
| 61-9 | Même ouverture, deux noms | Portsmouth Gambit / Wing Gambit Deferred après 3.b4 | Regrouper dans `opening_group` |
| 61-10 | Coups de répertoire jamais jugés | 5.d5 −21 pts sans miniature (`first_move=8`) | Lié à 61-5 |
| 61-11 | Texte LLM inventé | « pion d7 passé », « Be7!? sacrifie 3 pions » | Faits plus contraints |
| 62-2 | Suivi Telegram invente la position | « j'avais mat en 2 » → « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp | Code livré au sprint 63 ; reste ouverte jusqu'au run live `docs/sprint63/02_run_live.txt` |
| 63-1 | Revendication sans position citée | « j'avais mat en 2 » seul reste au LLM sans moteur (décision 1a) | Balayage des coups de Nico si un cas réel le demande |
| 66-1 | Miniatures d'un PGN collé | `/game` ne refait pas l'analyse complète : pas de miniatures hors fiche | Retrouver la fiche par le hash des coups si Nico le veut |
| 66-2 | Miniatures des fiches anciennes | Fiches d'avant le sprint 66 sans `minis_json` | Réanalyse ~1 min/partie [6 runs] si Nico le veut |
| 62-9 | Anticiper les réponses adverses | Échiquier ARIA : coups logiques de l'adversaire + variante pour chacun (recoupe 61-4) | — |
| 62-11 | « pire coup » du résumé ignore le mat raté | Résumé : « pire coup 13.Be3 » alors que 10.Nxc7+ rate un mat (`summary.py:125`) | Après sprint 62 si Nico le veut |
| 62-10 | Accès Iona | Note de Nico 2026-11-20 : « accès Iona à faire », contenu à préciser | — |
| 64-1 | Deux règles de cadence | `chess_coach/level._cadence` (Lichess, blitz < 480 s) ≠ `meta_commands.game_cadence` (chess.com, < 600 s) : 480–599 s classé différemment | Aligner si Nico le veut |
| 64-2 | « 1 dernières » | Bilan court de `/parties` avec une seule fiche : libellé au pluriel | Accorder au singulier |
| 65-2 | « partie introuvable » effacé | Échiquier : le message sur la ligne d'état est remplacé par l'analyse live après ~1 s (comme « PGN illisible ») | Garder le message affiché si Nico le veut |
| 65-3 | Échiquier inaccessible hors tailnet | Tailscale Serve « tailnet only » : seul le téléphone ouvre la Mini App, pas l'ordi de Nico | Tailscale sur l'ordi ; Funnel (public) seulement après arbitrage |
| 66-3 | Boucle de rétroaction | Nico, 2026-11-25 : 👍 = j'aime, 😢 = je n'aime pas, sur **chaque** message Telegram (échecs ou non ; miniature = son Pourquoi, texte final = bilan). Retours positif / aucun / négatif enregistrés dans le palace, traités ensemble en conception. But final : ARIA s'auto-améliore à chaque message (réécrit ses prompts, modifie son code si possible) ; système cognitif pas encore prêt. Constats : `run_polling` sans `allowed_updates` (réactions non reçues) ; une réaction ne porte que l'id du message → mémoriser à l'envoi message → réponse ; le résultat du router ne porte pas l'id de la fiche | **Sprint 67** ; mode de traitement à décider en conception |
| 66-4 | « Envoyer à ARIA » depuis une FEN | Le PGN exporté porte `SetUp`/`FEN` ; lecture côté serveur non vérifiée | Vérifier si Nico envoie une position collée |
| 66-5 | ▶ du haut sur PC vide la suite d'une miniature | ▶ de `#nav` fait `goTo` (partie) ; la suite se joue par → ou la molette | Faire jouer `ahead` à ▶ si Nico le veut |
| 66-6 | Miniatures perdues au rechargement hors Telegram | Rechargement : partie relue par `/game`, sans `minis` | Rouvrir par `/stored` si Nico le veut |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_retroaction.md`. Conception figée. Tronçon 01 fait (non commité à sa sortie de sous-agent). Prochaine étape : tronçon 02 (`02_amelioration.md`, `bridge.load_feedback(since)` disponible), puis run live `03_run_live.txt` par Nico.
