# Sprint 27 — Tronçon 02 : affichage de l'occasion explosive (router + rendu)

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md`, `docs/sprint27/01_moteur_explosif.md`
(structure `CriticalPosition.explosive` / `ExplosiveMove` livrée au tronçon 01 — vérifier
les noms réels au code avant d'écrire).

## Objectif

Montrer la sorte `d` à Nico : diagramme avec 2 flèches, légende, faits moteur dans le
message enrichi, consigne LLM honnête sur le « pari pratique ».

## Fichiers

- `chess_coach/render.py` : `render_position(fen, orientation, best_uci, out_path,
  alt_uci=None)`. Si `alt_uci` : 2e flèche **orange** (ex. `(230, 120, 20, 190)`), même
  `_draw_arrow` (ajouter un paramètre de couleur), dessinée sur le même calque que la verte.
- `execution/routers/chess_router.py` :
  - `_KIND_FR["d"] = "occasion explosive"`.
  - Appel de `render_position` : passer `alt_uci=critical.explosive.uci` si sorte d.
  - `_caption` sorte d : `Position i — coup N (<couleur>) : joué X, explosif Y!? (meilleur Z)`
    (notation française via `_move_label`).
  - `_build_enriched`, bloc d'une position d, en plus des lignes existantes :
    `  explosif Y!? : coût P pts de % de gain (W % → W2 %), ligne : <_format_line(pv)>`
    puis `  sacrifice : N pion(s) ; forçant : échec/prise/menace ; piège : si l'adversaire
    joue R, il perd T pts ; volatilité V pts` (omettre les éléments nuls).
  - Consigne : ajouter une phrase pour les positions « occasion explosive » : explique
    l'idée du coup explosif (initiative, attaque, piège), son coût objectif, et dans quel
    contexte pratique le tenter ; ne le présente jamais comme le meilleur coup.
    (Message enrichi uniquement : **ne pas toucher le prompt AnalystAgent**.)
- `tests/execution/test_chess_router.py` : le monkeypatch existant
  `lambda fen, o, b, out: out` casse avec `alt_uci` → l'adapter (`lambda *a, **k: a[3]`).

## Tests à ajouter

- Router : une critique `d` construite à la main (sans Stockfish) → légende
  `… explosif …!? (meilleur …)`, `alt_uci` transmis au rendu, message enrichi contenant
  « occasion explosive », le coût et la ligne du piège.
- Rendu : `render_position(..., alt_uci=...)` produit un PNG de taille `SIZE`.

## Hors scope (ne PAS faire)

- Modifier l'algorithme de recherche (tronçon 01) ou ses seuils.
- `summary.py`, `write_chess_game`, rangement wing/room.
- Prompt AnalystAgent, `soul.md`.

## Critère de fin

`pytest tests/ -q` vert ; sandbox ou script : rendu du PGN Morra (`01_moteur_explosif.md`
test 1) → PNG avec flèches verte (e5) et orange (Cd5), message enrichi lisible
[vérifié VM] ; §REPRISE de `00_etat.md` mis à jour.
