# Sprint 55 — Audit : rang de précision (jour, ouverture) et légende 🟢

Date : 2026-11-09. Code lu à `fbfdcdf` (tag `sprint-54`).

## Demande de Nico (bilan Telegram du 2026-11-09, Caro-Kann contre The_Neyzak)

1. « Précision 92 % : ta 52e meilleure partie sur 206 » : il veut aussi le rang
   **parmi les parties du jour** et **parmi les parties de cette ouverture**.
2. « 🟢 coup du moteur (toi / adversaire) » : il croit que c'est le compte des coups forcés.
   Ce n'est jamais un compte, et le libellé « (toi / adversaire) » est toujours affiché.

## 1. Rang de précision : code actuel

`chess_coach/level.py:37` :

```python
def accuracy_rank(accuracy: float, games: list) -> tuple[int, int]:
    accuracies = [g["accuracy"] for g in games if g.get("accuracy") is not None]
    return 1 + sum(1 for a in accuracies if a > accuracy), len(accuracies)
```

Il y a 2 appelants :
- `execution/routers/chess_router.py:551` `_rank_line(accuracy, games)` → « 🏅 Précision X % : ta Ne
  meilleure partie sur T ». Appelé en dernière ligne du bilan (`chess_router.py:1103-1104`).
  `games` = `self.mempalace_bridge.load_chess_games()` (`chess_router.py:1046`, lecture via le
  bridge, partie courante incluse puisqu'elle est déjà écrite).
- `interfaces/board_interface.py:198` `game_history` (échiquier web, partie collée) : même
  libellé, sans 🏅.

Les champs nécessaires sont déjà dans les fiches `chess_game` :
- jour : `date` (en-tête PGN, « 2026.11.09 »), sinon `timestamp`. La règle existe déjà dans
  `interfaces/meta_commands.py:143` `_game_day` (utilisée par `/parties`, `_in_period`).
  Pour la partie courante : `summary["date"]` (`chess_coach/summary.py:186`).
- ouverture : `chess_coach/player_model.py:155` `game_opening_group(game)` (groupe, sinon famille
  du slug), avec `nico_color`. La ligne 📖 du bilan (`chess_router.py:670-677`) groupe déjà par
  (groupe, couleur), via `after.openings`.

Il n'y a aucun écart bloquant : tout est lu depuis les fiches déjà chargées, sans nouvelle
lecture mémoire ni écriture. Les règles inviolables ne sont pas touchées.

Limites connues :
- #175 : le jour vient de la date PGN, qui est peut-être en UTC. Une partie jouée après minuit
  peut tomber la veille. C'est la même règle que `/parties`, donc la cohérence est conservée.
- Le rang sur 1 partie (1re partie du jour, ou 1re partie dans l'ouverture) n'apporte rien.

## 2. Légende 🟢 : code actuel

`chess_router.py:124` : `_MARK_BEST = "🟢"`. D'après le commentaire du sprint 51 (l.122), c'est le
meilleur coup du moteur, de la même couleur que la flèche verte des miniatures.

`chess_router.py:530-543` `_marks_key` : les 5 qualités ont un compte « toi / adversaire »,
🟠 et 🩵 ont un compte, et 🟢 a un libellé fixe :
`parts.append(f"{_MARK_BEST} coup du moteur (toi / adversaire)")`.

🟢 sert dans les légendes des positions : « joué 🔴 4...Nf6, … (meilleur 🟢 4...Nc6) »
(tests `tests/execution/test_chess_router.py:161, 254, 881, 994`).

Diagnostic : 🟢 n'est **pas** un coup forcé. C'est le coup que le moteur proposait à la place du
coup joué. La notion de coup forcé existe (`chess_coach/analysis.py:596`), mais elle sert
seulement à borner les suites et n'a aucune pastille. Le suffixe « (toi / adversaire) » imite les
pastilles comptées alors qu'il n'y a aucun compte : c'est lui qui induit en erreur.

Un coup joué qui est le meilleur coup du moteur est compté en 🔵. Compter 🟢 ferait doublon,
ou compterait les positions montrées, ce qui n'a pas de sens pour Nico.

Tests touchés par un changement de libellé : `tests/execution/test_chess_router.py:90` et `:924`.
