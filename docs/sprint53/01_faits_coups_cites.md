# Sprint 53 — tronçon 01 : faits pour tous les coups cités au LLM

Lire d'abord : `CLAUDE.md`, `docs/sprint53/00_etat.md`, `docs/sprint53/audit_recits.md`.

## Objectif

Le LLM raconte mal certains coups (« Qxf1+ échange ta dame contre un cavalier » alors que le
coup gagne le cavalier, dette #187) parce qu'il ne reçoit les faits du coup joué que sur les
erreurs (sortes a/b). Donner au LLM, dans le bloc enrichi, les **faits de chaque coup qu'il est
amené à raconter**, avec la **réponse adverse réellement jouée** (c'est elle qui dit si la pièce
est reprise), et étendre la consigne « pas de prise / échange sans fait » à tout le texte.

Rien ne change dans ce que Nico voit directement (légendes, déroulé affiché) : seul le texte
envoyé au LLM (`_build_enriched`) s'enrichit.

## Fichiers à toucher

- `execution/routers/chess_router.py` : `ChessExecutionRouter._build_enriched` (l.1003), et
  éventuellement un petit helper de module.
- `chess_coach/summary.py` : exposer la liste des coups cités par le déroulé (voir 3).
- `tests/execution/test_chess_router.py`, `tests/chess_coach/test_summary.py`.

## Comportement attendu

Les faits se calculent avec le helper existant `_move_facts(fen, moves_san, move_number, color)`
(python-chess, sans moteur). Les demi-coups sont dans `analysis.plies`, indexés par `ply`
(`analysis.plies[p.ply - 1]` est déjà utilisé pour le coup précédent).

1. **Suite jouée, sur chaque position du bloc** (toutes les sortes a, b, c, d, e, piège compris,
   et les positions « réflexion longue » de `extra_thinks`) : une ligne, placée juste après
   la ligne « joué … perte … » :
   `  suite jouée, faits : <_move_facts(p.fen_before, [p.san, réponse.san], p.move_number, p.color)>`
   où `réponse = analysis.plies[p.ply + 1]` si elle existe ; sinon (dernier coup de la partie)
   le coup joué seul. Exemple attendu sur une prise sans reprise :
   `suite jouée, faits : 24.Qxf1+ (prend Nf1, échec) 24...Kh7`.
2. **Tournant (sorte e)** : la ligne « erreur adverse X : perte … » est suivie de
   `  erreur adverse, faits : <_move_facts(prev.fen_before, [prev.san], prev.move_number, prev.color)>`.
3. **Déroulé** : après la ligne `Déroulé (données) : …`, une ligne
   `Coups du déroulé, faits : <coup> ; <coup> …`, chaque coup cité par le déroulé (tournants ou
   pire coup) suivi de la réponse adverse jouée, mêmes règles qu'au point 1. Pas de ligne si le
   déroulé ne cite aucun coup. La liste des coups cités doit venir **du même calcul que
   `story_line`** (`chess_coach/summary.py:120`, seuils `_DECISIVE_LOSS`, `_NEAR_DROP_RATIO`,
   `_WORST_MOVE_MIN`) : extraire ce choix dans une fonction publique (ex. `story_plies(plies,
   nico_color)`) que `story_line` utilise à son tour. Le texte de `story_line` ne change pas
   (ses tests existants restent verts tels quels).
4. **Consigne** (`consigne` dans `_build_enriched`) : la phrase actuelle « ne dis qu'une pièce est
   prise ou épargnée que si ces faits le montrent » ne vaut que dans l'exception « Pourquoi ».
   Ajouter une règle générale, valable pour toutes les entrées **et** le Bilan : ne dire qu'une
   pièce est prise, échangée, reprise ou épargnée que si une ligne « faits » le montre (citer les
   lignes « suite jouée » et « Coups du déroulé »). Formulation libre, courte.

## Tests (cas nominaux)

- Bloc enrichi d'une position de sorte d (ou réflexion longue) dont le coup joué prend une pièce
  sans reprise : la ligne `suite jouée, faits :` contient `prend` et la réponse adverse jouée.
  Inspiration : `test_explosive_position_caption_arrow_and_enriched` /
  `test_turning_point_caption_and_enriched` (`tests/execution/test_chess_router.py`), FEN réels
  et rejouables.
- Sorte e : la ligne `erreur adverse, faits :` est présente (adapter
  `test_turning_point_caption_and_enriched`, qui a déjà le coup adverse 7...h6).
- `story_plies` : un test dans `tests/chess_coach/test_summary.py` (tournants cités = coups rendus).
- `pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Retirer le PGN du message envoyé au LLM.
- Ajouter le fait « cloue » (dette #190) ou tout autre nouveau type de fait.
- Variantes d'un seul coup (#188), relance moteur, nouvel appel Stockfish.
- Modifier les légendes ou le déroulé affichés à Nico, `_variant_line`, `_compared_lines`.
- Toucher au prompt AnalystAgent ou à `soul.md`.

## Critère de fin

Tests ajoutés verts, `pytest tests/ -q` vert ; bloc enrichi d'un test montrant les trois nouvelles
lignes (suite jouée, erreur adverse, coups du déroulé). Validation du récit : run live (tronçon 03).
