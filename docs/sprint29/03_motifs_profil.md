# Sprint 29 — Tronçon 03 : motifs dans l'analyse, la fiche et le profil

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_sprint29.md` §1.
Prérequis : tronçon 02 (`chess_coach/motifs.tag_motifs`).

## Objectif

Chaque coup de Nico porte les motifs de son **meilleur coup** ; un coup trouvé / raté
fait monter / baisser le classement de chacun de ses motifs. Les mats sont regroupés en
un classement « Mats ». Le Global devient la moyenne des thèmes ayant ≥ 1 épreuve.

## Fichiers à toucher

### `chess_coach/analysis.py`
- `PlyAnalysis` : nouveau champ `motifs: list` (défaut vide).
- Après `analyze_game` (dans `analyze`, avant la recherche explosive) : pour chaque
  coup de Nico d'indice `ply > 0`, couper la PV du meilleur coup au point d'avantage
  clair (`clear_advantage(board, line, p.win_before, p.pv_mate)` sur `p.pv_uci`, comme
  `_evidence`) ; pas d'avantage clair → `motifs = []`. Sinon
  `tag_motifs(plies[i-1].fen_before, plies[i-1].uci, pv_uci[:n])`.
  Fonction pure, pas de Stockfish supplémentaire.

### `chess_coach/summary.py`
- `plies_json` : nouvelle clé `"motifs": p.motifs` (liste de chaînes). Les fiches
  antérieures n'ont pas la clé (décision : pas de rétroactivité).

### `chess_coach/player_model.py`
- `LABELS` : ajouter un libellé français par motif (clés de `motifs.py`) et `"mates":
  "Mats"`. `"hanging"` devient « Gain de matériel » (même clé `hanging` pour la
  continuité des 14 fiches existantes) ; il reçoit les épreuves dont les motifs
  contiennent `hangingPiece`.
- `_move_themes` : si le ply a la clé `motifs`, les thèmes motifs viennent de cette
  liste (tout identifiant de mat, `"mate"` compris → `"mates"`) ; la règle actuelle
  `hanging` (tag / « x ») ne s'applique **qu'aux plies sans clé `motifs`**. Les
  thèmes de situation (`punish`, `convert`, `endgame`) inchangés.
- `Trial` : champ optionnel pour le nom du mat (ex. « mat d'Anastasia ») quand
  l'épreuve touche `mates`.
- `_mean` : moyenne des thèmes dont `trials ≥ 1` (le thème `result` compris quand il
  a des épreuves). Aucun thème joué → valeur de départ.
- Rien d'autre (badges, ouvertures inchangés).

### `execution/routers/chess_router.py`
- `_progression_block` itère déjà `LABELS` et n'affiche que les thèmes au delta non nul :
  vérifier que les motifs s'y affichent sans autre changement ; `_trial_text` ajoute le
  nom du mat quand présent (« 31.Qh7# trouvé (difficulté ≈1650), mat d'Anastasia »).
- Ligne « Position N » du bloc enrichi : ajouter `motifs : fourchette, clouage` (libellés
  français) quand la liste n'est pas vide, pour que le LLM puisse nommer le motif.

## Tests à ajouter (cas nominal)

- `test_player_model.py` : fiche dont un ply porte `motifs: ["fork"]` trouvé → le
  classement Fourchette monte ; Global = moyenne des seuls thèmes joués.
- `test_player_model.py` : fiche sans clé `motifs` → mêmes thèmes qu'avant (pièces en
  prise par la règle actuelle). Adapter les tests existants qui supposaient Global =
  moyenne des 6 thèmes.
- `test_chess_router.py` : ligne Progression d'un mat avec son nom.

## Hors-scope (NE PAS faire)

- Pas de script de réanalyse des fiches existantes, pas d'écriture palace nouvelle.
- Pas de nouveau badge, pas de changement de seuils d'épreuve.
- Pas de motif pour la recherche explosive (tronçon 04).

## Critère de fin

`pytest tests/ -q` vert. Une analyse réelle (test Stockfish existant) produit des
`motifs` non vides sur au moins un coup — à vérifier sans l'imposer en test.
