# Sprint 29 — état de conception

**Phase** : B' — retours run live figés (OK Nico 2026-10-22), tronçons 07-11 prêts pour `/sprint-auto sprint 29`
**Branche** : `feat/sprint29-coach-motifs` (créée sur OK de Nico)

## Décisions arrêtées

- Périmètre (Nico, 2026-10-22) : trois sujets échecs — **motifs tactiques** (#100),
  **coup le plus piégeant**, **explication en légende** sous chaque image — plus deux
  compléments fiabilité : **erreur kernel vide** (trace logguée, `print()` kernel #71) et
  **réponse perdue signalée** (échec des réessais Telegram).
- Audit : `audit_sprint29.md` (HEAD `d2a3150`).
- Motifs : **compléter** les thèmes. « Pièces en prise » devient le motif « gain de
  matériel » ; motifs ajoutés ; situations (punir, ouverture, convertir, finale) et
  Résultats gardées. **Global = moyenne des thèmes ayant ≥ 1 épreuve** (anti-dilution).
  Liste de Nico (2026-10-22) = thèmes puzzles Lichess : gain de matériel, fourchette,
  clouage/enfilade, découverte, sacrifice, pièce enfermée, pion avancé, attaque f2/f7,
  capture du défenseur, échec double, roi exposé, attraction, dégagement, coup
  colinéaire, déviation, interception, coup intermédiaire, rayon X, + mats nommés
  (Anastasia, arabes, couloir, arbalète, deux tours, Boden, coin, deux fous, Cozio,
  épaulettes, hameçon, mise en boîte, Pillsbury, Morphy, opéra, guéridon, triangle,
  Vukovic, étouffée).
  ⚠ La plupart exigent la **variante** (PV) : la détection par rejeu sans PV est
  abandonnée → détection à l'analyse (PV `pv_uci` disponible) et stockage dans
  `plies_json`. Piste : porter `tagger/cook.py` de lichess-puzzler (python-chess, AGPL,
  usage perso) qui couvre tous les motifs non-mats et 8 mats ; les 11 autres mats sont à écrire.
  Copie de référence : `docs/sprint29/ref/` (cook.py, util.py, model.py).
  Format Lichess : partie qui démarre AVANT le coup adverse précédent, mainline =
  [coup adverse joué, meilleur coup de Nico, suite de la PV…] ; pov = camp de Nico.
- Classements : **un par motif**, **mats regroupés** en un classement « Mats » (nom du
  mat affiché dans l'épreuve). Global = moyenne des thèmes ayant ≥ 1 épreuve.
- Rétroactivité : **non**. Motifs pour les parties analysées après le sprint ; les 14
  fiches saison 1 gardent les thèmes de situation + Résultats (et la règle actuelle
  de « pièces en prise », renommée « Gain de matériel »). Aucune écriture palace hors
  analyse normale.
- Budget de la recherche explosive : **aucun** (Nico : temps d'analyse indifférent).
  Vérifié : aucun timeout dans le pipeline (kernel / dispatcher / interface).
- Coup piégeant : **espérance humaine Maia** — E = Σ P_maia(réponse, Elo adverse) ×
  % de gain Nico. Admissible : perte ≤ 15 pts sur jeu parfait et E(candidat) ≥
  E(meilleur coup) + 10. Réponse logique affichée = réponse humaine la plus probable
  (traite #91). Règle d'avantage clair gardée pour la variante montrée.
- Occasions explosives : **toute la partie** (coup 1 au dernier), **Maia partout**,
  jusqu'à **3 occasions** affichées (les plus belles).
- Légende : légende = ligne factuelle + entrée « Position N » du LLM ; texte final =
  ancre + Niveau + Progression ; > 1024 car. → coupure à la dernière phrase + « … » ;
  entrée introuvable → affichage actuel.
- Réponse perdue : gardée en RAM par chat_id, **livrée avant la réponse suivante**
  avec « ⚠️ Ma réponse précédente n'avait pas pu partir : » ; log ERROR à l'échec.
  Perdue au redémarrage (accepté).
- Erreur kernel vide : `log.exception` dans le dispatcher (type + trace + router),
  `print()` du kernel → logger (#71). Sans arbitrage.
- Réglages par défaut (figés, sans objection de Nico) : Maia indisponible → aucune
  occasion explosive + WARNING ; positions éligibles non décidées (35-75 %) ; réponses
  Maia jusqu'à 90 % cumulés, 6 max ; jusqu'à 6 images (3 critiques + 3 occasions).

## Carte des tronçons

| # | Kickoff | Statut |
|---|---------|--------|
| 01 | `01_fiabilite.md` — trace dispatcher, logger kernel, réponse perdue livrée au message suivant | ✅ (non commité, 327 verts) |
| 02 | `02_tagueur_motifs.md` — `chess_coach/motifs.py` (portage cook.py + 11 mats) | ✅ (non commité, 334 verts) |
| 03 | `03_motifs_profil.md` — motifs à l'analyse, `plies_json`, classements, Global pondéré | ✅ (non commité, 336 verts) |
| 04 | `04_coup_piegeant.md` — espérance humaine Maia, toute la partie, 3 occasions | ✅ (non commité, 337 verts) |
| 05 | `05_legende.md` — explication en légende sous chaque image | ✅ (non commité, 340 verts) |
| 06 | `06_run_live.md` — run live (Nico), messages : `run_live_parties.txt` | ✅ fait 2026-10-22 (4 parties), retours → phase A' |
| 07 | `07_explosif_hybride.md` — règle hybride (ancienne règle OU gain Maia ≥ 5) | ✅ (non commité, 341 verts) |
| 08 | `08_precision_meilleur_pire.md` — précision Lichess, meilleur coup (Maia + Stockfish), pire coup | ✅ (non commité, 343 verts) |
| 09 | `09_legende_variante.md` — légende : idée générale + variante expliquée | ⏳ |
| 10 | `10_arret_rapide.md` — `os._exit(0)` après arrêt PTB | ⏳ |
| 11 | `11_run_live_retours.md` — run live (Nico) | ⏳ |

## Dettes

- Fermées si le sprint passe : #71 (`print()` kernel), #91 (réponse logique = bonne
  réponse), #100 (motifs) ; #74, #73/#86 non traitées.
- Nouvelles : #103 `handle_event` synchrone bloque la boucle du bot pendant l'analyse
  (devient plusieurs minutes sans budget) ; #104 un échec d'envoi de photo interrompt
  l'envoi du texte qui suit (`images_text`).
- Nouvelles (retours run live) : #105 quarantaine HNSW récurrente de `mempalace_drawers`
  (`hnsw:sync_threshold` 50 000 → HNSW jamais persisté) ; #106 le LLM écrit « finale »
  sur une position classée milieu de partie.

## Phase A' — retours du run live (ouverte 2026-10-22)

Audit : `audit_retours_run_live.md`. Quatre sujets, tronçons 07+ à concevoir :
1. Occasions explosives : 0 trouvée (gain max 5,9 < seuil 10 [n=4]). Nico : seuil 5,
   adapté à l'Elo, retrouver les idées risquées d'avant (règle sprint 28).
2. Légende : gardée (Nico) ; ajouter variante textuelle expliquée + idée générale.
3. Précision : se rapprocher de chess.com (actuel = moyenne arithmétique).
4. Arrêt aria.service lent : diagnostic py-spy autorisé (carte blanche Nico), en cours.

## Questions ouvertes

- (aucune)

## Décisions phase A'

- Q1 (Nico, 2026-10-22) : règle hybride — admissible si ancienne règle sprint 28
  (sacrifice ≥ 1 ou piège ≥ 10, fenêtre 5/15, avantage clair) OU gain Maia ≥ 5 ;
  seuil fixe (Maia reçoit déjà l'Elo adverse).
- Q2 (Nico) : précision = algorithme Lichess complet (pas de chiffres chess.com pour
  calibrer) ; afficher en plus le meilleur et le pire coup de Nico de la partie.
- Q3 (Nico) : entrée de légende = idée générale + variante du meilleur coup expliquée
  coup par coup ; chiffre clé supprimé ou réduit à « 57 % → 75 % ».

## §REPRISE

Lire `CLAUDE.md`, `context_kickoff_sprint_29.md`, ce fichier.
Tronçon 01 fait (dispatcher `log.exception` + type dans `error`, logger kernel, `send` → `_deliver` + attente par chat_id).
Note : si la livraison de l'attente échoue à son tour, c'est la réponse courante qui est gardée (la plus récente écrase).
Tronçon 02 fait : `chess_coach/motifs.py` (`tag_motifs`, portage cook.py/util.py filtré + 11 mats ajoutés, ordre `_EXTRA_MATES`), 7 tests `tests/chess_coach/test_motifs.py`. Non branché.
Adaptation : `is_mate` exige que le camp mat soit l'adversaire (une PV pourrait finir sur un mat contre Nico).
Mats ajoutés : heuristiques « zone du roi contrôlée uniquement par les pièces du motif » ; seul `triangleMate` est testé.
Tronçon 03 fait : `analysis.assign_motifs` (PV coupée par `clear_advantage`, appelée dans `analyze` avant `find_explosive`), clé `motifs` dans `plies_json`, `LABELS` motifs + « Mats », `hanging` = « Gain de matériel », `MATE_LABELS` (noms des mats, hors classements), `Trial.mate`, `_mean` = thèmes à ≥ 1 épreuve, ligne `motifs :` du bloc enrichi.
Vérifié sur 2 parties réelles (run live sprint 28) : motifs non vides (fork, pin, sacrifice, mate…).
Tronçon 04 fait : `difficulty.reply_distribution` (top Maia jusqu'à 90 % cumulés, 6 max, p brutes), `explosive` réécrit (E = Σ p renormalisée × win Nico, admissible perte ≤ 15 + E ≥ E(meilleur) + 10 + avantage clair sur la réponse la plus probable, score = gain, toute la partie, sans budget, Maia absent → WARNING + aucune occasion), `select_critical` ≤ 3 d en bonus, router (réponse humaine la plus probable, espérance, lignes « si X (p %) »), consigne d mise à jour.
Champs `trap` / `volatility` supprimés de `ExplosiveMove` ; ajout `expected`, `best_expected`, `p` dans `replies`. Probabilité affichée = p brute Maia.
Écart : `difficulty._load` n'appelait pas `net.eval()` (dropout actif → probabilités Maia aléatoires d'un appel à l'autre, difficulté du sprint 28 comprise) ; corrigé.
Tests supprimés : `test_explosive_smith_morra_nd5`, `test_explosive_early_queen_nf6`, `test_explosive_excludes_first_pass_best` (Nd5 / Nf6 ne sont plus des occasions selon Maia ; l'exclusion ne se teste plus sans occasion réelle).
Mesure : 0 occasion sur les 2 premières parties de `run_live_parties.txt` [n=2] (gains tous < 10) ; passe explosive 57 s et 37 s [n=2].
Tronçon 05 fait : `chess_router._split_entries` (après `_to_english`) : entrée « Position N — » (gras Markdown et tirets –/- tolérés) → légende = ligne factuelle + saut de ligne + entrée sans son marqueur ; fin d'entrée = entrée suivante ou ligne « Niveau » ; > 1024 → `_fit_entry` (dernière phrase + « … ») ; une entrée 1…len(images) manquante → repli complet ; `log.info` `chess_caption_split OK/FALLBACK`. Consigne : marqueur en début de ligne, ne pas recopier la ligne factuelle. 3 tests.
Choix : le marqueur « Position N — » est retiré de l'entrée (la ligne factuelle le porte déjà) ; une entrée « Position K » avec K > nombre d'images reste dans le texte.
Phase A' close, kickoffs 07-11 figés. Prochaine étape : `/sprint-auto sprint 29` (tronçons 07 → 10), puis run live 11 par Nico.
Tronçon 07 fait : `ExplosiveMove.trap` réintroduit (prise naturelle en `root_moves=[capture]`, piège = win adverse PV principale − win après la prise), `_admissible` hybride (avantage clair ET (règle sprint 28 `_WINDOW` 5 / `_TRAP_MIN` 10 OU perte ≤ 15 + gain Maia ≥ `_GAIN_MIN` 5)), score = gain Maia inchangé ; router : ligne « pari : … » si gain < 5, consigne d « idée risquée ». Test paramétré `test_explosive_admissible_hybrid` (remplace `…_human_expectation`).
Mesure (4 parties `run_live_retours_parties.txt`, avant `select_critical` qui en garde ≤ 3) : 5 / 2 / 1 / 4 occasions [n=4] ; 11 sur 12 admises par la seule règle sprint 28 (gain Maia de −13,7 à +0,6), 1 par Maia (Ng4, +5,4).
Tronçon 08 fait : `summary._game_accuracy` (Lichess : fenêtres glissantes, poids = écart-type population borné 0,5-12, (pondérée + harmonique) / 2, plancher 1 %/coup) → clé `accuracy` ; `worst_move` / `worst_win_before` / `worst_win_after` (perte max ≥ 10) ; `explosive.find_best_move` + `_problem_score` → `GameAnalysis.best_move` (`BestMove`), clés `best_move`, `best_defense`, `best_defense_p`, `best_reply_played` ; router : `_level_line` = `précision Nico : N %`, ligne 🎯 `_moves_line` avant le bloc Progression. 2 tests ajoutés, 4 tests router ajustés (ligne 🎯).
Choix non tranchés par le kickoff : score Maia = Σ sur les seules **fautes** (écart ≥ 5) ; aucun meilleur coup si score max ≤ 0 ; défense hors des réponses Maia gardées (90 % cumulés) → p = 0, affichée « 0 % de chances ». `summary_text` (document indexé) garde la précision par phase.
Mesure (4 parties `run_live_retours_parties.txt`) [n=4] : précision 91 / 49 / 88 / 86 % (audit : 91 / 52 / 89 / 85 sans pondération) ; meilleur coup 20.Kd2 (score 44, défense Be6, joué Bxg2), 14.Qxb7 (14), 10.Nb5 (8,5), 33...Qd8 (18,5) ; pire coup 17.Be5 (51 → 37), 39.Bb2 (88 → 2), 28.Ndf7 (85 → 63), 31...Rxa5 (43 → 26) ; passe meilleur coup 15-21 s.
⚠ La meilleure défense est hors du top Maia sur les 4 parties [n=4] (biais de sélection : le score est maximal quand les humains ratent la défense) → « 0 % de chances » systématique ; à arbitrer au run live (afficher « < 5 % » ou la p brute non tronquée).
Prochaine étape : tronçon 09.
