# Sprint 68 — tronçon 01 : bilan Telegram plus rapide (durées, sans rappels mémoire, préchargement)

Lire d'abord `CLAUDE.md`, `docs/sprint68/00_etat.md`, puis `audit_joueur_du_bas.md` §6.4-6.5.

## Objectif

Une partie envoyée sur Telegram : (1) le journal dit combien de temps prend chaque étape ;
(2) le bilan ne fait plus de recherche vectorielle dans la mémoire ; (3) l'embedder et Maia sont
chargés au démarrage d'ARIA, pas au premier message.

## Constats (vérifiés au code le 2026-11-25)

- `execution/routers/chess_router.py:_execute_game` enchaîne : diagrammes (`render_position`),
  `summarize` + `write_chess_game`, progression (`load_chess_games` + 2 `build_profile`),
  `self.llm_execution_router.execute({... "metadata": {**metadata, "forced_intent_name": …,
  "skip_history": True}})`, puis miniatures (`update_chess_game_minis`) et courbe.
- `execution/routers/llm_router.py:_run_pipeline` (LLMExecutionRouter) fait, avec `message` = tout
  le prompt enrichi (~9 000 car.) : `retrieve_memories` (étape 1), `find_documents`,
  `retrieve_by_intent` (étape 4), `build_context_block` (`cognition/context_builder.py`, appelle
  `bridge.retrieve_semantic`), puis `load_consignes` → `_rules_block`. Recherche vectorielle à
  chaud : ~4 s par appel avec une requête de 9 000 caractères [3 mesures].
- Le drapeau `skip_history` (même fonction, étape 1b) est le précédent à imiter.
- `bot.py:main` construit le bridge (`MempalaceBridge(store=search, get_by_metadata=…)`), puis
  `start_board_server(...)`. L'embedder se charge à la première recherche (~24 s à froid
  [1 mesure]) ; Maia par `chess_coach.difficulty._load(models_dir)` (cache, ~6 s [1 mesure]).

## À faire

1. **Durées au journal.** Dans `_execute_game`, une ligne `chess_timing` en fin de pipeline avec
   les secondes de chaque étape (diagrammes, fiche, progression, llm, miniatures, courbe). Dans
   `_run_pipeline`, une ligne avec la durée de la préparation (étapes 1 à 4b) et celle de
   `controller.run`. Format libre, une ligne chacune, `log.info`.
2. **Drapeau `skip_memory`.** `_execute_game` l'ajoute aux métadonnées, à côté de `skip_history`.
   Dans `_run_pipeline`, s'il est vrai : aucune de `retrieve_memories`, `find_documents`,
   `retrieve_by_intent`, `build_context_block` ; mémoires vides (même forme que
   `{"hits": [], "count": 0}` déjà utilisée pour `session_memories`), `context_block` réduit aux
   règles et consignes (`_rules_block(consignes)`, garder `load_consignes`). Log
   `memory_recall SKIPPED reason=skip_memory`. Intent forcé, écriture épisodique et conversation :
   inchangés.
3. **Préchargement.** Dans `bot.py`, un thread daemon lancé au démarrage : une recherche courte
   via le bridge (charge l'embedder ; règle 2 : lecture par le bridge) puis
   `difficulty._load(config.maia_models_dir)`. Log de fin avec la durée. Une erreur est loguée
   (`log.exception`), le service continue.

## Tests (cas nominal)

- `_run_pipeline` avec `skip_memory=True` : le bridge factice ne reçoit aucun appel
  `retrieve_memories` / `retrieve_by_intent` / `retrieve_semantic` / `find_documents`, et le LLM
  est appelé.
- `_execute_game` transmet `skip_memory: True` (adapter un test existant du chess_router si l'un
  capture déjà les métadonnées).

## Hors scope

- Ne pas toucher aux écritures (tronçon 02), à la recherche explosive (tronçon 03), à l'ordre des
  chaînes LLM, au prompt AnalystAgent.
- Pas de `skip_memory` ailleurs que dans le bilan d'une partie. `_execute_many` (plusieurs
  parties collées) appelle `_execute_game` : il en hérite, c'est voulu.

## Critère de fin

`pytest tests/ -q` vert ; le journal d'un bilan (test ou sandbox) montre `memory_recall SKIPPED`
et la ligne `chess_timing`. Gain réel : run live (tronçon 06).
