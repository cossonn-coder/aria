# Sprint 17 — état (A3 branchement caller, clôture fil rouge #34)

**Phase** : B figée le 2026-10-15 → prêt pour `/sprint-auto sprint 17`
**Branche** : `feat/sprint17-conversation-wiring`
**Docs** : `context_kickoff_sprint_17.md` (cadrage initial, mai),
`audit_branchement_caller.md` (tour 1, 2026-05-25, revérifié 2026-10-15)

## Carte des tronçons

| # | Kickoff | Qui | État |
|---|---|---|---|
| 01 | `01_isolation_tests.md` — tests isolés du palace et d'`intents.json` de prod | /sprint-auto | ✅ |
| 02 | `02_branchement.md` — lecture + écriture conversationnelle, Analyst en forme messages | /sprint-auto | ✅ |
| 03 | `03_run_live.md` — reset mémoire prod + conversation Telegram 4 messages | Nico | ✅ |

## Décisions arrêtées (2026-10-15, Nico)

- Q1 : plan de l'audit retenu (C1 + C2 + D1–D8). Amendement : les
  échanges sont écrits dans `aria_conversation` même sans intent résolu.
- Q2 : historique = 10 derniers tours (20 messages), sans limite de
  temps. Dette si confusions au run live.
- Q3/Q4 : découpage 01 isolation tests → 02 branchement → 03 run live.
- Q5 : remise à zéro du palace et d'`intents.json` de prod au début du
  run live (archivés, pas supprimés). Rien d'important dedans (Nico).
- Embedder : on accepte +2 embeddings CPU par message ; latence observée
  au run live.
- Niveau d'exigence : standard (faible). Le palace prod n'est touché
  qu'en ajout (nouveau wing) + reset validé par Nico.

## Constats de la revérification (2026-10-15)

- Audit toujours vrai (seuls `bin/` et un commentaire ont changé depuis).
- Recall vectoriel limité à `aria_episodic` → `aria_conversation` ne
  pollue pas le recall.
- Pipeline : Analyst en tête partout sauf UNKNOWN/CONFIRMATION en phase
  `execution` (executor + critic, sans historique).
- Tests → prod : `tests/conftest.py` n'isole ni `config.mempalace_path`
  ni `intent.intent_store.STORE_PATH`. 286 docs factices en prod,
  `intents.json` réécrit à chaque `pytest`. Probable cause de la
  quarantaine `.drift-20261015-094138`. Traité par le tronçon 01.
  Note : la baseline pytest de `/sprint-auto` (avant 01) écrira encore
  en prod une fois, sans conséquence (reset au 03).

## Dettes à reporter au kickoff sprint 18

- #34 : fermée si le run live passe.
- #36 cand. : `LLMRouter.route()` inerte.
- #37 cand. : `max_history_turns` compte des tours, l'API des messages.
- #38 cand. : double présence épisodique / conversation dans le contexte.
- Nouvelle : executor/critic (phase `execution`) sans historique.
- Nouvelle : embeddings inutiles sur `aria_conversation` (latence CPU,
  insertions HNSW, lien possible avec #31).
- Nouvelle (run live 03) : chaîne de fallback LLM moribonde. Modèles
  retirés : groq `llama-3.3-70b-versatile`, cerebras `llama3.1-8b` /
  `llama-3.3-70b` / `qwen-3-235b-a22b-instruct-2507`, openrouter
  `llama-3.3-70b-instruct:free` / `gemma-3-27b-it:free` → 404. Mistral en 429.
  Seul Anthropic (claude-haiku-4-5) répond ; ~6 échecs ≈ 6-8 s perdus
  par appel LLM [n=4 messages]. DeepSeek absent de la chaîne runtime
  (clé valide, utilisée seulement par `bin/`).
- Nouvelle : `executor_agent.py` et `critic_agent.py` absents de l'inventaire
  sprint 16 des callers de `complete` (constat C3).

## §REPRISE

Tronçon 01 fait (2026-10-15) : fixture autouse `isolate_storage` dans
`tests/conftest.py` (monkeypatch `config.mempalace_path` et
`intent_store.STORE_PATH` → `tmp_path`), test `tests/test_storage_isolation.py`.
pytest 247 verts ; mtimes de `~/.mempalace/palace/chroma.sqlite3` et
`~/.aria/intents.json` inchangées après un run complet.
Tronçon 02 fait (2026-10-15) : kernel injecte `get_by_metadata` dans le
bridge ; `LLMRouter.build_base_system_prompt()` (source unique, utilisée
par la branche legacy) ; `LLMExecutionRouter` lit l'historique (clé
`chat_id`, n = `max_history_turns`×2) dans `ctx.extra["conversation_history"]`
et écrit user + assistant dans `aria_conversation` même sans intent ;
`AnalystAgent` en forme messages (`_build_system_prompt`,
`_format_memories` supprimé, `PROMPT` = PROJET RÉCENT + RÈGLES).
Écart au kickoff : `mempalace_store.get_by_metadata` renvoie `{}` sur
`PalaceNotFoundError` (sinon le 1er message après le reset du 03 plantait).
pytest 252 verts (garde-fou Analyst vert).
Tronçon 03 fait (2026-10-15, Nico) : reset palace + intents archivés
(`*.pre-sprint17-<TS>`), conversation tomates 4 messages. Historique lu
(messages=0/2/4/6), `conversation_write OK` à chaque tour, rappel correct
au 4e message (« tu me disais quoi déjà sur l'orientation ? »). #34 fermée.
Prochaine étape : clôture (kickoff sprint 18, CLAUDE.md, tag, merge, push sur OK).
Chaque tronçon met à jour la carte ci-dessus (⏳ → ✅).
