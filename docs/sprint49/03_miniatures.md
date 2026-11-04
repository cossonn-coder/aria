# Tronçon 03 — miniatures : variante du meilleur coup, chute d'évaluation, écart au 2e

## Objectif

L'image montre la variante du meilleur coup, pas son seul premier coup. La légende d'une erreur montre la chute d'évaluation, celle d'un seul coup l'écart avec le 2e meilleur coup.

## Fichiers

- `chess_coach/render.py` : `render_position`.
- `execution/routers/chess_router.py` : `_execute_game` (appel du rendu), `_caption`, `_variant_line`.
- `tests/execution/test_chess_router.py`, `tests/chess_coach/test_chess_coach.py` (`test_render_position_*`).

## Comportement attendu

**Image** : `render_position` reçoit la variante (paramètre optionnel, ex. `best_line_uci`), au plus 3 demi-coups, alimentée par `p.pv_uci[:3]` (`PlyAnalysis`). Flèches vertes numérotées 1, 2, 3 : pastille verte à bord blanc, chiffre blanc, près de la case d'arrivée, dessinée au-dessus des pièces. Sans variante, rendu inchangé.
- Coup joué = meilleur coup : la flèche bleue porte le n° 1, puis les vertes 2 et 3.
- Les flèches orange et bleue restent. Essai déjà jugé lisible sur 1 position, sans orange.
- Toute sorte de miniature (`a`, `b`, `c`, `d`, `e`) : l'image part toujours du meilleur coup.

**Légende `d`** : `_variant_line` garde la variante du coup explosif et une ligne s'y ajoute pour le meilleur coup (`p.pv_san`), au même format et clairement libellée (ex. « Variante du meilleur coup : … »). `a`, `b`, `c`, `e` donnent déjà la variante du meilleur coup : ne pas la dupliquer.

**Légende `a`, `b`** : ajouter la chute, du point de vue de Nico, depuis `p.win_before`, `p.win_after`, `p.loss` : par exemple « évaluation : 62 % → 41 % (−21 pts) ».

**Légende `c`** : ajouter l'écart, depuis `p.win_before` et `p.second_gap` (non `None` pour un `c`, `select_critical` l'exige) : par exemple « 2e meilleur coup : 72 % → 48 % (−24 pts) ». Son nom n'est pas stocké, ne pas ajouter de champ.

`e` et `d` n'ont pas d'évaluation ajoutée. La partie factuelle grandit, le commentaire LLM reste coupé à `_CAPTION_MAX` par `_split_entries` : ne rien changer à ce mécanisme.

## Tests (cas nominal)

- Rendu : PNG produit avec `best_line_uci` de 3 coups, et avec coup joué = meilleur coup.
- Le router passe les 3 premiers `pv_uci`.
- Légende `a` : contient la chute. Légende `c` : contient l'écart. `d` : contient les deux variantes.

## Hors périmètre

Longueur des variantes (#109) ; prompt LLM ; message enrichi ; échiquier web ; nom du 2e coup.

## Critère de fin

`pytest tests/ -q` vert. Lisibilité à juger au run live.
