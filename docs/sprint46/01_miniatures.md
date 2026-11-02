# Sprint 46 — tronçon 01 : miniatures (4 places, coup 4, flèche bleue, pseudos)

## Objectif

Le compte rendu d'une partie montre d'abord les coups manqués de Nico, jamais avant le coup 4,
avec le coup joué en flèche bleue. ARIA reconnaît les pseudos de Nico dans les en-têtes PGN.

## Fichiers

- `chess_coach/analysis.py` : `select_critical` (l. 406), `detect_color` (l. 151).
- `chess_coach/render.py` : `render_position`.
- `execution/routers/chess_router.py` : appel de `render_position` dans `_execute_game` ; en-tête du
  module (« ≤ 3 »).
- `config.py` : section « Coach d'échecs ».
- Tests : `tests/chess_coach/test_chess_coach.py`, `tests/execution/test_chess_router.py`.

## Comportement

**Sélection (`select_critical`)**
- Budget unique de 4 positions. Le bonus séparé de 3 explosifs disparaît.
- Une position avec `move_number < 4` n'est jamais retenue, quelle que soit sa sorte (explosifs compris).
- Ordre de remplissage : erreurs a/b (score décroissant), explosifs d (score décroissant), tournants e
  (score décroissant), coups uniques c (score décroissant). Une position déjà prise est sautée.
- Retour en ordre chronologique, comme aujourd'hui. Docstring mise à jour.

**Flèche bleue (`render_position`)**
- Nouveau paramètre mot-clé `played_uci: str | None = None`, couleur bleue semi-transparente, dessinée
  en dernier sous les pièces.
- Si `played_uci == best_uci`, la flèche verte n'est pas dessinée : seule la bleue reste.
- `_execute_game` passe `played_uci=critical.ply.uci`. Garder `out_path` en 4e position : les tests lisent `a[3]`.
- La flèche orange ne change pas.

**Pseudos**
- `config.py` : `chess_usernames: tuple = ("La_Bagouze", "TardoScoped", "staroflexeur")`.
- `detect_color` : l'en-tête White ou Black vaut `NICO_NAME` **ou** un de ces pseudos (insensible à la casse).
  `analysis.py` n'importe pas encore `config` ; l'import est permis (`config.py` n'importe pas `chess_coach`).
- `analyze` garde sa signature.
- L'échiquier live ne change pas (`NICO_NAME` y reste « Nico »).

## Tests (cas nominal)

- 5 erreurs + 1 explosif + 1 coup unique → 4 positions, toutes a/b, les plus grosses pertes.
- 1 erreur + 1 explosif + 1 tournant + 1 coup unique → les 4, dans l'ordre chronologique.
- Erreur au coup 3 écartée, au coup 4 retenue.
- `render_position` avec `played_uci` différent puis égal au meilleur coup : pixel bleu présent sur le trajet,
  pas de vert dans le second cas.
- `detect_color` : `La_Bagouze` en Black → `("black", "header")`.

**Tests existants à adapter :**
- `_ply` calcule `move_number` à partir du ply : les positions des premiers plies tombent avant le coup 4.
  Passer `move_number` explicite dans les tests de sélection.
- `test_select_critical_explosive_is_bonus` : réécrire selon le budget unique.
- `test_analyze_detects_blunder` : la gaffe est au coup 3 ; n'y garder que l'assertion de qualité.
- `test_detect_color` : `staroflexeur` devient reconnu → `("black", "header")`. Le cas « inconnu » prend un autre nom.

## Hors scope

Texte des légendes, consignes du LLM, ouvertures, `find_explosive` (il cherche encore sur les coups 1-3 :
dette notée), page de l'échiquier.

## Fin

`pytest tests/ -q` vert. À valider en live : tronçon 05.
