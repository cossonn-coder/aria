# Sprint 39 — tronçon 07 : « moi » au lieu d'un pseudo d'échecs

Décision de Nico (2026-10-29) : plus de notion de pseudo (staroflexeur, TardoScoped…).
Nico choisit sa couleur sur l'échiquier (« Je joue : blancs / noirs ») ; le PGN exporté
ou envoyé porte **`Nico`** du côté choisi et le nom de l'adversaire de l'autre. ARIA
reconnaît `Nico` dans les en-têtes. Les fiches `chess_game` déjà écrites ne sont pas
touchées.

## Fichiers (vérifiés au code le 2026-10-29)

- `config.py` : champ `chess_username` (l. 83) et sa surcharge `CHESS_USERNAME`
  (l. ~106, commit `91271c5`) → supprimer les deux.
- `chess_coach/analysis.py` : `detect_color(headers, message, username)` (l. 123) et
  `analyze(text, message, username, engine_path, maia_models_dir)` (l. 431) → retirer le
  paramètre `username` ; `detect_color` compare White / Black (insensible à la casse) à
  une constante de module `NICO_NAME = "Nico"`. Ordre inchangé : en-tête, puis message
  (« je joue les noirs »), puis blancs par défaut.
- `execution/routers/chess_router.py` l. 564 : appel `analyze(message, message,
  config.chess_username, …)` → sans le pseudo.
- `interfaces/board_interface.py` l. 190 : remplacement `__CHESS_USERNAME__` → à retirer
  (page servie telle quelle).
- `interfaces/board/index.html` : `CHESS_USERNAME = "__CHESS_USERNAME__"` (l. ~115) →
  constante `"Nico"` (renommer en `NICO_NAME` si plus clair) ; le handler `#playing`
  (l. ~690) l'écrit dans le champ du camp choisi et l'ôte de l'autre (logique inchangée).
- `.env` (hors git) : supprimer la ligne `CHESS_USERNAME=TardoScoped`.

## Tests

- `tests/chess_coach/test_chess_coach.py` : `test_detect_color` et l'appel `analyze(…,
  "staroflexeur", …)` (l. 33) adaptés à la nouvelle signature ; cas nominal : en-tête
  `[Black "Nico"]` → `("black", "header")` ; `[Black "staroflexeur"]` sans message →
  `("white", "default")`.
- `tests/interfaces/test_board_interface.py` l. 78 : plus d'assertion sur le pseudo
  injecté ; vérifier que `__CHESS_USERNAME__` n'est plus dans la page.
- Les fixtures qui contiennent `staroflexeur` comme simple nom d'en-tête (classifier,
  router, summary) restent telles quelles sauf si un test en dépend pour la couleur.

## Hors scope

- Réécrire les fiches `chess_game` existantes ou leurs en-têtes.
- Toucher au rendu Telegram de l'analyse (lignes « Blancs : X »).
- La liste des coups et la zone PGN (tronçon 08).

## Critère de fin

`grep -rn "chess_username\|CHESS_USERNAME" --include=*.py --include=*.html . | grep -v venv`
vide ; `./venv/bin/pytest tests/ -q` vert.
