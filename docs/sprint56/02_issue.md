# Sprint 56 — Tronçon 02 : `/issue` corrige le résultat d'une partie

À lire d'abord : `CLAUDE.md`, `docs/sprint56/00_etat.md`. Diagnostic : audit, constat 2.

## Objectif

Une partie collée avec `Result "*"` (abandon non noté) reste « issue inconnue » pour toujours :
aucun chemin n'écrit `result` / `outcome` d'une fiche existante. Nico doit pouvoir la corriger
depuis Telegram, sans LLM.

## Comportement attendu

Commande `/issue <adversaire> <victoire|nulle|défaite>` :

- Fiche visée : la **plus récente** (tri `_game_date_key`, `interfaces/meta_commands.py:332`)
  dont `opponent` est égal à `<adversaire>`, sans casse.
- Issue acceptée sans casse ni accent : `victoire`, `nulle`, `defaite` / `défaite`.
- Écriture : nouvelle fonction `memory/writer.py` `update_chess_game_result(doc_id, result, outcome)`,
  sur le modèle de `update_chess_game_accuracy` (l. 186) : `col.update(ids=[doc_id], metadatas=[{"result": …, "outcome": …}])`
  (ChromaDB fusionne : le reste de la fiche est intact, pas de ré-embedding).
  `outcome` ∈ `win` / `draw` / `loss` ; `result` déduit de `outcome` et de `nico_color`
  (`1-0`, `0-1`, `1/2-1/2`), la logique inverse de `_outcome` (`chess_coach/summary.py:52`).
- Réponse écrite par le code, une ligne :
  `✅ Issue corrigée : contre Tailor4321 (2026-11-11) → victoire.`
  Aucune fiche : `Aucune partie contre <adversaire>.` Arguments invalides : rappel de la syntaxe.
- Log : `meta_command name=issue` puis `meta_issue doc_id=… outcome=…`.

Câblage : entrée `COMMANDS["issue"]` dans `interfaces/meta_commands.py` (description courte), méthode
`_cmd_issue` dans `interfaces/telegram_interface.py` (enregistrement automatique, l. 167). Même
patron que `/oublie` (l. 467) : le handler lit via `self.bridge.load_chess_games` et écrit via
`memory.writer`, fonctions de texte et d'analyse des arguments dans `meta_commands.py` (testables).

## Fichiers à toucher

- `memory/writer.py`, `interfaces/meta_commands.py`, `interfaces/telegram_interface.py`.
- Tests : `tests/memory/test_writer.py`, tests de `meta_commands`.

## Tests (cas nominal)

- `update_chess_game_result` appelle `update` avec les deux champs seulement.
- Choix de la fiche + calcul du `result` : Nico noir, `victoire` → `0-1`, `win`.
- Texte de réponse et cas « aucune partie ».
- `pytest tests/ -q` vert.

## Hors-scope (ne PAS faire)

- Pas de compréhension en langage naturel (« gain sur abandon ») : la consigne d'honnêteté du
  tronçon 04 fera dire au LLM d'utiliser `/issue`.
- Le texte indexé de la fiche (`summary_text`, « résultat * (issue inconnue) ») n'est pas réécrit :
  dette cosmétique à noter.
- Pas de champ `termination` ajouté.

## Critère de fin

Tests verts.
