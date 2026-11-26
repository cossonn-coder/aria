# Sprint 68 — état du sprint

**Phase** : B figée (OK de Nico, 2026-11-25). Prochaine étape : `/sprint-auto sprint 68`.
**Sujet** : étape 7 de la feuille de route, échiquier centré sur le joueur du bas + réponses
adverses (61-4 + 62-9), élargi à la vitesse de l'échiquier et de l'analyse Telegram. Nico, 2026-11-25 : on suit la feuille de route ; les axes de
`/amelioration` restent en dettes (67-1 à 67-5).
**Branche** : `feat/sprint68-vitesse-anticipation` (depuis `main` à `626ec49`).

## Contexte hérité

- Sprint 67 clos (tag `sprint-67`), run live validé : chaque message envoyé noté dans `aria_feedback`,
  réactions 👍 / 👎 reçues, commentaire par « Répondre » + texte commençant par 👍 / 👎,
  `scripts/feedback_report.py`, alerte SessionStart, skill `/amelioration` (`.claude/`, non versionné).
  Premier rapport : `docs/amelioration/2026-11-25.md` (4 axes). Détail : `docs/sprint67/00_etat.md`.
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
6. ~~67 (ajouté par Nico, 2026-11-25) : boucle de rétroaction (66-3) : réactions 👍 / 👎 sur
   les messages Telegram, enregistrées dans le palace, traitées ensemble en conception~~ : fait au sprint 67, run live validé.
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
| 66-4 | « Envoyer à ARIA » depuis une FEN | Le PGN exporté porte `SetUp`/`FEN` ; lecture côté serveur non vérifiée | Vérifier si Nico envoie une position collée |
| 66-5 | ▶ du haut sur PC vide la suite d'une miniature | ▶ de `#nav` fait `goTo` (partie) ; la suite se joue par → ou la molette | Faire jouer `ahead` à ▶ si Nico le veut |
| 66-6 | Miniatures perdues au rechargement hors Telegram | Rechargement : partie relue par `/game`, sans `minis` | Rouvrir par `/stored` si Nico le veut |
| 67-1 | Demande de recettes routée vers l'image | Run live 2026-11-25 : « donne 3 idées de dîner d'automne hiver rapide gourmand genereux et gras pour 7 » → une image générée, légende = la demande ; 👎 de Nico (fiche `tg_6895898630_6816`) | Cause : `"genere"` testé en sous-chaîne (`cognition/cognitive_classifier.py:65`, `:117`) ; axe 3 de `docs/amelioration/2026-11-25.md` | Mots-clés en mots entiers |
| 67-2 | Variante explosive coupée avant la pointe | 12.Bb5!? s'arrête à 13.Qxa8 (avantage « clair »), sans …Qxa8 Nxc7+ ; pas de ligne « Pointe : » en sorte d ; 👎 + commentaire Nico « c'est ce genre d'analyse que je recherche » | Axe 1 de `docs/amelioration/2026-11-25.md` ; recoupe 61-3, 61-11 |
| 67-3 | Bilan : % de gain sans repère, « coup N » sans le coup | « de 44 % au coup 5 à 88 % au coup 18 » ; 👎 + commentaire Nico | Axe 2 de `docs/amelioration/2026-11-25.md` ; recoupe 61-8 |
| 67-4 | Commentaire hors « Répondre » perdu | Texte libre après un 👎 part au kernel (suivi « coup 18 » inventé, excuse qui invente encore) | Axe 4 : rappeler le geste ou rattacher au dernier 👎 |
| 67-5 | Contexte de conversation qui bave | « 👎  trop long » sans « Répondre » → « aucune info sur un dessert » ; « et pour le dessert ? » sans le dîner (réponse image) | À arbitrer |
| 67-6 | `.claude/` gitignoré | Skill `/amelioration` et hook SessionStart non versionnés | Versionner si Nico le veut |
| 68-1 | Analyse live trop lente | Nico 2026-11-25 : « tout est trop lent » ; 4 passes ×1/×2/×4/×8 (≈ 75 s cumulées [commentaire de `live.py`, non mesuré]) au tour du joueur du bas | Hors sprint 68 (seul le tour adverse est allégé) ; mesurer puis réduire si Nico le veut |
| 68-2 | Écritures palace lentes : embedding torch à 16 threads | Tronçon 02 (`mesure_ecritures.txt`) : ~2,2 à 2,6 s par écriture [n=3, machine chargée], dont embedding ~1,8 s ; ~10 `write_sent_message` attendus entre les envois d'un bilan ≈ 25 s [estimation]. À 4 threads : ~1,2 à 1,6 s par écriture [n=3, autre passage]. Réouverture du client : ~0,1 s, sans gain | (a) `torch.set_num_threads(4)` au démarrage (touche aussi Maia) ; (b) `write_sent_message` sans attendre, après l'envoi (nouveau motif dans `telegram_interface`). À arbitrer par Nico |
| 68-3 | Recherche explosive toujours ~45 à 110 s par partie | Tronçon 03 : seul le réglage torch passe le corpus ; `_MAX_DEEP` 2 et `_DEEP_TIME` 0.2 changent les coups (`mesure_explosive.txt`). Durées murales bruitées par la charge (11-22) | Remesurer machine au calme si Nico le veut ; pas d'autre réglage sans perte de coups dans le périmètre |
| 60 | Lecture d'échiquier en image | Lecteur local chess.com faux, quota Gemini, correction | `docs/sprint60/00_etat.md` |

## Tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_bilan_telegram.md` | Durées par étape, bilan sans rappels mémoire, préchargement | ✅ |
| 02 | `02_ecritures.md` | Écritures mesurées sur une copie du palace, puis allégées | ✅ (mesure seule, dette 68-2) |
| 03 | `03_recherche_explosive.md` | Recherche explosive plus courte, mêmes coups sur un corpus | ✅ (Maia à 1 thread torch ; gain mural incertain) |
| 04 | `04_echiquier_serveur.md` | Anticipation, `/eval` persistant, publication précoce, sans ×8, PGN connu | ✅ |
| 05 | `05_echiquier_page.md` | Orientation, retournement, flèches et panneau d'anticipation | ✅ |
| 06 | `06_run_live.txt` | Run live (Nico) | ⏳ |

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳. Exécution : `/sprint-auto
sprint 68`. Contexte des mesures : `audit_joueur_du_bas.md` §6.

Tronçon 01 fait : `chess_timing` (`_execute_game`) et `pipeline_timing` (`_run_pipeline`) au
journal ; drapeau `skip_memory` posé par `_execute_game` (log `memory_recall SKIPPED`) ;
préchargement embedder + Maia dans un thread daemon de `bot.py` (log `preload OK duration=…`).
Gain réel à mesurer au run live (tronçon 06).

Tronçon 02 fait, mesure seule : `docs/sprint68/mesure_ecritures.py` (copie du palace dans
`~/.cache`, `/tmp` plein) et `mesure_ecritures.txt`. Aucune piste admise par le kickoff ne gagne
(pas de double embedding, pas de relecture, réouverture ~0,1 s) : le coût est l'embedding torch à
16 threads sur machine chargée, dette 68-2 (arbitrage Nico). Aucun code de prod modifié.

Tronçon 03 fait : `docs/sprint68/mesure_explosive.py` + `mesure_explosive.txt`. Corpus = 8 fiches
récentes avec une miniature d dans `plies_json` (`minis_json` n'existe que sur 2 fiches). Retenu :
`find_explosive` met Maia à 1 thread torch pendant `run_on_engines`, rétabli après : 50 coups sur
50 identiques et réponses Maia identiques [2 passages], CPU −15 % puis −6 %, durée murale −15 %
puis +1 % [2 passages appariés, charge 11-22]. Rejetés : `_MAX_DEEP` 2 (perd 3 coups),
`_DEEP_TIME` 0.2 (coups différents dans 6 parties). Gain réel à lire au run live
(`chess_explosive … duration=`). Test : `test_find_explosive_runs_maia_on_one_torch_thread`.

Tronçon 04 fait : `live.anticipate_pass` (Maia du camp au trait, 3 coups p ≥ 0,10, réponse
tirée de `line_san[1]`) ; `BoardWorker.submit(…, bottom)`, mode `analyse` / `anticipate` dans la clé
du cache, état `anticipated` ; `/eval` sur un Stockfish de module sous verrou ; piège / stratégie
publiés par `on_head` dès `_human_moves` ; `FACTORS = (1, 2, 4)` ; `/game` d'un PGN déjà en fiche
→ `stored_game` (log `board_game stored id=…`, hash dupliqué de `chess_router._game_hash`).
L'anticipation garde la boucle des 3 passes (temps de réponse ×1, ×2, ×4). Tests : 654 verts.

Tronçon 05 fait (`interfaces/board/index.html` seul) : `orientToPlaying()` (orientation = « Je
joue », appelée au changement de `#playing`, dans `openStored`, `restoreState` et à la réponse de
`/game` portant `playing`) ; ⟲ → `newPosition()` ; `bottom` dans `POST /position` ; pinceau `grey`,
flèches numérotées (`label`) + cercle + réponse bleue si `state.anticipated` et case
`#show-anticipation` ; statut « 🔮 coups adverses probables » ; panneau `#replies` ouvert aussi
sur `anticipated` (`hasReplies()`) ; miniatures de `/game` si `minis`. Ajout hors lettre : si
`orientToPlaying` change l'orientation (changement de `#playing`, `/game`), `newPosition()` est
relancé pour que l'analyse suive le nouveau camp du bas. Rendu réel : tronçon 06.

## Décisions arrêtées (lot 1, Nico, 2026-11-25)

- Anticipation : jusqu'à 3 coups adverses (p ≥ 10 %), chacun avec pièce cerclée + flèche grise
  semi-transparente numérotée 1, 2, 3 ; la réponse du joueur du bas en flèche bleue portant le
  même numéro. Raison : demande de Nico (« les coups les plus probables et leur réponse »).
- Orientation automatique sur « Je joue » (fiche ouverte depuis `/parties` comprise) ; ⟲ peut
  toujours retourner, l'anticipation suit le joueur du bas. Raison : sinon une partie avec les
  noirs anticipe les coups de Nico lui-même.

- Tour adverse (révisé, Nico 2026-11-25 : « tout est trop lent ») : **aucune analyse live du
  camp au trait** ; la passe calcule seulement l'anticipation (3 coups Maia les plus probables,
  p ≥ 10 %, + réponse moteur du joueur du bas, une analyse `root_moves`). Restent les flèches
  gratuites déjà connues de la page : bleu tiré de `evals` (/game, /eval), flèche d'erreur,
  cercle du coup joué. Case « Anticipation » dans le menu, cochée par défaut.

