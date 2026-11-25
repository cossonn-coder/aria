# Sprint 66 — audit miniatures jouables dans l'échiquier (62-8)

Audit du 2026-11-25 sur `main` @ `ea193c5`. Lecture du code réel.

Dette 62-8 (Nico) : « Jouer la variante depuis la position, explications comme dans les miniatures ».

## 1. Ce qu'est une miniature Telegram aujourd'hui

`execution/routers/chess_router.py` `_execute_game` (`:1329-1456`), après
`chess_coach.analysis.analyze` (moteur + Maia, **34 à 93 s par partie** [6 runs du
`logs/router.log`, 37 à 103 demi-coups]) :

| Miniature | Source | Légende écrite par le code |
|---|---|---|
| Position N (critique, sortes a/b/c/d/e) | `analysis.critical` | `_caption` (`:878`) + `_variant_line` (`:537`) + réflexion longue éventuelle |
| Position N (réflexion longue hors critiques) | `long_thinks` | `_think_caption` (`:905`) |
| Conversion | `repeated_ideas(period)`, calculé **après** l'écriture de la fiche (`:1411`) | `_conversion_caption` (`:914`) |
| Courbe | `render_curve` | fixe |

`_variant_line` produit, selon la sorte :
- a/b avec `best_line_san` : « Meilleur coup : … → fin », « Ton coup : … → fin », puis
  « Pointe : … » et une ligne « Si … » par défense réfutée (`_point_text`, `:502`) ;
- c/e : « Variante : » `critical.line_san` ;
- d : « Variante : » coup explosif + `trap_line_san`, ligne « Piège : » (réponse piégeante),
  « Variante du meilleur coup : » `p.pv_san`.

Puis `_split_entries` (`:941`) colle sous chaque légende l'entrée « Position N — … » du LLM
(le « Pourquoi », 1 à 3 phrases). **Le texte LLM n'existe qu'après l'appel LLM**, lui-même
après l'écriture de la fiche (`write_chess_game`, `:1381`), parce que la progression (lue
dans les fiches, courante incluse) alimente le prompt.

## 2. Ce que la fiche stocke

`summary.plies_json` (`summary.py:279`) : par demi-coup `kind` (sorte critique ou `None`),
`best_san`, `uci`, `win_*`… **Aucune légende, aucune ligne de variante** (`best_line_san`,
`played_line_san`, `point`, `defenses`, `explosive`, `line_san` absents). Les 499 fiches
existantes [lecture prod 2026-11-20, audit sprint 65] ne permettent donc pas de reconstruire
une miniature sans refaire l'analyse complète.

## 3. L'échiquier aujourd'hui

`interfaces/board_interface.py` + `interfaces/board/index.html` :
- `/stored` (sprint 65) : fiche → PGN, courbe, meilleurs coups, historique ; aucun moteur.
- `/game` : `analyze_game` seul (pas `analyze` : ni critiques, ni Maia, ni lignes).
- Page : variantes déjà gérées — `goTo(n, line)` (`:593`) place la partie au coup n puis
  joue `line` en variante (affichée entre parenthèses dans « Coups »), `ahead` = pile des
  coups devant (▶ les rejoue un à un), « Revenir à la partie ». `variation(fen, sans)`
  (`:336`) rend une suite SAN survolable (mini-échiquier) mais **non jouable** sur l'échiquier.
- Onglets téléphone (`#tabs`, `:112`) : Coups, Courbe, explosifs, pièges, stratégie.

## 4. Règles d'architecture

- Écriture : un champ de plus dans `extra` de `write_chess_game` (même voie que
  `plies_json`, chaîne JSON car métadonnée Chroma scalaire) : règle 1 respectée tant qu'il
  n'y a **qu'une** écriture par partie. Ajouter le texte LLM imposerait une 2e écriture
  (upsert après LLM) ou de déplacer l'écriture après le LLM (casse la progression du prompt).
- Lecture : `/stored` lit déjà la fiche via `load_games` injecté (règle 2).
- **Palace prod touché en écriture** (nouveau champ sur les fiches futures) : additif, aucune
  fiche existante modifiée.
- Aucun router appelé par l'échiquier, aucun LLM, kernel non touché.

## 5. Options

1. **Stocker** à l'analyse Telegram les miniatures (légende + lignes jouables structurées :
   libellé, demi-coup de départ, coups SAN) dans la fiche ; `/stored` les renvoie.
   Coût nul à l'ouverture. Parties anciennes : rien (rattrapage = réanalyse ~1 min/partie).
2. **Recalculer** dans l'échiquier (`analyze` complet) à l'ouverture : 34-93 s d'attente,
   moteur + Maia partagés avec le worker live, texte LLM absent quand même.

## 6. Run live

Partie neuve envoyée à ARIA → `/parties` → lien → échiquier : onglet miniatures avec une
entrée par miniature Telegram, même légende ; un tap sur une ligne joue la variante sur
l'échiquier, ▶ avance coup par coup ; `journalctl` : `board_stored … minis=K`, aucun
`board_game`.
