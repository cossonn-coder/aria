# Sprint 55 — Tronçon 01 : rang de précision du jour et de l'ouverture, légende 🟢

À lire d'abord : `CLAUDE.md`, `docs/sprint55/00_etat.md`. Diagnostic complet dans
`docs/sprint55/audit_rang_precision.md`.

## Objectif

Dans le bilan Telegram d'une partie analysée (`execution/routers/chess_router.py`) :

1. La dernière ligne 🏅 donne trois rangs de précision : sur toutes les fiches, sur les fiches
   du même jour et sur les fiches de la même ouverture (groupe + couleur de Nico).
2. Dans la clé des pastilles, 🟢 n'est plus présentée comme un compte.

## Comportement attendu

### Ligne 🏅 (`_rank_line`, `chess_router.py:551`, appel à la l.1103-1104)

Format exact, sur une seule ligne :

```
🏅 Précision 92 % : 52e sur 206 · 2e sur 5 aujourd'hui · 1re sur 4 en Caro-Kann Defense (blancs)
```

- Le rang 1 s'écrit `1re` dans tous les segments, et le rang N ≥ 2 s'écrit `Ne`. L'ancien texte
  « ta meilleure partie » / « ta Ne meilleure partie » disparaît de cette ligne.
- Chaque rang est calculé par `accuracy_rank(summary["accuracy"], sous_ensemble)`
  (`chess_coach/level.py:37`, inchangé) sur la liste `games` déjà chargée
  (`self.mempalace_bridge.load_chess_games()`, l.1046, partie courante incluse). Il n'y a
  **aucune** lecture mémoire en plus.
- Segment « aujourd'hui » : il compte les fiches dont le jour est égal au jour de la partie
  courante. Jour d'une fiche = `(g.get("date") or g.get("timestamp") or "")[:10].replace(".", "-")`,
  la même règle que `_game_day` (`interfaces/meta_commands.py:143`). **Ne pas importer** depuis
  `interfaces/` : le couplage routeur → module Telegram est la dette #204. On recopie cette
  ligne dans `chess_router.py`, avec un commentaire qui renvoie à `_game_day`. Jour de la partie
  courante : on applique la même règle à `summary` (champ `date`, `chess_coach/summary.py:186`).
  S'il est vide, on prend la date du jour (la fiche courante vient d'être écrite avec un
  timestamp d'aujourd'hui). Le libellé est « aujourd'hui » même si le jour PGN n'est pas
  aujourd'hui : c'est le jour de la partie, et cela reste accepté.
- Segment ouverture : il compte les fiches avec `g.get("opening")`, le même `nico_color` que
  `summary["nico_color"]` et `game_opening_group(g) == game_opening_group(summary)`
  (`chess_coach/player_model.py:155`, déjà importé et utilisé l.671). Libellé :
  `en {groupe} ({_COLOR_FR[couleur]})`, comme la ligne 📖 (l.675). Il n'y a pas de segment si
  `summary["opening"]` est vide.
- Un segment jour ou ouverture dont le total vaut 1 est **omis**. Le segment global est
  toujours présent.
- La garde d'appel ne change pas : `summary["accuracy"] is not None and games is not None`.

### Légende 🟢 (`_marks_key`, `chess_router.py:542`)

`f"{_MARK_BEST} coup du moteur (toi / adversaire)"` devient `f"{_MARK_BEST} meilleur coup du moteur"`.

## Fichiers à toucher

- `execution/routers/chess_router.py` : `_rank_line` (signature libre, `summary` en plus), son
  appel l.1104, `_marks_key` l.542.
- `tests/execution/test_chess_router.py` : libellés attendus l.90, l.93 et l.924, et un test du
  nouveau format.

## Tests (cas nominal)

- Un test unitaire de `_rank_line` avec quelques fiches : jours différents, ouvertures et
  couleurs différentes. Il vérifie la ligne exacte avec les 3 segments, puis le cas où le
  segment jour (ou ouverture) porte sur 1 partie et est omis.
- Mise à jour des assertions existantes (légende 🟢, ligne 🏅 de
  `test_execute_returns_text_and_images_and_delegates_reasoning`).
- `pytest tests/ -q` est vert.

## Hors-scope (ne PAS faire)

- `interfaces/board_interface.py` (`game_history`, ligne de rang de l'échiquier web) : on n'y
  touche pas.
- `accuracy_rank` : pas de modification.
- Ne pas déplacer `_game_day` et ne pas modifier `interfaces/meta_commands.py`.
- Pas de compte pour 🟢, pas de notion de coup forcé.
- Pas de correction UTC du jour (#175).

## Critère de fin

Le bilan produit la ligne 🏅 au format ci-dessus et la légende `🟢 meilleur coup du moteur`, et
`pytest tests/ -q` est vert. Commit local `feat(sprint55) tronçon 01: …`.
