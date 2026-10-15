# Sprint 19 — tronçon 02 : photo interrogative sans intent (#51)

À lire avant : `CLAUDE.md`, `docs/sprint19/00_etat.md` (décision Q4),
`docs/sprint19/audit_vision.md` §2 « #51 ».

## Objectif

Une photo à légende interrogative (« c'est quoi ») passe toujours par
le pipeline texte (mémoire, contexte, AnalystAgent, historique), mais
**ne résout, ne crée et ne modifie aucun intent**. Aujourd'hui le
message enrichi `[Analyse visuelle : …] c'est quoi` crée un intent
nommé d'après la description vision, présenté ensuite à l'agent comme
« PROJET RÉCENT EN MÉMOIRE » → « c'est ta maison de montagne ».

## Fichiers à toucher

### `execution/routers/image_router.py` — `_handle_input_enriched` (l. 142-183)

1. Le payload envoyé à `llm_execution_router.execute` porte dans
   `metadata` un drapeau `skip_intent: True` en plus de la metadata
   reçue (`{**payload.get("metadata", {}), "skip_intent": True}`).
2. Le message enrichi ajoute, après le bloc `[Analyse visuelle : …]`,
   une consigne courte : ne rattacher la photo à un projet de Nico que
   si la description le justifie clairement. Garder
   `[Analyse visuelle :` (test existant
   `tests/images/test_interrogative_vision_pipeline.py:278`).

### `execution/routers/llm_router.py` — `_run_pipeline` (l. 99-260)

Si `metadata.get("skip_intent")` : sauter les étapes 2 (resolve) et 3
(`extract_intent_name` + `intent_engine.apply`) → `intent = None`,
`recall_decision = None`. Tout le reste inchangé : l'étape 1 (mémoire
globale), 4 (`session_memories` vide, déjà géré l. 146-150), 4b
(`build_context_block` avec `[Projets actifs]`), 4c (historique), 8-9
(déjà gardés par `if intent`), 10 (`memory_write SKIPPED` déjà géré,
écriture conversation conservée). Logger
`log.info("intent SKIPPED reason=skip_intent")`.

### `agents/analyst_agent.py` — `_build_system_prompt` (l. 51-63)

`PROMPT.format(intent_name=ctx.intent.name)` plante si `ctx.intent` est
`None`. Passer `ctx.intent.name if ctx.intent else "aucun"`.
**Ne pas modifier le texte de `PROMPT`.** Faire passer
`tests/agents/test_analyst_prompt_guard.py` (règle projet).

Vérifier au passage que l'agent réellement exécuté pour REASONING
(via `controller.run`, `agents/controller/controller_agent.py`) tolère
`ctx.intent is None` ; si un autre agent du chemin REASONING plante sur
`None`, le signaler en fin de livrable plutôt que d'élargir le correctif
au-delà d'une garde équivalente.

## Tests

Un test de non-régression (cas nominal) : `LLMExecutionRouter` avec un
`intent_engine` mock, payload `metadata={"skip_intent": True}` →
`intent_engine.resolve` et `intent_engine.apply` **non appelés**, une
réponse `{"text": …}` est renvoyée. Fixtures existantes à réutiliser :
`tests/execution/test_llm_execution_router.py`.
Et une assertion dans `tests/images/test_interrogative_vision_pipeline.py`
(ou nouveau test) : le payload transmis en mode enrichi porte
`metadata["skip_intent"] is True`.

## Hors scope (ne PAS faire)

- Rattachement sur correspondance forte (option Q4.b) — dette si le
  run live le demande.
- Toute modification du texte `PROMPT` d'AnalystAgent ou de `soul.md`.
- Toucher `IntentEngine` / `IntentRecallEngine`.
- Supprimer l'intent « maison de montagne » (fait par Nico au run live).

## Critère de fin

`pytest tests/ -q` vert (dont `tests/agents/test_analyst_prompt_guard.py`).
