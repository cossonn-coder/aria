# Sprint 29 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-22), prête pour `/sprint-auto sprint 29`
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
| 04 | `04_coup_piegeant.md` — espérance humaine Maia, toute la partie, 3 occasions | ⏳ |
| 05 | `05_legende.md` — explication en légende sous chaque image | ⏳ |
| 06 | `06_run_live.md` — run live (Nico), messages : `run_live_parties.txt` | ⏳ |

## Dettes

- Fermées si le sprint passe : #71 (`print()` kernel), #91 (réponse logique = bonne
  réponse), #100 (motifs) ; #74, #73/#86 non traitées.
- Nouvelles : #103 `handle_event` synchrone bloque la boucle du bot pendant l'analyse
  (devient plusieurs minutes sans budget) ; #104 un échec d'envoi de photo interrompt
  l'envoi du texte qui suit (`images_text`).

## Questions ouvertes

- (aucune)

## §REPRISE

Lire `CLAUDE.md`, `context_kickoff_sprint_29.md`, ce fichier.
Tronçon 01 fait (dispatcher `log.exception` + type dans `error`, logger kernel, `send` → `_deliver` + attente par chat_id).
Note : si la livraison de l'attente échoue à son tour, c'est la réponse courante qui est gardée (la plus récente écrase).
Tronçon 02 fait : `chess_coach/motifs.py` (`tag_motifs`, portage cook.py/util.py filtré + 11 mats ajoutés, ordre `_EXTRA_MATES`), 7 tests `tests/chess_coach/test_motifs.py`. Non branché.
Adaptation : `is_mate` exige que le camp mat soit l'adversaire (une PV pourrait finir sur un mat contre Nico).
Mats ajoutés : heuristiques « zone du roi contrôlée uniquement par les pièces du motif » ; seul `triangleMate` est testé.
Tronçon 03 fait : `analysis.assign_motifs` (PV coupée par `clear_advantage`, appelée dans `analyze` avant `find_explosive`), clé `motifs` dans `plies_json`, `LABELS` motifs + « Mats », `hanging` = « Gain de matériel », `MATE_LABELS` (noms des mats, hors classements), `Trial.mate`, `_mean` = thèmes à ≥ 1 épreuve, ligne `motifs :` du bloc enrichi.
Vérifié sur 2 parties réelles (run live sprint 28) : motifs non vides (fork, pin, sacrifice, mate…).
Prochaine étape : tronçon 04 (`04_coup_piegeant.md`), puis 05, puis run live 06 par Nico.
