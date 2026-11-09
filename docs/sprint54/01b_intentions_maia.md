# Sprint 54 — tronçon 01b : intentions élargies et trace Maia

Lire avant : `CLAUDE.md`, `docs/sprint54/00_etat.md`, `docs/sprint54/01_idee_et_oubli.md`
(tronçon 01, déjà commité : `_intent_line`, `_relative_pins` dans `execution/routers/chess_router.py`).
Branche : `feat/sprint54-pensee-erreur`.

## Pourquoi (retour Nico, 2026-11-09)

Le tronçon 01 ne connaît que 3 intentions (met à l'abri, défend, décloue). Un coup se joue pour
bien d'autres raisons (développer, attaquer, activer une pièce, ouvrir une ligne…), et une erreur
de calcul part toujours d'une idée. Arbitrages Nico :
- élargir les intentions calculées par le code ;
- la consigne présente ces faits comme des **indices**, pas une liste fermée ;
- **Maia est utilisé** (revient sur la décision 1) pour deux choses : probabilité du coup à l'Elo
  de Nico, et suite humaine probable après le coup (trace du calcul de tête) ;
- **seuil du coup 10 gardé** : rien de Maia pour `move_number <= 10` (`_OPENING_MOVES`).

## 1. Intentions élargies (`_intent_line`, segment « ton coup : »)

Ajouter, après les intentions existantes, sur `p.fen_before` / coup `p.san` (pièce jouée = X) :
- `développe X` : cavalier ou fou qui quitte sa case de départ (b1, g1, c1, f1 / b8, g8, c8, f8) ;
- `attaque Y` : reprendre le fait « attaque … » déjà calculé par `_move_fact_items` (comme
  « décloue », filtré par préfixe) ;
- `contrôle d4, e5` : cases centrales (d4, d5, e4, e5) attaquées par X après le coup et pas
  avant (par X) ;
- `vise le roi` : X attaque après le coup une case voisine du roi adverse qu'il n'attaquait pas avant ;
- `active X (N → M cases)` : cases attaquées par X (hors cases occupées par son camp) passent de
  N à M avec M − N ≥ 3 ;
- `libère Z` : autre pièce à longue portée Z (fou, tour, dame) de Nico dont les cases attaquées
  augmentent après le coup (ouverture d'une colonne ou d'une diagonale).

Ne pas modifier `_move_fact_items`.

## 2. Trace Maia (seulement si `p.move_number > 10` et Maia disponible)

Nouveau segment de la ligne « idée du coup joué », après « après ton coup » :

    Maia : coup choisi par N % des joueurs de ton niveau ; suite probable : 14.Nf3 (attaque …) 14...Qe7 (…)

- **N** : `p.played_p` (déjà calculé, Maia-2 à l'Elo de Nico), arrondi en %.
- **Suite probable** : depuis la position après le coup de Nico, la réponse adverse la plus
  probable selon Maia, puis le coup suivant de Nico le plus probable (2 demi-coups), avec leurs
  faits via `_move_facts`. Calcul par `reply_distribution` (`chess_coach/difficulty.py`), premier
  élément de chaque distribution, Elo = celui utilisé pour `assign_difficulty`.
- **Où calculer** (hypothèse réfutable) : dans `chess_coach/analysis.py`, sur le chemin Maia
  existant, pour les positions critiques de Nico à `best_line_san` non vide et
  `move_number > 10` ; résultat stocké sur la position critique (nouveau champ, ex.
  `human_line_san: list`). Le routeur ne charge pas Maia lui-même, il formate.
  Deux passes batchées (réponses adverses de toutes les erreurs, puis suites de Nico).
- Sans Maia (échec ou absent) ou coup ≤ 10 : segment omis, sans erreur.

## 3. Consigne « Pourquoi : » (même endroit que tronçon 01)

Remplacer l'énumération fermée « (menace du coup adverse précédent, met à l'abri / défend /
décloue, temps …) » par : les faits de « idée du coup joué » sont des **indices** (menace du coup
adverse, faits de « ton coup », temps : rapide = réflexe, long = réfléchi ; Maia : coup fréquent
à ton niveau = coup naturel, rare = idée personnelle ; « suite probable » = ce que Nico avait sans
doute calculé) ; retenir celui qui explique le mieux le coup, au conditionnel ; si aucun ne
colle, dire que l'idée n'est pas claire plutôt que d'en inventer une. Le reste de la consigne 3
temps est inchangé.

## Hors scope

Prompt AnalystAgent, `soul.md`, `_move_fact_items`, seuil Maia des autres usages, légendes.

## Tests (cas nominal)

- `_intent_line` sur une position simple : un coup de développement donne `développe X`, et un
  coup qui ouvre la diagonale d'un fou donne `libère <fou>`. La ligne de référence du tronçon 01
  (9...Qd7) contient toujours ses faits.
- Formatage du segment Maia : position critique avec `played_p` et `human_line_san` fournis
  (sans charger Maia) → `Maia : coup choisi par N %` et `suite probable :` présents ; coup ≤ 10 → absent.
- `pytest tests/ -q` vert.

## Critère de fin

Tests verts ; à valider en run live (02) : sur une erreur après le coup 10, le « Pourquoi : »
s'appuie sur un indice présent (dont Maia) sans en inventer.