- Périmètre (Nico, 2026-11-25, « tout dans le 68 ») : anticipation + vitesse de l'échiquier
  (évaluation, flèches, PGN collé) + vitesse de l'analyse Telegram. Raison : Nico utilise lichess
  parce qu'ARIA est trop lent. Mesures : `audit_joueur_du_bas.md` §6.

## Décisions arrêtées (lot 2, Nico, 2026-11-25 : « tout ce qui peut accélérer »)

- Telegram : bilan sans rappels mémoire ; mesurer puis alléger les écritures ; recherche
  explosive plus courte ; préchargement embedder + Maia au démarrage (ajout, même logique).
- Échiquier : Stockfish gardé ouvert pour `/eval` ; piège / stratégie publiés dès qu'ils sont
  prêts, passe ×8 supprimée ; PGN collé déjà en fiche = chargé comme `/stored`.
- Machine : les deux `cuire_portraits.js` (Symbiose) restent (Nico).
- Hors sprint, faits le 2026-11-25 : Anthropic en `claude-haiku-5-5` (`5a59749`), DeepSeek en
  dernier des chaînes (`12b7f4e`).

## Découpage (validé par Nico, 2026-11-25)

1. Bilan Telegram : durées par étape au journal, bilan sans rappels mémoire, préchargement.
2. Écritures : mesure sur une copie du palace, allègement sans changer ce qui est écrit.
3. Recherche explosive : réglage plus court retenu seulement s'il retrouve les mêmes coups sur
   un corpus de fiches.
4. Échiquier serveur : anticipation, `/eval` persistant, publication précoce, sans ×8, PGN connu.
5. Échiquier page : orientation, retournement, flèches et panneau d'anticipation.
6. Run live (Nico).

## Questions ouvertes

Aucune pour l'exécution. Contexte LLM (hors sprint, 2026-11-25) : DeepSeek à court de crédit
(dernier succès vu le 2026-11-20 07:30, premier 402 vu le 2026-11-25 14:49 [journaux collés dans
les transcripts seulement]) ; recharge ou non : à Nico, d'après le tableau d'usage DeepSeek.
Anthropic : 18,97 $ restants, ~0,013 $ par analyse sur Haiku 4.5 [n=2]. Faits : Anthropic en
`claude-haiku-5-5` (`5a59749`), DeepSeek en dernier des chaînes (`12b7f4e`), `ask-deepseek` /
`write-deepseek` sur Haiku 5.5 (`626ec49`). Prise d'effet côté ARIA au redémarrage du service.

## Défauts retenus (non questionnés, repris dans les kickoffs)

- Coup adverse : pièce cerclée + flèche grise semi-transparente ; réponse : flèche bleue (couleur
  du meilleur coup) avec pastille.
- Panneau sous l'échiquier (celui des réponses au coup explosif) : un coup anticipé par ligne,
  probabilité, variante cliquable (`line_san`).
- Serveur : `bottom` dans `/position` ; camp au trait ≠ bas → passe `live.anticipate_pass` à la
  place d'`analyse_pass` (réutilise `reply_distribution` + `_human_replies`, Elo Maia du camp au
  trait) ; `bottom` dans la clé du cache.
