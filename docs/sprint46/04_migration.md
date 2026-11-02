# Sprint 46 — tronçon 04 : script de migration des fiches de parties

**Palace prod : exception au calibrage faible.** Le script est écrit et testé sur une **copie** par ce tronçon.
Seul Nico l'exécute sur la prod, au tronçon 05. Ne jamais lancer `--apply` sur `~/.mempalace/palace` ici.

## Objectif

Sur les 66 fiches `chess_game` : supprimer les 9 analysées du mauvais camp, ranger les 57 autres dans la room de
leur ouverture, sans toucher au reste.

## Fichiers

- `memory/writer.py` : deux nouvelles fonctions (règle 1, tout passe par le writer).
- Nouveau `scripts/migrate_chess_rooms.py`, modèle `scripts/migrate_wing_aria_to_episodic.py` si utile.
- Tests : `tests/memory/test_writer.py`, nouveau `tests/scripts/test_migrate_chess_rooms.py` (ou l'emplacement
  des tests de scripts s'il existe).

## Comportement

**Writer**
- `update_chess_game_opening(doc_id, room, opening, opening_group, eco)` : `col.update(ids=[doc_id], metadatas=[…])`
  avec ces seuls champs. Vérifié sur copie : la mise à jour fusionne, `timestamp`, `plies_json` et document intacts
  [1 fiche]. Aucun ré-embedding, `timestamp` inchangé (sinon #97 réordonne la chronologie).
- `delete_chess_games(doc_ids)` : `col.delete(ids=doc_ids)`.

**Script** : `scripts/migrate_chess_rooms.py [--palace CHEMIN] [--apply]`
- Défaut = essai à blanc, sans aucune écriture. `--palace` (défaut `config.mempalace_path`) remplace
  `config.mempalace_path` pour le writer.
- Lit les fiches via `MempalaceBridge(store=search, get_by_metadata=get_by_metadata).load_chess_games()`, construit
  comme dans `bot.py:31`. `load_chess_games` lit `config.mempalace_path` : à poser avant.
- **À supprimer** : `opponent` égal à un pseudo de `config.chess_usernames` ou à `Nico`, insensible à la casse.
  Attendu sur la prod au 2026-11-02, à afficher et à comparer :
  `chess_game_13b7dfa511210031`, `chess_game_77fe80051db8b240`, `chess_game_dce2b1804d94b7eb`,
  `chess_game_6f1e3bb987feeecb`, `chess_game_204a4207b294a118`, `chess_game_2f3a3b1f3a18e216`,
  `chess_game_991140ab8fbb3116`, `chess_game_f8eeb32ca876ec9f`, `chess_game_8ef649fb688185e3`.
- **À ranger** : les autres. `detect_opening` sur les `uci` de `plies_json`, puis `opening_group` et `opening_room`.
  `eco` : valeur de la fiche, sinon valeur détectée. Fiche non reconnue : signalée, laissée telle quelle.
- Essai à blanc : affiche les suppressions, le nombre de fiches par room, les non reconnues.
- `--apply` :
  1. refuse si `systemctl is-active aria` répond `active` et que le palace visé est celui de la config ;
  2. copie le palace vers `<palace>.pre-sprint46-<AAAAMMJJ-HHMMSS>` et affiche le chemin ;
  3. supprime, puis met à jour ;
  4. relit et vérifie : nombre de fiches = avant − supprimées, `timestamp` et `plies_json` inchangés, plus aucune
     fiche à pseudo adverse. Tout écart est affiché et sort en code ≠ 0.
- Idempotent : relancer ne change rien. Journal via `get_logger`, tableau final imprimé en sortie console, comme les
  scripts existants du dossier.

## Tests (cas nominal)

- Fonctions du writer sur `fake_col` (voir `test_writer.py`) : champs passés, `delete` appelé.
- Plan de migration sur des fiches factices : pseudo → suppression, Göring → `chess_goring-gambit`.

## Vérification obligatoire du tronçon (sur copie)

Copier `~/.mempalace/palace` vers le scratchpad, puis `--palace <copie>` à blanc et `--apply`. Rapporter : fiches
avant / après, rooms, non reconnues, seconde exécution sans changement, et que `load_chess_games` puis `build_profile`
tournent sur la copie migrée. La copie réelle peut compter plus de 66 fiches si Nico a joué depuis.

## Hors scope

Réanalyse (décision de Nico : suppression), document indexé (dette), fiches « Test » / « Ami » (#98), `.drift-*` (#142).

## Fin

`pytest tests/ -q` vert, vérification sur copie rapportée, prod intacte.
