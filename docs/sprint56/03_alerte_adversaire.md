# Sprint 56 — Tronçon 03 : alerte précision adverse suspecte dans le bilan

À lire d'abord : `CLAUDE.md`, `docs/sprint56/00_etat.md`. Origine : audit, constat 6 (demande de
Nico du 2026-11-10, que le LLM avait promise sans pouvoir la faire).

## Objectif

Dans le bilan d'une partie analysée, une ligne écrite par le code signale une précision adverse
anormalement haute sur une partie assez longue pour ne pas être de la préparation.

## Comportement attendu

Dans `_moves_line` (`execution/routers/chess_router.py:581`), juste après la ligne `🎯 Précision`,
quand `summary["accuracy_opponent"]` n'est pas None, `summary["opponent_moves"] >= 20` et
`summary["accuracy_opponent"] >= 95` :

```
⚠️ Précision adverse 99 % sur 27 coups (1698 Elo) : à surveiller
```

- `(1698 Elo)` seulement si `summary["elo_opponent"]` est connu ; sinon la parenthèse disparaît.
- Constantes nommées pour les deux seuils (20 coups, 95 %), commentaire : décision de Nico du
  2026-11-11 (un seul seuil ; le nombre de coups affiché dit le poids de la précision).
- Aucune ligne sinon.

## Fichiers à toucher

- `execution/routers/chess_router.py`, `tests/execution/test_chess_router.py`.

## Tests (cas nominal)

- 27 coups adverses, 99 %, Elo 1698 → la ligne exacte ci-dessus.
- 15 coups à 99 % → pas de ligne ; 27 coups à 90 % → pas de ligne.
- `pytest tests/ -q` vert.

## Hors-scope (ne PAS faire)

- Pas de seuil dépendant de l'Elo, pas de pondération par la longueur (sprint 57).
- Pas de mention dans le texte LLM ni sur l'échiquier web.

## Critère de fin

Tests verts.
