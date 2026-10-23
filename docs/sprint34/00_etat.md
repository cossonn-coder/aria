# Sprint 34 — état de conception

**Phase** : B figée (OK de Nico, 2026-10-23) — prêt pour `/sprint-auto sprint 34`.
**Branche** : `feat/sprint34-rangement` (créée depuis `main` `89b2dbc`).

## Décisions arrêtées

- Q1 cible = #72 élargie (rangement du code sans caller : executor, critic, dispatcher,
  plan builder ; + #39, #41, #55) **et** #114 (`actions_history` d'`intents.json`), en un
  seul sprint. Choix de Nico ; #115 reste en dette. (2026-10-23)
- Q2 #72 = supprimer `agents/executor_agent.py`, `agents/critic_agent.py`,
  `cognition/cognitive_dispatcher.py`, `cognition/dispatcher_types.py`,
  `execution/execution_plan_builder.py`, leurs entrées du registre, et les orphelins créés
  (`ExecutionPlan`, `Intent.infer_phase`, `IntentPhase`) ; `test_controller_pipeline` adapté.
  #36 et `ExecutionStatus` non touchés. Ferme #39, #41, #55, #72. (2026-10-23)
- Q3 #114 = troncature à 100 car. de chaque action dans `save_intents`
  (`intent/intent_store.py`) : un point, le fichier existant redescend à la 1re sauvegarde.
  Mémoire vive non tronquée (aucun lecteur). (2026-10-23)
- Q4 run live = court, sans partie : redémarrage, pas d'ImportError, `intents.json` < 20 Ko.
  Ajustement conception : `salut` seul ne sauvegarde probablement pas (namer « aucun » →
  pas d'intent → pas de `save`, `llm_router.py:224-227,294-296`) ; on ajoute un message qui
  porte un intent (tomates balcon). (2026-10-23)
- Référence tests : 355 verts sur `main` (`89b2dbc`).

## Questions ouvertes

(aucune)

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_rangement_code_mort.md` — suppression executor, critic, dispatcher, types, plan builder + orphelins (#72) | ✅ (355 verts, non commité) |
| 02 | `02_troncature_actions.md` — `save_intents` coupe chaque action à 100 car. (#114) | ⏳ |
| 03 | `03_run_live.md` — run live (Nico), messages dans `run_live_messages.txt` | ⏳ |

## Dettes

- Fermées par le sprint (à confirmer au run live) : #72, #39, #41, #55, #114.
- Nouvelles (constats d'audit, hors scope) : `intent_compression_engine.py:101` affecte la
  property `actions` sans setter (crash si fusion, non vérifié) ; `print()` dans
  `intent_store.py:44` ; deux intents `jeux echecs` ; `ExecutionStatus` sans usage.

## Repères pré-audit (2026-10-23)

- Plafond sprint 33 : `execution/routers/llm_router.py:50-51` (`HISTORY_MESSAGE_MAX_CHARS =
  1_500`, `HISTORY_BUDGET_CHARS = 6_000`), `_trim_history` l.54, appliqué l.164.
- Bloc enrichi échecs : `execution/routers/chess_router.py:640` `_build_enriched` — ordre :
  ancre, en-têtes, compteurs, niveau, historique joueur, positions critiques (faits),
  consigne, puis message original (PGN). Les 1 500 premiers car. couvrent au mieux
  l'ancre, les en-têtes, les compteurs et le début de la Position 1.

## §REPRISE

Tronçon 01 fait (5 modules supprimés, registre/types/intent/test adaptés, 355 verts ;
reste à commiter par l'orchestrateur). Suite : tronçon 02, puis run live 03 par Nico. Lire `CLAUDE.md`, ce fichier, le kickoff du tronçon en cours.
