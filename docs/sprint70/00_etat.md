# Sprint 70 — état du sprint

**Phase** : A (audit + arbitrages), ouverte le 2026-11-27.
**Sujet** : meilleur coup à la sortie du répertoire (demande de Nico au run live du sprint 69) :
A = ligne 📚 du bilan, B = fiche de la position de sortie avec la ligne du meilleur coup
prolongée et sa pointe. Entrée : `docs/sprint69/03_retour_run_live.md`.
**Branche** : `feat/sprint70-sortie-repertoire` (depuis `main`, tag `sprint-69`).

## Contexte hérité

- Sprint 69 clos (tag `sprint-69`), run live validé le 2026-11-27 : ligne 📚 juste sur la partie
  BaguetteCopter – jaypril17 (Philidor, Bird Gambit) ; ligne ❗ non vue → dette 69-1.
- Sprint 63 : run live `docs/sprint63/02_run_live.txt` toujours à jouer à la prochaine partie neuve.
- 4 retours 👎 en attente : `/amelioration` après ce sprint.

## Feuille de route (validée par Nico, 2026-11-20, reprise du sprint 66)

Nico, 2026-11-20 : « les choses une après l'autre, sans rien oublier ». Un sujet par sprint, dans l'ordre :

1. ~~62 : mat raté (62-1)~~ : fait au sprint 62.
2. ~~63 : suivi Telegram avec moteur (62-2 + 61-1)~~ : code livré au sprint 63, run live non fait.
3. ~~64 : `/parties` sans échiquier (62-4, 62-5, 62-6)~~ : fait au sprint 64, run live validé.
4. ~~65 : `/parties` → échiquier ARIA avec l'analyse stockée (62-3 + 62-7)~~ : fait au sprint 65, run live validé.
5. ~~66 : miniatures jouables dans l'échiquier (62-8)~~ : fait au sprint 66, run live validé.
6. ~~67 (ajouté par Nico, 2026-11-25) : boucle de rétroaction (66-3) : réactions 👍 / 👎 sur
   les messages Telegram, enregistrées dans le palace, traitées ensemble en conception~~ : fait au sprint 67, run live validé.
7. ~~68 : échiquier centré joueur du bas + réponses adverses (61-4 + 62-9), vitesse~~ : fait au sprint 68, run live validé.
8. ~~69 : répertoire connu d'ARIA (61-5 + 61-10)~~ : fait au sprint 69, run live validé (ligne ❗ non vue, dette 69-1).
8 bis. 70 (ajouté par Nico, 2026-11-27) : meilleur coup à la sortie du répertoire (A + B de
   `docs/sprint69/03_retour_run_live.md`).
9. Texte du coach : 61-6, 61-8, 61-11, 61-2 ; progression 61-7 ; noms d'ouverture 61-9.
10. 62-10 Iona : contenu à préciser par Nico. 60 (lecture d'image) reste suspendu.

## Dettes

| # | Dette | Constat | Piste |
| 61-1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : faits de la position N absents | Code livré au sprint 63 ; reste ouverte jusqu'au run live `docs/sprint63/02_run_live.txt` |
| 61-2 | Motif « fourchette » trompeur | `assign_motifs` tague Qxe7+ fourchette | Revoir l'usage des motifs dans le Pourquoi |
| 61-3 | Clouage relatif et mat hors pointe | Pointe limitée au gain matériel et au clouage absolu | Étendre si un cas réel le demande |
| 61-6 | Phrase « négligé » du Pourquoi | Commente encore le départ (Be7), pas la pointe | Quand une pointe existe, (2) porte sur la pointe |
| 61-7 | Progression fausse à la réanalyse | `games=439` répété, bloc repris de la partie précédente | Recompter quand la fiche est remplacée |
| 61-8 | Bilan inverse le camp | « 5.d5 (−21 pts pour l'adversaire) », coup de Nico | Données du tournant plus explicites |
| 61-9 | Même ouverture, deux noms | Portsmouth Gambit / Wing Gambit Deferred après 3.b4 | Regrouper dans `opening_group` |
| 61-11 | Texte LLM inventé | « pion d7 passé », « Be7!? sacrifie 3 pions » | Faits plus contraints |
| 62-2 | Suivi Telegram invente la position | « j'avais mat en 2 » → « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp | Code livré au sprint 63 ; reste ouverte jusqu'au run live `docs/sprint63/02_run_live.txt` |
| 63-1 | Revendication sans position citée | « j'avais mat en 2 » seul reste au LLM sans moteur (décision 1a) | Balayage des coups de Nico si un cas réel le demande |
| 66-1 | Miniatures d'un PGN collé | `/game` ne refait pas l'analyse complète : pas de miniatures hors fiche | Retrouver la fiche par le hash des coups si Nico le veut |
| 66-2 | Miniatures des fiches anciennes | Fiches d'avant le sprint 66 sans `minis_json` | Réanalyse ~1 min/partie [6 runs] si Nico le veut |
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
| 68-4 | Pointe réduite à « gain matériel + clouage absolu » | `combination.point_of` (sprint 61) : la pointe = première prise qui fixe un gain de matériel, clouage absolu en option. Manque : pointe qui mate, qui ne prend rien tout de suite, fourchette, déviation, coup intermédiaire, clouage relatif. Nico 2026-11-26 : « la pointe ne vient pas toujours d'un clouage » | Reconnaître la pointe par son effet ; regroupe 61-3 et 67-2. Étape 9 (texte du coach) ou avant si Nico le veut |
| 68-5 | Défilement de l'échiquier sur téléphone | Correctif `b5c5c23` (défilement porté par `body`) non confirmé à part au run live | Vérifier à la prochaine ouverture sur téléphone |
| 69-1 | Ligne ❗ jamais vue en live | Codée et testée au sprint 69 ; aucune partie du run live ne rejouait un coup habituel mauvais | À confirmer à la prochaine partie qui rejoue 5.d5 (Portsmouth) ou 6.exd5 (Göring) |
| 69-2 | Fiche « le cavalier a besoin de sécurité » pour un sacrifice | 👎 2026-11-27 09:51 sur Nd5+ ; la réponse d'ARIA invente « défendu par e4 » et nie avoir les analyses des positions 1, 2, 4 | `/amelioration` (4 👎 en attente) |

## Décisions arrêtées

- 2026-11-27 : sujet = A + B du retour de run live du sprint 69 (demande Nico).

## Questions ouvertes

Voir §REPRISE.

## §REPRISE

Lire `audit_sortie_repertoire.md`, puis remonter les arbitrages à Nico.
