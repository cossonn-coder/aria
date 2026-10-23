# Tronçon 01 — messages courts et non classés : analyst seul (#74, #113)

## Objectif

Un message `CONFIRMATION` / `UNKNOWN` (ex. `salut`, `ok`) ne doit plus jamais répondre
« Prochaine action : … » ni envoyer à DeepSeek un prompt de 300 000 car. Diagnostic complet :
`docs/sprint32/audit_prochaine_action.md`.

Cause : dans `agents/controller/controller_agent.py`, la branche `else` (toute opération autre que
FACT_RECALL, MEMORY_QUERY, PROFILE_QUERY, META_MEMORY, PLANNING, REASONING) choisit le pipeline
selon `ctx.intent.infer_phase()` ; en phase `execution` (intent avec `next_action`), elle lance
`["executor", "critic"]`.

## Fichier à toucher

- `agents/controller/controller_agent.py` : la branche `else` (lignes 36-46 sur `main` `9516075`)
  devient `pipeline = ["analyst"]`, sans consulter la phase. Commentaire français court qui dit
  pourquoi (#74 : la phase `execution` répondait « Prochaine action » à un `salut` et collait à
  l'intent ; #113 : prompt executor de 319 000 car.). Le reste du fichier est inchangé.
- Si l'import `CognitiveOperation` ou une variable devient inutile, le retirer ; sinon rien d'autre.

## Comportement attendu

| Opération | Avant | Après |
|---|---|---|
| FACT_RECALL, MEMORY_QUERY, PROFILE_QUERY, META_MEMORY, REASONING | analyst | analyst |
| PLANNING | analyst + planner | analyst + planner |
| autres, phase `creation` | analyst | analyst |
| autres, phase `planning` | analyst + planner | **analyst** |
| autres, phase `execution` | executor + critic | **analyst** |

## Test à ajouter

Nouveau fichier `tests/agents/test_controller_pipeline.py`, cas nominal : `AgentController`
avec un registre factice (`MagicMock`, `get(name)` renvoie un agent factice par nom dont `run`
renvoie le ctx), `AgentContext` (voir `_make_ctx` de `tests/cognition/test_planner_agent.py`)
avec `extra={"cognitive_operation": CognitiveOperation.CONFIRMATION}` et un `Intent` en phase
`execution` (`actions_history=["x"]`, `next_action="y"`) → seul l'agent `analyst` est exécuté
(executor et critic jamais appelés).

## Hors-scope (ne PAS faire)

- Ne pas supprimer `agents/executor_agent.py`, `agents/critic_agent.py` ni leurs entrées dans
  `agents/registry_agent.py` (code devenu sans chemin : à mentionner en fin de livrable).
- Ne pas corriger `intent.subject` sans parenthèses dans executor/critic.
- Ne pas toucher `Intent.infer_phase`, `IntentEngine`, `PlannerAgent`, ni `~/.aria/intents.json`.
- Ne pas tronquer `actions_history` (dette adjacente).
- Ne pas toucher le prompt AnalystAgent.

## Critère de fin

`pytest tests/ -q` vert, nouveau test compris ; diff limité à `controller_agent.py` + le test.
