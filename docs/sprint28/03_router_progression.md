# Sprint 28 — tronçon 03 : bloc « Progression » dans la réponse d'analyse

À lire avant : `CLAUDE.md`, `docs/sprint28/00_etat.md`, `docs/sprint28/02_modele_joueur.md`
(`build_profile`, `Profile`, `bridge.load_chess_games`).

## Objectif

Après chaque analyse de partie, Nico voit sous la réponse du LLM un bloc **écrit par le
router** (exact par construction, pas par le LLM) : XP gagnée / perdue, paliers franchis
avec leur raison, badges débloqués, ligne d'ouverture. Le LLM reçoit une ligne de
données d'historique pour sa ligne « Niveau : ».

## Fichiers à toucher

- `core/kernel.py` (~l. 102) : `ChessExecutionRouter(llm_execution_router=…,
  mempalace_bridge=mempalace_bridge)` — même injection que `WebExecutionRouter`.
- `execution/routers/chess_router.py` :
  - `__init__(self, llm_execution_router, mempalace_bridge)` ;
  - dans `execute()`, **après** `write_chess_game` (la fiche courante est alors en base) :
    `games = self.mempalace_bridge.load_chess_games()` ;
    `before = build_profile([g for g in games if g["id"] != f"chess_game_{game_hash}"])`,
    `after = build_profile(games)`. Bloc entier dans **un** `try/except Exception` avec
    `log.exception("chess_progression ERROR")` → pas de bloc, la réponse part quand même
    (même logique que l'écriture de fiche). Log `chess_progression OK games=<n> global=<R>`.
  - nouvelle fonction de module `_progression_block(before, after, summary) -> str`,
    ajoutée **après** le texte LLM : `{"text": _to_english(result["text"]) + "\n\n" + block, …}`.
  - `_build_enriched` : une ligne `Historique (données) : <n> parties saison 1, classement
    global <R> (niveau <N>), <ΔR> sur cette partie` après la ligne `Niveau (données)`, et
    la consigne « Niveau : » dit de s'appuyer aussi sur cette ligne. Rien d'autre ne
    change dans la consigne (le prompt AnalystAgent n'est pas concerné).

## Format du bloc (texte Telegram brut)

```
🎮 Progression — saison 1, partie 4
Global 1342 (+18) · niveau 13
⬆️ Punir les erreurs 1385 (+25) · niveau 13 atteint : 17.Qb3 trouvé (difficulté ≈1950)
Finale 1290 (−12) : 39.Bb2 raté (difficulté ≈1490)
🏆 Badge débloqué : Tueur de géant — victoire contre un adversaire à 1452 (+107)
📖 Scotch Game (blancs) : 1 V, 0 N, 1 D — 50 %
```

Règles :
- ligne Global toujours ; une ligne par thème dont le ΔR de la partie est non nul, avec
  l'épreuve qui a le plus pesé ; `⬆️ … niveau N atteint` / `⬇️ … retour au niveau N` quand
  le niveau change entre `before` et `after` ;
- une ligne 🏆 par badge présent dans `after` et absent de `before`, avec sa raison ;
- ligne 📖 pour la famille et la couleur de la partie courante (rien si ouverture inconnue) ;
- première partie de la saison (`before` vide) : `🎮 Progression — saison 1 lancée`, puis
  la ligne Global seule et les badges éventuels ;
- partie hors saison (fiche ignorée par `build_profile`, ex. < 20 demi-coups) : pas de bloc.
- ΔR et R arrondis à l'entier ; signe − typographique comme `_material_line`.

## Tests (cas nominal) — `tests/execution/test_chess_router.py`

- Adapter le test existant : le router reçoit un bridge factice
  (`load_chess_games` renvoyant une liste préparée) ; le texte renvoyé commence par le
  texte LLM puis contient `🎮 Progression`.
- `_progression_block` sur deux profils construits à la main : palier franchi → ligne
  `⬆️` ; badge nouveau → ligne `🏆`.
- `load_chess_games` qui lève → réponse sans bloc, pas d'exception.

## Hors scope

- Pas de commande « bilan » sans PGN (dette #95).
- Pas de modification de `build_profile` (sauf bug bloquant constaté : le signaler).
- Pas de retouche des autres consignes du router ni de #89-#93.

## Critère de fin

`pytest tests/ -q` vert ; rendu à valider au run live (tronçon 04).
