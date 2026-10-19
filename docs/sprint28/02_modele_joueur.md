# Sprint 28 — tronçon 02 : modèle joueur (XP, niveaux, badges, ouvertures)

À lire avant : `CLAUDE.md`, `docs/sprint28/00_etat.md`, `docs/sprint28/01_difficulte_maia.md`
(champs `difficulty` / `second_gap` de `plies_json`).

## Objectif

Un module **pur** qui rejoue l'historique des fiches `chess_game` de la saison 1 et
produit le profil RPG de Nico, plus la **lecture des fiches** via le bridge. Aucune
écriture : le profil est recalculé à chaque analyse (décision Q1 a). Pas de rendu ici.

## 1. Lecture — `memory/mempalace_bridge.py`

Nouvelle méthode `load_chess_games(self) -> list[dict]`, sur le modèle de
`load_conversation_history` (même `get_by_metadata` injecté, même `RuntimeError` s'il
manque) : `where = {"$and": [{"wing": "aria_episodic"}, {"type": "chess_game"}]}`.
Retourne une liste de dicts `{**metadata, "id": <doc_id>}` triée par `timestamp`
croissant. Rien d'autre (règle 2 : seule voie de lecture).

## 2. Module — `chess_coach/player_model.py`

Aucun import mémoire / LLM / exécution (comme `summary.py`). Point d'entrée :
`build_profile(games: list[dict]) -> Profile` (dataclass). Le caller (tronçon 03)
appellera `build_profile` deux fois (sans la partie courante, puis avec) et comparera.

### Parties retenues
Fiches dont `plies_json` contient la clé `difficulty` (saison 1) **et** `n_plies ≥ 20`,
dans l'ordre reçu.

### Thèmes et classement (Elo façon puzzles)
Six classements : `global` + cinq thèmes. Valeur initiale de chaque classement =
`elo_nico` de la 1re partie retenue (1300 si absent).

**Épreuve** = coup de Nico (`color == nico_color`) avec `difficulty` non None,
`10 ≤ win_before ≤ 90`, et (`loss ≥ 10` ou `second_gap ≥ 10`).
Score S = 1 si `loss < 10`, sinon 0. Espérance E = 1 / (1 + 10^((difficulty − R)/400)).
ΔR = K · (S − E), K = 16 pour les 30 premières épreuves du classement, 8 ensuite.
Une épreuve met à jour `global` et chaque thème dont elle relève (souvent plusieurs) :

| Thème (libellé) | L'épreuve en relève si |
|---|---|
| Pièces en prise | le coup joué a l'étiquette `hanging`, ou `best_san` contient `x` |
| Punir les erreurs | le demi-coup adverse précédent a `loss ≥ 15` |
| Convertir l'avantage | `win_before ≥ 70` |
| Finale | `phase == "endgame"` |

**Ouverture** (pas de Maia avant le coup 10) : une épreuve **par partie**, S = 1 si aucun
coup de Nico avec `move_number ≤ 10` n'a `loss ≥ 20`, sinon 0 ; difficulté =
`elo_opponent` (sinon `elo_nico`) ; K comme ci-dessus.

**Résultat de partie** : met à jour `global` seulement, K = 32, S = 1 / 0,5 / 0 selon
`outcome` (win / draw / loss), difficulté = `elo_opponent`. Ignoré si `outcome == "unknown"`
ou Elo adverse absent. (Une défaite contre plus faible coûte donc plus cher.)

**Niveau** d'un classement = `int(R // 100)`.

### Profil (contenu minimal attendu)
- par classement : valeur R, niveau, nombre d'épreuves ;
- pour la **dernière partie** retenue : par classement, ΔR de la partie et l'épreuve qui a
  le plus pesé (|ΔR| max) avec son libellé de coup (`17.Qb3`, `17...Qb3`), sa difficulté
  et trouvé / raté ;
- badges débloqués (nom → libellé de la partie qui l'a débloqué) ;
- inventaire d'ouvertures ;
- nombre de parties retenues.

### Badges (débloqués une seule fois, à la 1re partie qui remplit la condition)

| Badge | Condition sur la partie (ou la série qui finit par elle) |
|---|---|
| Tueur de géant | `outcome == "win"` et `elo_opponent ≥ elo_nico + 100` |
| Main propre | `nico_blunder == 0` et `n_plies ≥ 40` |
| Justicier | `opponent_errors ≥ 2` et `opponent_errors_punished == opponent_errors` |
| Coup de maître | une épreuve trouvée avec `difficulty ≥ R_global avant l'épreuve + 400` |
| Phénix | `min_win_nico ≤ 20` et `outcome in ("win", "draw")` |
| Bourreau | 3 parties de suite avec `max_win_nico ≥ 80` et `outcome == "win"` |
| Série | 3 victoires de suite |
| Répertoire | 5e partie dans la même famille d'ouverture |

Ne pas utiliser `unconverted` / `saved` des fiches (faux sur les résultats `*`, dette).

### Inventaire d'ouvertures
Famille = champ `opening` (slug Chess.com, ex. `Scotch-Game-Goring-Double-Pawn-...`)
coupé après le premier mot parmi `Defense, Game, Opening, Gambit, Attack, System`
(inclus), sinon les deux premiers mots ; tirets → espaces (« Scotch Game »,
« Caro Kann Defense », « Van t Kruijs Opening »). `opening` vide → hors inventaire.
Clé (famille, `nico_color`) → victoires, nulles, défaites, win rate = victoires / parties.

## Tests (cas nominal) — `tests/chess_coach/test_player_model.py`

Fiches factices construites en dicts (pas de palace) :
- une épreuve trouvée à difficulté R+200 rapporte plus qu'une trouvée à R−300 ; une
  ratée à R−300 coûte plus qu'une ratée à R+200 ;
- fiche sans clé `difficulty` (ou `n_plies < 20`) ignorée ;
- défaite contre plus faible : ΔR global plus négatif que défaite contre plus fort ;
- badge Tueur de géant débloqué une seule fois sur deux victoires qualifiantes ;
- inventaire : famille « Scotch Game » (blancs) 1 V 1 D → 50 %.
- `tests/memory/` : `load_chess_games` filtre wing + type et trie par timestamp
  (get_by_metadata factice).

## Hors scope

- Pas de rendu, pas de branchement dans le router (tronçon 03).
- Pas d'écriture mémoire, pas d'`aria_semantic`, pas de REFLECTION.
- Pas de correction de `unconverted` dans `summary.py` (dette).

## Critère de fin

`pytest tests/ -q` vert.
