# Sprint 56 — Tronçon 01 : une partie tronquée ou complétée reste la même partie

À lire d'abord : `CLAUDE.md`, `docs/sprint56/00_etat.md`. Diagnostic : `docs/sprint56/audit_session_2026-11-11.md`, constat 1.

## Objectif

Renvoyer une partie déjà enregistrée, coupée plus tôt ou complétée, ne crée plus de 2e fiche.
Aujourd'hui l'identité d'une partie est le hash de **tous** ses coups (`_game_hash`,
`execution/routers/chess_router.py:871`). Un PGN coupé au coup 24 donne donc un autre hash et
une autre fiche (cas Amateurspoeler du 2026-11-11 : 47 demi-coups = les 47 premiers des 53).

## Règle « même partie »

Une fiche connue est **la même partie** que le PGN reçu si :
- les coups UCI de l'un sont le début exact des coups de l'autre (longueurs > 0) ; coups de la fiche :
  `[p["uci"] for p in json.loads(fiche["plies_json"])]`, comme `_past_games` (l. 955) ;
- et l'adversaire de la fiche (`fiche["opponent"]`) est l'un des deux en-têtes `White` / `Black`
  du PGN reçu, comparaison sans casse.

Mesure sur le palace prod (299 fiches, 2026-11-11) : 2 paires répondent à cette règle, toutes deux
de vrais doublons (même adversaire) ; aucun faux positif.

Le cas « hash identique » existant (doublon exact, réanalyse sur apport d'horloges, sprint 51) ne
change pas et reste testé en premier.

## Comportement attendu

Dans `execute` (l. 933-941) et `_execute_many` (l. 981-999), quand aucune fiche n'a le même hash
mais qu'une fiche est « la même partie » :

1. **PGN reçu plus court ou égal** que la fiche → doublon : même réponse que l'existant
   (`_duplicate_text(fiche)` en simple, `Partie k — déjà envoyée` en multiple), log
   `chess_router duplicate hash=… prefix_of=<doc_id>`.
2. **PGN reçu plus long** → c'est la version complète : analyse complète comme une partie neuve,
   écriture de la nouvelle fiche **avec le timestamp de l'ancienne** (paramètre `timestamp` déjà
   prévu par `_execute_game`, l. 1023, et `write_chess_game`), **puis** suppression de l'ancienne
   fiche par `writer.delete_chess_games([ancien_doc_id])` (`memory/writer.py:195`), seulement si
   l'écriture a réussi. Log `chess_router extend old=<doc_id> new=<hash>`.

Le calcul de la progression (`before` = fiches sans la courante, l. 1070) doit exclure aussi
l'ancienne fiche remplacée, sinon la partie compte deux fois dans « avant ». Le plus simple : la
supprimer avant ce calcul (l'écriture de la nouvelle a eu lieu juste avant).

Pas de lecture mémoire supplémentaire : `_known_games()` charge déjà toutes les fiches.

## Script de nettoyage (palace prod)

`scripts/sprint56_dedup_games.py` : applique la même règle à toutes les fiches du palace, pour
chaque paire garde la plus longue et supprime la plus courte via `writer.delete_chess_games`.
Sans option : affiche les paires trouvées (id, adversaire, nombre de demi-coups) et ne touche à
rien. Avec `--apply` : supprime. Lecture via `MempalaceBridge.load_chess_games` construit comme
dans `scripts/migrate_chess_rooms.py:83`.
Attendu en prod : `chess_game_ac268123120a3de5` (Amateurspoeler, 47) et
`chess_game_ed1eca8f1df7568e` (UIALY, 101). **Le script n'est PAS lancé en `--apply` dans ce
tronçon** : c'est l'étape du run live (service arrêté, sauvegarde).

## Fichiers à toucher

- `execution/routers/chess_router.py` : la règle (fonction pure testable), `execute`, `_execute_many`,
  `_execute_game` (suppression de l'ancienne fiche).
- `scripts/sprint56_dedup_games.py` (nouveau).
- `tests/execution/test_chess_router.py`.

## Tests (cas nominal)

- Fonction « même partie » : préfixe + même adversaire → vrai ; préfixe + autre adversaire → faux.
- `execute` avec une fiche connue plus longue → réponse « déjà envoyée », pas d'analyse.
- `execute` avec une fiche connue plus courte → analyse, `write_chess_game` appelé avec le
  timestamp de l'ancienne, `delete_chess_games` appelé avec l'ancien id.
- `pytest tests/ -q` vert.

## Hors-scope (ne PAS faire)

- Pas de changement de `_game_hash` ni des doc_id existants.
- Pas de fusion de métadonnées entre les deux fiches (la nouvelle analyse fait foi).
- Fiche tronquée sans version complète au palace (#199) : rien.
- PGN sans en-tête White/Black (routé au LLM) : dette, pas ici.

## Critère de fin

Tests verts ; le script en mode lecture liste les 2 paires attendues sur le palace prod.
