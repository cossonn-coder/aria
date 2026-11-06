# Sprint 52 — Tronçon 01 : module `chess_coach/level.py` + bilan Telegram

Lire d'abord `CLAUDE.md` et `docs/sprint52/00_etat.md` (décisions arrêtées).

## Objectif

1. Créer `chess_coach/level.py`, module **pur** (aucun import mémoire / LLM / moteur), deux fonctions
   sur des fiches `chess_game` (dicts de métadonnées, comme rendus par `bridge.load_chess_games()`) :
   - `performance(games) -> tuple[int, int] | None` : performance Elo et nombre de parties comptées.
     Parties comptées : `outcome` ∈ {`win`, `draw`, `loss`} **et** `elo_opponent` non nul.
     Score p = (V + 0,5·N) / n. Performance = moyenne des `elo_opponent` + 400·log10(p / (1 − p)),
     terme borné à [−800 ; +800] (p = 0 ou 1 → ±800). Arrondie à l'entier. Aucune partie comptée → None.
   - `accuracy_rank(accuracy, games) -> tuple[int, int]` : (rang, total). Total = fiches dont
     `accuracy` n'est pas None ; rang = 1 + nombre de ces fiches à `accuracy` **strictement** supérieure.
2. Bilan d'une partie (`execution/routers/chess_router.py`) :
   - `_moves_line` : la ligne 🎯 porte l'Elo officiel de chaque camp entre parenthèses quand il est connu
     (`summary["elo_nico"]`, `summary["elo_opponent"]`, déjà calculés par `summarize`) :
     `🎯 Précision : toi 84 % (1354) · adversaire 79 % (1332)`. Elo absent → pas de parenthèses pour ce camp.
   - **Dernière ligne du message** (après le bloc Progression s'il existe) :
     `🏅 Précision 84 % : ta 12e meilleure partie sur 140` (« ta meilleure partie » si rang 1 ;
     « 1re » n'apparaît donc jamais). Calcul sur les fiches déjà chargées dans `_execute_game`
     (`games = self.mempalace_bridge.load_chess_games()`, bloc Progression, l. ≈ 928) : la fiche courante
     y est (écrite avant). Pas de ligne si `summary["accuracy"]` est None ou si le chargement a échoué.

## Fichiers

- `chess_coach/level.py` (nouveau)
- `execution/routers/chess_router.py` (`_moves_line`, fin de `_execute_game`)
- Tests : `tests/chess_coach/test_level.py` (nouveau), `tests/execution/test_chess_router.py`
  (adapter les attentes sur la ligne 🎯, l. ≈ 73 et 248, et la nouvelle dernière ligne).

## Tests (cas nominal)

- `performance` : 2 V + 1 D contre 1500 → 1500 + 400·log10(2) ≈ 1620 ; toutes victoires → moyenne + 800 ;
  fiches sans Elo adverse ou à issue inconnue ignorées ; liste vide → None.
- `accuracy_rank` : ex æquo non comptés devant ; fiches sans `accuracy` exclues du total.
- Bilan : ligne 🎯 avec les deux Elo ; message terminé par la ligne 🏅.

## Hors scope (ne PAS faire)

- Aucun Maia, aucune estimation d'Elo par partie (abandonnés, audit §3 et §7.b).
- Ne pas réordonner les autres blocs du bilan. Ne pas toucher au prompt LLM ni à `_header_lines`.
- Pas de nouvelle clé dans la fiche.

## Critère de fin

`pytest tests/ -q` vert ; diff limité aux fichiers ci-dessus.
