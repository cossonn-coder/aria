# Tronçon 04 — aucune partie en double

## Objectif

Une partie déjà enregistrée n'est ni analysée, ni réenregistrée, ni illustrée : ARIA répond seulement qu'elle a déjà été envoyée.

## Fichiers

- `execution/routers/chess_router.py` : `execute` (lignes 577-590), `_execute_many`, `_execute_game` (`game_hash`, ligne 648).
- `tests/execution/test_chess_router.py`.

## Comportement attendu

**Identité** : même règle qu'aujourd'hui, `sha256` des UCI concaténés, 16 caractères, doc_id `chess_game_<hash>` (en-têtes ignorés). Un helper unique, partagé avec `_execute_game`. Le calcul se fait avant `analyze`, depuis `parse_pgn` (`chess_coach.analysis`) : mainline du jeu, sans moteur. PGN illisible : chemin existant, inchangé.

**Lecture** : `self.mempalace_bridge.load_chess_games()` (règle 2), en comparant `g["id"]`. Palace indisponible : on journalise et on analyse, comme `_past_games`.

**Une partie** : déjà connue → `{"text": ...}` sans appel à `analyze`, `render_position`, `write_chess_game` ni au LLM. Texte du code, pas du LLM, en une phrase : adversaire et date si la fiche les a (ex. « Cette partie contre X a déjà été envoyée le 2026-10-31. »). Ligne au journal : `chess_router duplicate hash=…`.

**Plusieurs parties** (`_execute_many`) : une ligne par doublon (`Partie k — déjà envoyée`), les autres analysées normalement. Toutes en doublon : texte seul, sans image. Deux fois la même partie dans un même message : la 2e est aussi un doublon.

**Écriture** : `write_chess_game` et son upsert restent ; il n'y a plus de second appel pour une même partie. Aucune écriture hors `memory/writer.py`.

Le chemin `/send` de l'échiquier passe par le même router : rien à ajouter.

## Tests (cas nominal)

- Partie connue : `analyze` et `write_chess_game` non appelés, texte « déjà envoyée », pas d'image.
- Partie nouvelle : pipeline inchangé.
- Plusieurs parties, une connue et deux fois la même : bon découpage.
- Les tests existants ont `analyze` monkeypatché et un bridge `MagicMock` : les adapter simplement si besoin.

## Hors périmètre

Réanalyse volontaire ; suppression de fiches parasites (#98) ; préfixes (une partie envoyée en cours de jeu puis finie = deux parties) ; migration (palace vérifié, 0 doublon sur 125 fiches [copie du 2026-11-04]).

## Critère de fin

`pytest tests/ -q` vert. À valider au run live.
