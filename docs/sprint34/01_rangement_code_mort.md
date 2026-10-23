# Tronçon 01 — supprimer le code sans caller (#72, + #39, #41, #55)

Lire d'abord : `CLAUDE.md`, `docs/sprint34/00_etat.md`. Détail : `audit_rangement.md` §1.

## Objectif

Supprimer executor, critic et trois modules sans aucune référence, plus les orphelins
que cette suppression crée. Aucun changement de comportement : depuis le sprint 32,
`AgentController` ne compose plus que `["analyst"]` ou `["analyst", "planner"]`.

## Fichiers

Supprimer (`git rm`) :
- `agents/executor_agent.py`
- `agents/critic_agent.py`
- `cognition/cognitive_dispatcher.py`
- `cognition/dispatcher_types.py`
- `execution/execution_plan_builder.py`

Modifier :
- `agents/registry_agent.py` : retirer les imports `ExecutorAgent` / `CriticAgent` et les
  entrées `"executor"` / `"critic"` du dict. Garder analyst et planner.
- `execution/execution_types.py` : retirer la classe `ExecutionPlan` (seul import :
  `execution_plan_builder.py`). Garder `ExecutionStatus` et `ExecutionResult`.
- `intent/intent.py` : retirer `IntentPhase` et la méthode `Intent.infer_phase` (seuls
  callers prod : executor et critic). Ne rien toucher d'autre (`build_llm_context` reçoit
  `phase` en paramètre, il reste).
- `tests/agents/test_controller_pipeline.py` : retirer l'assertion `infer_phase() ==
  "execution"` et les noms `"executor"` / `"critic"` (liste des agents factices et les deux
  `assert_not_called`). Le test garde son sens : intent avec `actions_history` et
  `next_action` (ex-phase « execution »), message CONFIRMATION → analyst seul, planner non
  appelé. Ajuster son commentaire d'en-tête si besoin.

Avant de supprimer, re-grep hors `venv/` chaque nom (`executor_agent`, `critic_agent`,
`ExecutorAgent`, `CriticAgent`, `cognitive_dispatcher`, `CognitiveDispatcher`,
`dispatcher_types`, `DispatchResult`, `execution_plan_builder`, `ExecutionPlanBuilder`,
`ExecutionPlan`, `infer_phase`, `IntentPhase`) : l'audit (commit `89b2dbc`) n'en trouvait
pas d'autre que ceux listés ici.

## Hors scope (ne PAS faire)

- `LLMRouter.route` et `Intent.build_llm_context` (#36) : ne pas toucher.
- `ExecutionStatus` (sans usage) : ne pas toucher.
- Commentaire historique dans `agents/controller/controller_agent.py` (mention
  executor + critic) : le laisser, il explique le choix du sprint 32.
- Le reste du controller (`before_state` inutilisé, etc.), `intent_compression_engine.py`,
  scripts sous `scripts/`, docs d'archives : ne pas toucher.
- Tronçon 02 (`save_intents`) : pas ici.

## Critère de fin

- grep hors `venv/` des noms ci-dessus : plus aucune occurrence dans le code Python
  (les docs `docs/` peuvent les citer).
- `python -c "import execution.routers.llm_router"` passe.
- `pytest tests/ -q` vert (référence 355, le nombre ne doit pas baisser).
