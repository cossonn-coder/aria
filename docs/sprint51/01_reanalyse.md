# Sprint 51, tronçon 01 — réanalyse quand le PGN apporte les horloges

## Objectif
Nico recolle une partie déjà envoyée, cette fois avec les horloges chess.com (`[%clk …]`).
Aujourd'hui ARIA répond « déjà envoyée » (doublon par hash des coups). Si la fiche existante
n'a **aucune** horloge et que le PGN collé en a, la partie est réanalysée et sa fiche
réécrite en **gardant sa date d'origine** (`timestamp`), pour ne pas la déplacer dans la
chronologie de la progression (#97).

Contexte et chiffres : `docs/sprint51/audit_conversion.md`.

## À faire

### 1. `memory/writer.py::write_chess_game`
Paramètre mot-clé facultatif `timestamp: str | None = None`. Dans `meta`, la clé structurelle
devient `"timestamp": timestamp or _now_iso()`, **toujours posée après le spread de `extra`**
(invariant W4, règle inviolable 1 : `extra` ne peut pas la surcharger). Docstring à jour.

### 2. `execution/routers/chess_router.py`
- Fonction pure : « la fiche n'a pas d'horloge » = toutes les entrées de
  `json.loads(fiche["plies_json"])` ont `clock` à `None` (clé absente = `None`).
- Fonction pure : « le PGN a des horloges » = au moins un nœud de la ligne principale avec
  `node.clock()` non `None` (réutiliser `parse_pgn`).
- `execute` (partie unique) et `_execute_many` (plusieurs parties) : quand la fiche connue
  existe, si fiche sans horloge **et** PGN avec horloges → ne pas répondre « déjà envoyée »,
  analyser, et transmettre le `timestamp` de la fiche connue jusqu'à `write_chess_game`
  (paramètre facultatif ajouté à `_execute_game`, `None` par défaut). Sinon comportement
  actuel inchangé.
- Log : `chess_router reanalyze hash=%s reason=clock`.

## Tests (cas nominal)
- Writer : `timestamp` fourni → conservé ; `extra={"timestamp": "x"}` sans paramètre → ignoré
  au profit de `_now_iso()` (anti-W4). Fichier : `tests/memory/test_writer.py`.
- Router (`tests/execution/test_chess_router.py`, suivre les doubles existants) : fiche connue
  sans horloge + PGN avec `%clk` → analyse lancée, écriture avec le timestamp de la fiche ;
  même fiche + PGN sans `%clk` → « déjà envoyée ».
- `pytest tests/ -q` vert.

## Hors scope
- Mot-clé « réanalyse » pour forcer une réanalyse quelconque (reste de #182).
- Récupération des horloges via l'API chess.com (#83).
- Toute analyse du temps : tronçon 03.

## Critère de fin
Tests verts ; aucun autre caller de `write_chess_game` modifié.
