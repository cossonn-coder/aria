# Sprint 46 — tronçon 03 : ouvertures et progression

## Objectif

ARIA détecte l'ouverture à partir des coups, range chaque partie dans la room de son ouverture, donne des
statistiques de victoire par ouverture et affiche un score Milieu de jeu.

Ni Stockfish ni Maia ne nomment une ouverture : d'où une table. Prototype : 66 fiches reconnues sur 66
[copie du palace, 2026-11-02]. Détail : `audit_miniatures_erreurs.md`, section « Complément ».

## Fichiers

- Nouveaux : `chess_coach/data/openings.tsv`, `chess_coach/openings.py`, `tests/chess_coach/test_openings.py`.
- `chess_coach/summary.py`, `chess_coach/player_model.py`.
- `memory/writer.py` : `write_chess_game`.
- `execution/routers/chess_router.py` : `_execute_game`, `_anchor`, `_progression_block`, `_build_enriched`.
- `interfaces/meta_commands.py`, `interfaces/telegram_interface.py` : commande `/ouvertures`.
- Tests existants : `test_summary.py`, `test_player_model.py`, `test_chess_router.py`, `test_writer.py`,
  `test_meta_commands.py`.

## Comportement

**Table** : concaténer en un fichier, en-tête unique, `a.tsv` à `e.tsv` de
`https://raw.githubusercontent.com/lichess-org/chess-openings/master/<lettre>.tsv` (CC0 ; colonnes `eco`,
`name`, `pgn`). 3 865 positions, 395 Ko. Citer la source et la licence en tête de `openings.py`.

**`chess_coach/openings.py`** (module pur)
- Chargement paresseux en cache de la table : position (`board.epd()`) → `(eco, name)`. Environ 2 s au
  premier appel [n=1].
- `detect_opening(ucis: list[str]) -> tuple[str, str] | None` : rejoue les coups en UCI avec
  `board.push(chess.Move.from_uci(u))` ; garde la dernière position connue de la table. Transpositions comprises.
- `OPENING_CATALOG` : une ligne par ouverture, libellé → préfixes de nom, testés avec `str.startswith` dans cet
  ordre, le 1er gagne :

| Libellé | Préfixes |
|---------|----------|
| Göring Gambit | `Scotch Game: Göring Gambit`, `Scotch Game: Scotch Gambit, Göring Gambit Declined` |
| Scotch Gambit | `Scotch Game: Scotch Gambit` |
| Rousseau Gambit | `Italian Game: Rousseau Gambit` |
| Dutch Defense | `Dutch Defense` |
| Benko Gambit | `Benko Gambit` |
| Icelandic Gambit | `Scandinavian Defense: Icelandic-Palme Gambit` |
| Portsmouth Gambit | `Sicilian Defense: Portsmouth Gambit` |
| Delayed Wing Gambit | `Sicilian Defense: Wing Gambit, Deferred Variation` |
| Alapin Gambit | `French Defense: Alapin Gambit` |
| von Popiel Gambit | `Blackmar-Diemer Gambit: von Popiel Gambit` |
| von Hennig Gambit | `Caro-Kann Defense: von Hennig Gambit`, `Tarrasch Defense: von Hennig Gambit` |
| Hartlaub-Charlick Gambit | `Englund Gambit: Hartlaub-Charlick Gambit` |

- `opening_group(name) -> str` : libellé du catalogue, sinon la famille = ce qui précède le premier `:` ou `,`.
- `opening_room(group: str | None) -> str` : `chess_<slug>` (minuscules, sans accents, tirets), `chess` si `None`.
  Le préfixe évite toute collision avec les rooms `documents` et `general`.

**Fiche (`summarize`)**
- `opening` = nom détecté, sinon valeur actuelle (en-tête / slug). Nouveau champ `opening_group` (`None` si
  rien de détecté). `eco` = en-tête, sinon valeur détectée.
- `_anchor` et `_build_enriched` : retirer `.replace("-", " ")` sur l'ouverture, qui abîmerait « Caro-Kann ».

**Écriture (`write_chess_game`)** : nouveau paramètre mot-clé `room: str = "chess"`, toujours posé après le
spread de `extra` (invariant W4). `_execute_game` passe `room=opening_room(summary["opening_group"])`.

**Statistiques (`player_model.py`)**
- Fonction pure `opening_stats(games) -> dict` : `(groupe, couleur) → OpeningStats`, sur **toutes** les fiches
  reçues (pas seulement la saison), groupe = `game.get("opening_group") or opening_family(game["opening"])`,
  fiches sans ouverture ignorées, issue inconnue non comptée.
- `build_profile` : `profile.openings = opening_stats(games)`. Le comptage du badge « Répertoire » utilise le même
  groupe.
- Compte rendu : la ligne `📖` existante de `_progression_block` utilise le groupe et reste sous la même condition.

**Commande `/ouvertures`**
- `COMMANDS.update` + `openings_text(games)` dans `meta_commands.py` (le texte part de `opening_stats`).
  Une ligne par (groupe, couleur), du plus joué au moins joué :
  `Göring Gambit (blancs) : 5 V, 0 N, 3 D — 62 % [8 parties]`. Dernière ligne : nombre de fiches à issue inconnue,
  non comptées. Message dédié si aucune fiche.
- `_cmd_ouvertures` dans `telegram_interface.py`, modèle `_cmd_parties` (l. 390). L'enregistrement du handler se fait
  par `getattr` à partir de `COMMANDS`.

**Milieu de jeu (`player_model.py`, `_progression_block`)**
- Thème `"middlegame": "Milieu de jeu"` dans `LABELS`, après `opening`. `_move_themes` l'ajoute si
  `phase == "middlegame"`. Global n'a pas bougé au prototype : 1420 avant et après [53 fiches de saison].
- `_progression_block` : hors première partie, une ligne fixe sous Global :
  `Ouverture 1652 (+5) · Milieu de jeu 1412 (−3) · Finale 1380 (0)`, formatée avec `_signed`, même à variation nulle.
  `opening`, `middlegame` et `endgame` sortent des lignes fusionnées pour ne pas apparaître deux fois.

## Tests (cas nominal)

- `detect_opening` : Göring, von Hennig Caro-Kann, transposition (1.d4 e6 2.e4 → French).
- `opening_group` : un cas par libellé du catalogue, plus `Ruy Lopez: Steinitz Defense` → `Ruy Lopez`.
  « Scotch Gambit, Göring Gambit Declined » → Göring Gambit.
- `opening_room("Göring Gambit")` → `chess_goring-gambit`, `None` → `chess`.
- `write_chess_game` : room passée respectée, `extra={"room": ...}` sans effet.
- `opening_stats` : V / N / D par couleur, issue inconnue exclue. `openings_text` : format et dernière ligne.
- `_progression_block` : ligne fixe présente, phases absentes des lignes fusionnées.
- Thème `middlegame` alimenté par une épreuve en milieu de partie.

## Hors scope

Migration des fiches existantes (tronçon 04), document indexé (`summary_text` ne change que par `opening`), `/parties`,
ménage des fiches « Test » / « Ami » (#98), échiquier live.

## Fin

`pytest tests/ -q` vert. Aucune écriture dans le palace prod pendant ce tronçon.
