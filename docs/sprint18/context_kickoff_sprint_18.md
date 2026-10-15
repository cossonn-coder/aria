─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 18 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-15
**Tag de référence sortie**       : `sprint-17`
**État sprint 17**                : CLOS. Branchement conversationnel
  (lecture + écriture `aria_conversation`, Analyst en forme messages)
  livré en 3 tronçons (`a29d0eb`, `641baa4`, run live `f3a36bd`).
  Détail : `docs/sprint17/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 17 (rappel synthétique)

- Tests isolés du palace et d'`intents.json` de prod (fixture autouse
  `isolate_storage`). Fin des 286 docs factices écrits en prod.
- `LLMExecutionRouter` lit les 10 derniers tours (`chat_id`) et écrit
  user + assistant dans `aria_conversation`, même sans intent résolu.
- `AnalystAgent` en forme messages ; system prompt de base unique
  (`LLMRouter.build_base_system_prompt()`).
- Run live 2026-10-15 (palace et intents remis à zéro, archives
  `*.pre-sprint17-<TS>`) : conversation tomates 4 messages, historique
  relu (0/2/4/6 messages), rappel correct au 4e message.
  **#34 fermée.**

─────────────────────────────────────────────────────────────────────────

## Cible sprint 18 : chaîne de fallback LLM (demande Nico)

Constat run live sprint 17 : seul Anthropic (`claude-haiku-4-5`)
répond. Chaque appel traverse ~6 échecs avant lui, ~6-8 s perdues
par appel [n=4 messages].

Vérifié le 2026-10-15 via `GET /models` de chaque provider :

| Provider | Modèle configuré | État |
|---|---|---|
| groq ×3 | `llama-3.3-70b-versatile` | retiré → 404. Dispo : `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` |
| cerebras | `llama3.1-8b`, `llama-3.3-70b`, `qwen-3-235b-a22b-instruct-2507` | retirés → 404. Dispo : `gpt-oss-120b`, `qwen-3.8-27b` |
| openrouter | `meta-llama/llama-3.3-70b-instruct:free`, `google/gemma-3-27b-it:free` | retirés → 404 |
| openrouter | `nvidia/nemotron-3-super-120b-a12b:free` | listé, mais 404 au run (cause non investiguée) |
| mistral | `mistral-small-latest` | 429 (quota) |
| deepseek | — | absent de `ROUTING_TABLE` ; clé `DEEPSEEK_API_KEY` valide (`/models` → 200), utilisée seulement par `bin/` |

Objectif : (1) remplacer les noms de modèles retirés par des modèles
disponibles ; (2) ajouter DeepSeek au catalogue (`ROUTING_TABLE`,
`config.py`). Lieux : `llm/llm_router.py` (lignes ~40-150, modèles
en dur ET via `config`), `config.py` (lignes 19-40),
`scripts/check_keys.py` (modèles en dur).

À trancher en conception : modèle par provider et par rôle, position
de DeepSeek dans chaque chaîne, sort de Mistral (429), modèles de
vision OpenRouter (non vérifiés), centralisation des noms en dur
dans `config.py` ou non.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-15 (post sprint 17)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert ; lien possible avec les embeddings `aria_conversation` |
| 32 | Digression Normandie → Belgique | à reconfirmer : #34 fermée |
| 33 | Garde runbook `"mempalace-fork" in __file__` | ouvert, polish trivial |
| 34 | Perte du contexte conversationnel multi-tour | **FERMÉE sprint 17** |
| 35 | Tests dépendants de l'auto-sys.path pytest | ouvert |
| 36 | `LLMRouter.route()` inerte, jamais appelée | ouverte sprint 17 |
| 37 | `max_history_turns` compte des tours, l'API des messages | ouverte sprint 17 |
| 38 | Double présence épisodique / conversation dans le contexte | ouverte sprint 17 |
| 39 | executor/critic (phase `execution`) sans historique | ouverte sprint 17 |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouverte sprint 17 |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | ouverte sprint 17 |
| 42 | Chaîne de fallback LLM moribonde + DeepSeek absent | **cible sprint 18** |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouverte sprint 17, cosmétique |

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-17` (tag sur le commit de clôture
  documentaire).
- Branche sprint 18 à créer sur demande de Nico (nom proposé :
  `feat/sprint18-llm-catalog`).
- Prochaine étape : `/conception sprint 18`.
