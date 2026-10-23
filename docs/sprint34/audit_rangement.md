# Sprint 34 — audit : code sans caller (#72 élargie) et `actions_history` (#114)

Date : 2026-10-23. Code au commit `89b2dbc` (`main`, tag `sprint-33`).
Sources : code lu intégralement (fichiers ci-dessous), grep exhaustif hors `venv/`,
lecture seule de `~/.aria/intents.json`.

## 1. #72 — code sans caller

### 1.a Inventaire (grep `--include=*.py`, hors `venv/`)

| Fichier | Contenu | Références hors lui-même |
|---|---|---|
| `agents/executor_agent.py` | `ExecutorAgent` (prompt « ACTION / STATUS », écrit `next_action` et `actions_history`) | `agents/registry_agent.py:4,21` seulement |
| `agents/critic_agent.py` | `CriticAgent` (critique stockée dans `ctx.extra["critique"]`, jamais lue — #55) | `agents/registry_agent.py:5,22` seulement |
| `cognition/cognitive_dispatcher.py` | `CognitiveDispatcher` (registre de handlers par op) | aucune |
| `cognition/dispatcher_types.py` | `DispatchResult` (TypedDict) | aucune |
| `execution/execution_plan_builder.py` | `ExecutionPlanBuilder` | aucune |

- Le registre (`agents/registry_agent.py`) instancie les 4 agents ; seul caller du
  registre : `execution/routers/llm_router.py:37,103` (`AgentRegistry()` puis
  `AgentController(self.registry)`).
- `AgentController.run` (`agents/controller/controller_agent.py`) ne compose plus que
  `["analyst"]` ou `["analyst", "planner"]` depuis le sprint 32 : `registry.get("executor")`
  et `registry.get("critic")` ne sont jamais appelés. Aucun autre `.get(` du registre.
- Aucune référence par chaîne `"executor"` / `"critic"` en prod. Tests :
  `tests/agents/test_controller_pipeline.py:28,39-40` les nomme dans un registre **factice**
  (MagicMock) et vérifie qu'ils ne sont pas appelés.

### 1.b Orphelins créés par la suppression

| Symbole | Seuls usages après suppression |
|---|---|
| `ExecutionPlan` (`execution/execution_types.py:19-22`) | aucun (seul import : `execution_plan_builder.py:3`) |
| `Intent.infer_phase` (`intent/intent.py:110-115`) | `tests/agents/test_controller_pipeline.py:16` (assertion de mise en place) |
| `IntentPhase` (`intent/intent.py:33-36`) | `infer_phase` seulement |

`ExecutionStatus` / `ExecutionResult` (même fichier) : hors sujet (`ExecutionResult` cité en
commentaire du kernel, `ExecutionStatus` déjà sans usage → dette préexistante, non touchée).

### 1.c Dettes rattachées

- #39 (executor/critic sans historique), #41 (absents de l'inventaire `complete`), #55
  (critique jamais lue) : sans objet depuis le sprint 32 ; se ferment avec la suppression.
- #36 (`LLMRouter.route()` inerte) : **distincte**, non touchée. Elle est le seul caller de
  `Intent.build_llm_context` (`llm/llm_router.py:428-447`).

## 2. #114 — `actions_history` qui grossit `intents.json`

### 2.a Écriture

`Intent.add_action` (`intent/intent.py:191-192`) : `self.actions_history.append(action)`.
Appelé par `IntentEngine.apply` (`intent/intent_engine.py`) :

| Ligne | Branche | Contenu |
|---|---|---|
| 145, 150 | CREATE, nom existant (exact / sémantique) | message **entier** |
| 155 | CREATE, nouvel intent | `created_from_message:` + 100 car. |
| 172 | ATTACH | message **entier** |
| 185 | SPLIT, nom existant | message **entier** |
| 193 | SPLIT, nouvel intent | `split_from_context:` + 100 car. |

Le `message` reçu est celui de `LLMExecutionRouter` : pour une analyse de partie,
c'est le **bloc enrichi** (`forced_intent_name`, `llm_router.py:183-195`, CREATE sur nom
existant `jeux echecs` → ligne 145 → ≈ 9 000 car. par analyse).

Persistance : `IntentEngine.save` (`intent_engine.py:233-235`) → `save_intents`
(`intent/intent_store.py:10-22`) réécrit **tout** le fichier, à chaque message qui porte un
intent (`llm_router.py:294-296`). Tests isolés : `tests/conftest.py:101` redirige
`STORE_PATH` vers `tmp_path`.

### 2.b Lecteurs de `actions_history`

| Lecteur | État |
|---|---|
| `ExecutorAgent` | supprimé par #72 |
| `Intent.infer_phase` | orphelin après #72 (§1.b) |
| `Intent.actions` (property) | `tests/cognition/test_intent_engine.py:43` (compte ≥ 2) ; `intent_compression_engine.py:101-104` (voir §3) |
| `Intent.build_llm_context` | caller unique `LLMRouter.route` (#36, inerte) |
| `intent_store.save/load` | sérialisation |
| `scripts/inspect_intents.py`, `clean_intents.py`, `diagnose_retrieval.py`, `embedder_bench/cleanup_intent_fantome.py` | comptent les entrées / affichent la dernière |

→ Après #72, **aucun lecteur prod du contenu** : le champ n'est qu'écrit. Le compte
d'entrées reste utilisé (scripts, test).

### 2.c Mesure (`~/.aria/intents.json`, 2026-10-23 11:58)

- 343 805 octets, 9 intents, 119 actions, **326 438 car. d'actions** (95 % du fichier).
- 69 actions > 300 car. ; la plus longue 9 621 car.
- `jeux echecs` ×2 (64 et 33 actions), `plantation tomates balcon est` 10, autres ≤ 3.
- Plafond 100 car./action (idiome `created_from_message:`) : ≤ 11 900 car. d'actions
  [borne haute 119 × 100, hors en-têtes JSON].

## 3. Constats adjacents (hors scope, dettes)

- `intent_compression_engine.py:101` : `merged.actions = []` affecte une property sans
  setter → `AttributeError` si la fusion s'exécute ; `i.embedding` posé dynamiquement par
  `load_intents`. Jamais observé : fusion probablement jamais déclenchée. Non vérifié.
- `intent_store.py:44` : `print()` dans `load_intents` (règle « jamais print en prod »).
- Deux intents `jeux echecs` (dédoublonnage par nom en défaut, ou antérieurs au sprint 22).
- `ExecutionStatus` sans usage.

## 4. Pistes #114

| Piste | Point de code | Fichier existant | Effet |
|---|---|---|---|
| A. Tronquer à 100 car. dans `add_action` | `intent.py:191` (1 point, 4 appels couverts) | reste à 343 Ko | futur seul |
| **B. Tronquer à 100 car. dans `save_intents`** | `intent_store.py:20` (1 point) | réécrit à la 1re sauvegarde | passé + futur ; mémoire vive longue jusqu'au redémarrage, sans lecteur |
| C. A + migration ponctuelle (script) | 2 points | script à lancer par Nico | passé + futur |
| D. Supprimer le champ | store, intent, scripts, test | — | plus large, `infer_phase` / scripts à revoir |
