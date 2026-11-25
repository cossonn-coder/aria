# Sprint 66 — tronçon 01 : miniatures enregistrées dans la fiche, servies par `/stored`

Lire d'abord : `CLAUDE.md`, `docs/sprint66/00_etat.md`, `docs/sprint66/audit_miniatures_echiquier.md`.

## Objectif

Chaque partie analysée sur Telegram garde dans sa fiche `chess_game` ses miniatures (même
liste, même ordre et même légende finale que les images Telegram, « Pourquoi » du LLM compris),
avec de quoi les rejouer dans l'échiquier. `/stored` les renvoie à la page.

## Format : métadonnée `minis_json` (chaîne JSON, liste)

Une entrée par image Telegram **sauf la courbe**, dans l'ordre des images :

```json
{"ply": 23, "kind": "a", "best": "Nf5", "also": [],
 "caption": "<légende finale de l'image Telegram>",
 "lines": [{"label": "Meilleur coup", "sans": ["Nf5", "exf5", "Qxf5"]}, …]}
```

- `ply` : `p.ply` (indice 0-based du demi-coup dans la partie = indice de la position avant le
  coup dans les FEN de l'échiquier).
- `kind` : sorte critique `"a".."e"`, `"think"` (réflexion longue hors critiques),
  `"conversion"`.
- `best` : `p.best_san`. `also` : autres coups qui réussissent l'exercice — sorte d :
  `[critical.explosive.san]` ; sinon `[]`.
- `caption` : légende **finale** de l'image (après `_split_entries`, donc factuel + variante +
  entrée LLM quand le découpage a réussi ; factuel seul sinon).
- `lines` : suites jouables, **toutes en SAN depuis la position de la miniature** (coup de Nico
  en tête) ; une suite vide est omise.

| Miniature | `lines` (libellé → coups) |
|---|---|
| a/b avec `best_line_san` | « Meilleur coup » → `best_line_san` ; « Ton coup » → `played_line_san` ; si `critical.point` et `critical.defenses` : une ligne par défense, libellé `f"Si {defense['san']}"`, coups `best_line_san[:point["prep"] + 1] + defense["line_san"]` (voir `_point_text`, `chess_router.py:502` : la défense suit le coup préparatoire) |
| c / e | « Variante » → `critical.line_san` |
| d | « Coup explosif » → `[explosive.san] + explosive.trap_line_san` ; si `_trap_replies(critical)` : « Piège » → `[explosive.san] + trapping[0]["line_san"]` ; « Meilleur coup » → `p.pv_san` |
| a/b sans `best_line_san` | « Meilleur coup » → `p.pv_san` |
| réflexion longue | « Meilleur coup » → `p.pv_san` |
| conversion | « Meilleur coup » → `ideas[0].first.pv_san` |

## Fichiers

- `memory/writer.py` : `update_chess_game_minis(doc_id: str, minis_json: str)`, sur le modèle de
  `update_chess_game_accuracy` (`col.update`, ChromaDB fusionne les métadonnées : le reste de la
  fiche intact, pas de ré-embedding). Règle 1 : seule voie d'écriture.
- `execution/routers/chess_router.py`, `_execute_game` (`:1329`) :
  - construire la liste des miniatures **en parallèle des images** (même indice) là où elles
    sont créées : boucle des critiques, réflexions longues, conversion ;
  - après l'ajout de la miniature de conversion et avant la courbe, recopier
    `images[i]["caption"]` dans l'entrée i ;
  - puis, seulement si l'écriture de la fiche a réussi, `update_chess_game_minis(
    f"chess_game_{game_hash}", json.dumps(minis, ensure_ascii=False))` dans un `try/except`
    `log.exception("chess_minis_write ERROR hash=%s")`, comme l'écriture de la fiche
    (non bloquant) ; succès : `log.info("chess_minis_write OK hash=%s minis=%d")`.
  - Ne pas déplacer `write_chess_game` (la progression du prompt lit la fiche en base).
- `interfaces/board_interface.py`, `stored_game` (`:220`) : clé `minis` =
  `json.loads(fiche.get("minis_json") or "[]")` ; `_stored` logue `minis=%d` en plus.

## Tests (cas nominal)

- `tests/memory/test_writer.py` : `update_chess_game_minis` passe seulement `minis_json`
  (modèle `test_update_chess_game_opening_passes_only_these_fields`).
- `tests/execution/test_chess_router.py` : sur un test existant à image critique (modèle
  `test_execute_returns_text_and_images_and_delegates_reasoning`), `update_chess_game_minis`
  mocké reçoit l'id de la fiche et un JSON dont la 1re entrée a le `ply`, le `best` et la
  `caption` de la 1re image.
- `tests/interfaces/test_board_interface.py` : `/stored` renvoie `minis` (fiche avec
  `minis_json`) et `[]` sans (modèle `test_stored_serves_fiche_without_analysis`).

## Hors scope

- Pas de rattrapage des fiches existantes. Pas de changement de la page (tronçon 02).
- Pas de modification du texte des légendes ni du prompt LLM.
- `/game` (PGN collé) : pas de miniatures.

## Critère de fin

`pytest tests/ -q` vert ; les 3 tests ci-dessus présents.
