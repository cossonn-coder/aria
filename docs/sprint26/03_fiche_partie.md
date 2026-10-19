# Sprint 26 — Tronçon 03 : fiche structurée par partie (palace prod)

Lire d'abord : `CLAUDE.md`, `docs/sprint26/00_etat.md` (Q7/Q8), puis
`chess_coach/analysis.py` et `execution/routers/chess_router.py` (tronçons 01-02),
et `memory/writer.py`.

⚠ **Palace prod touché** : nouveau type de document dans `aria_episodic`.
Exception au calibrage faible : test d'écriture avec collection simulée, et
vérification que wing/room/type sont structurels (invariant W4).

## Objectif

Chaque PGN analysé produit **une** fiche `chess_game` en mémoire épisodique,
dédoublonnée (renvoyer la même partie la remplace), contenant les faits bruts
par demi-coup + une synthèse. Elle prépare le bilan joueur du sprint 27 (#81),
qui n'est PAS fait ici.

## Fichiers

### `chess_coach/summary.py` (nouveau, pur — pas d'import mémoire/LLM)

`summarize(analysis: GameAnalysis) -> dict` — **valeurs scalaires uniquement**
(str, int, float, bool, None ; contrainte ChromaDB). Clés :

| Clé | Contenu |
|---|---|
| `date` | en-tête `Date` (ou `UTCDate`), "" sinon |
| `nico_color`, `color_source` | depuis l'analyse |
| `opponent` | nom adverse (en-tête) |
| `elo_nico`, `elo_opponent` | int ou None |
| `result` | en-tête `Result` ; `outcome` : "win" / "loss" / "draw" / "unknown" (vu de Nico) |
| `termination` | en-tête `Termination`, "" sinon |
| `time_control` | en-tête `TimeControl`, "" sinon |
| `eco`, `opening` | en-têtes `ECO`, `Opening` ; à défaut dernier segment de `ECOUrl` ; "" sinon |
| `opening_line` | 12 premiers demi-coups en SAN (anglais), séparés par des espaces |
| `n_plies` | nombre de demi-coups |
| `nico_best`, `nico_correct`, `nico_inaccuracy`, `nico_mistake`, `nico_blunder` | compteurs |
| `first_error_nico`, `first_error_opponent` | n° de coup du 1er `mistake`/`blunder`, None si aucun |
| `accuracy_opening`, `accuracy_middlegame`, `accuracy_endgame` | précision Nico par phase, moyenne de `clamp(103.1668 * exp(-0.04354 * loss) - 3.1669, 0, 100)`, None si phase absente |
| `max_win_nico`, `min_win_nico` | extrêmes du % de gain de Nico |
| `unconverted` | `max_win_nico >= 80` et outcome != "win" |
| `saved` | `min_win_nico <= 20` et outcome != "loss" |
| `opponent_errors`, `opponent_errors_punished` | coups adverses `loss >= 20` ; parmi eux, ceux où la réponse de Nico a `loss < 10` |
| `errors_low_clock` | coups de Nico `mistake`/`blunder` avec `clock < 60`, None si pas de pendule |
| `plies_json` | `json.dumps` de la liste des demi-coups : ply, move_number, color, san, uci, win_before, win_after, loss, best_san, quality, phase, tags, clock, kind critique ("a"/"b"/"c"/None) |

`summary_text(analysis, summary) -> str` : 2-3 phrases françaises indexables, ex. :
« Partie d'échecs du 2026.10.19 : Nico (noirs, 1307) contre King_walks_19 (1272),
ouverture A80 Hollandaise, résultat 0-1 (victoire). Précision ouverture 88 %,
milieu 71 %. 1 erreur, 0 gaffe ; 1re erreur au coup 17. »

### `memory/writer.py`
Nouvelle fonction, même style que les autres :
```python
def write_chess_game(text: str, game_hash: str, *, extra: dict | None = None) -> None:
```
- `doc_id = f"chess_game_{game_hash}"` → `upsert` (dédoublonnage).
- `meta = {**(extra or {}), "wing": "aria_episodic", "room": "chess",
  "type": "chess_game", "timestamp": _now_iso(), "source": "chess_router"}` —
  champs structurels APRÈS le spread (invariant W4), `_validate(meta)`.
- `game_hash` : calculé par le caller = `sha256` des coups UCI joués concaténés
  (pas des en-têtes : un même PGN recopié sans en-têtes reste la même partie), 16 car.

### `execution/routers/chess_router.py`
Après l'analyse (et avant la délégation LLM) : `summary = summarize(analysis)`,
`write_chess_game(summary_text(...), game_hash, extra=summary)` dans un
`try/except Exception: log.exception(...)` non bloquant (même convention que
les autres écritures non bloquantes des routers). Log :
`log.info("chess_game_write OK hash=%s plies=%d", …)`.

### `CLAUDE.md`
Règle inviolable 1 : ajouter `write_chess_game` à la liste des fonctions du writer.
Section « Couches mémoire » : `aria_episodic` « interactions, images et fiches de
parties d'échecs (`type=chess_game`, room `chess`) ».

## Tests à ajouter (cas nominal)

- `tests/chess_coach/test_summary.py` : `summarize` sur un `GameAnalysis` construit
  à la main (2-4 PlyAnalysis) → compteurs, `first_error_nico`, `outcome`, toutes
  les valeurs scalaires, `plies_json` rechargeable par `json.loads`.
- `tests/memory/test_writer.py` (suivre le patron `patch("memory.writer.get_collection")`) :
  `write_chess_game` → `upsert` avec id `chess_game_<hash>`, wing/room/type
  structurels même si `extra` contient `wing`/`type` ; deux appels même hash → même id.
- `tests/execution/test_chess_router.py` : `write_chess_game` appelé une fois
  avec un `extra` contenant `nico_color`.

## Hors scope (ne PAS faire)

- Aucune lecture des fiches, aucun bilan / progression / détection de déviation
  de répertoire (sprint 27, #81).
- Pas de nouvelle collection ni de nouveau wing.
- Pas de modification de `memory/mempalace_bridge.py`.

## Critère de fin

- `pytest tests/ -q` vert.
- Sandbox avec collection simulée : la fiche du PGN de la partie 2 (run live,
  message B) a `nico_color == "black"`, `outcome`, `opening_line` non vide,
  `len(plies_json)` < 20 000 car.
