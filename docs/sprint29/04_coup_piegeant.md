# Sprint 29 — Tronçon 04 : coup le plus piégeant (espérance humaine Maia)

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_sprint29.md` §2.

## Objectif

L'occasion explosive retenue est le coup qui rapporte le plus **face à un humain** de
l'Elo adverse, quitte à être moins bon sur jeu parfait. Recherche sur **toute la
partie**, **sans budget**, jusqu'à **3 occasions** affichées. La réponse logique
montrée est la réponse humaine la plus probable (traite #91).

## Définitions

- Distribution humaine : politique Maia-2 (modèle rapid déjà chargé par
  `difficulty._load`) dans la position APRÈS le candidat, `elo_self = elo_oppo = Elo
  adverse` (en-tête PGN, sinon `DEFAULT_ELO`). On garde les réponses les plus probables
  jusqu'à 90 % de probabilité cumulée, 6 au plus, renormalisées.
- Espérance humaine E(coup) = Σ P(réponse) × % de gain de Nico après la réponse
  (Stockfish, `root_moves` = ces réponses, MultiPV, `_DEEP_TIME`).
- Admissible : perte ≤ 15 pts vs le meilleur coup (jeu parfait) **et**
  E(candidat) ≥ E(meilleur coup) + 10 **et** la ligne de la réponse humaine la plus
  probable donne un avantage clair (`clear_advantage`, règle gardée).
- Classement entre candidats et entre positions : gain = E(candidat) − E(meilleur coup).

## Fichiers à toucher

### `chess_coach/difficulty.py`
- Nouvelle fonction batchée `reply_distribution(fens: list, elo: int, models_dir) ->
  list[list[tuple[uci, p]]]` sur le modèle de `_probabilities` : softmax masqué sur les
  coups légaux, indices → UCI via l'inverse de `all_moves_dict`, **démiroir**
  (`inference.mirror_move`) quand c'est aux noirs. Même `_load` paresseux.

### `chess_coach/explosive.py`
- `find_explosive(plies, nico_color, engine_path, opponent_elo, models_dir)` :
  éligibles = coups de Nico, **tous les numéros de coup** (supprimer `_MAX_MOVE_NUMBER`),
  35 ≤ win_before ≤ 75, loss < 10 ; **supprimer `_BUDGET`** et sa vérification.
- `_search_position` : candidats comme aujourd'hui (MultiPV + coups de forme), filtre
  perte ≤ 15 (`_TRAP_WINDOW`) ; E calculée pour le meilleur coup et pour les candidats
  approfondis (`_MAX_DEEP` inchangé) ; `_admissible` / `score` remplacés par la règle
  ci-dessus (score = gain). Les champs d'affichage existants restent remplis quand ils
  ont un sens (sacrifice, forçant, ligne) ; `trap_reply_san` / `replies` deviennent les
  réponses humaines (san, probabilité, ligne, % de gain Nico).
- Maia indisponible (exception au chargement ou `models_dir` None) → aucune occasion,
  `log.warning`, l'analyse continue. Supprimer la logique « prise naturelle / piège »
  devenue sans usage si plus rien ne l'appelle.

### `chess_coach/analysis.py`
- `analyze` : passer l'Elo adverse et `maia_models_dir` à `find_explosive`.
- `select_critical` : jusqu'à **3** occasions explosives en bonus (meilleur score
  d'abord), sans évincer les a/b/c/e, en sautant celles dont la position est déjà retenue.
  Docstring à jour.

### `execution/routers/chess_router.py`
- `_explosive_lines` : « réponse humaine la plus probable : Bxe5 (62 %) » ; ligne
  « espérance face à un humain : Nico X % (meilleur coup : Y %) » ; une ligne par
  réponse humaine « si Bxe5 (62 %) : <ligne>, Z % pour Nico ». Retirer les lignes qui
  n'ont plus de donnée.
- Consigne d'occasion explosive : remplacer « pourquoi la bonne réponse est difficile »
  par l'explication des réponses humaines probables qui perdent ; garder « ne le présente
  jamais comme le meilleur coup ».
- `_caption` sorte d inchangée (flèche orange inchangée).

## Tests à ajouter (cas nominal)

- `reply_distribution` : test réel `skipif` poids Maia absents (comme
  `test_assign_difficulty_real_maia`) : probabilités ∈ ]0,1], somme ≤ 1, coups légaux.
- `explosive` : test unitaire de l'admissibilité / du gain avec E injectées (pas de
  moteur) : un candidat perte 12, E +15 vs meilleur coup → retenu ; E +5 → rejeté.
- `select_critical` : 4 occasions fournies → 3 ajoutées, la plus faible écartée.
- Adapter les tests explosifs existants (`test_explosive_*`) à la nouvelle règle ; un
  test qui n'a plus de sens est supprimé en le disant dans le livrable.

## Hors-scope (NE PAS faire)

- Ne pas toucher aux sortes a/b/c/e ni à la règle d'avantage clair.
- Pas de nouveau réglage configurable (constantes de module).
- Pas de légende (tronçon 05).

## Critère de fin

`pytest tests/ -q` vert ; `chess_explosive` loggue le nombre de positions examinées
et retenues (format de log existant, sans `duration` de budget si devenu inutile).
