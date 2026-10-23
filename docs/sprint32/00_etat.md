# Sprint 32 — état de conception

**Phase** : B figée (2026-10-23) — prêt pour `/sprint-auto sprint 32`.
**Branche** : `feat/sprint32-prochaine-action`.

## Décisions arrêtées

- Q1 cible = « Prochaine action » sur un `salut` (#74) + prompt de 319 000 car. (#113). Raison :
  même racine, la branche `execution` du contrôleur (audit §3). (2026-10-23)
- Q2 correctif = messages courts et non classés → analyst seul, quelle que soit la phase de
  l'intent (piste A). Raison : corrige #74 et #113, retire aussi l'appel planner parasite ;
  ni palace ni `intents.json` touchés. Nico suit la reco. (2026-10-23)
- Q3 run live = `salut` après une analyse → réponse normale, pas de payload 3xx xxx / 1xx xxx car. ;
  `ok merci pour les tomates cerises` sans « Prochaine action ». (2026-10-23)

## Questions ouvertes

(aucune)

## Constats d'audit (détail : `audit_prochaine_action.md`)

- `salut` → CONFIRMATION → branche `else` du contrôleur → phase `execution` (intent avec
  `next_action`) → executor + critic → « Prochaine action : … » (`executor_agent.py:71`).
- Piège collant : l'executor repose une `next_action` à chaque passage.
- #113 mal diagnostiqué : les 319 023 car. sont le prompt executor (`intent.subject` sans appel =
  `repr` du dataclass avec `actions_history`, + `actions_history` recopié), 161 407 = prompt critic.
  Reconstitution : 319 067 / 161 325 car. [n=1].

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_controleur_analyst_seul.md` — messages courts et non classés : analyst seul (#74, #113) | ✅ (pytest 354 verts, non commité) |
| 02 | `02_run_live.md` — run live (Nico), messages dans `run_live_messages.txt` | ⏳ |

## Dettes

- Fermées par le sprint (après run live) : #74, #113 (rediagnostiquée : prompt executor/critic).
- Sans objet après le tronçon 01 : #39, #41, #55 → executor/critic sans chemin, à ranger avec #72.
- Nouvelle : `actions_history` stocke les messages entiers (blocs d'analyse ≈ 9 000 car.),
  `intents.json` à 327 Ko et en croissance ; plus envoyé au LLM, disque seulement.

## §REPRISE

Tronçon 01 ✅ : branche `else` du contrôleur → `["analyst"]` sans consulter la phase ; test
`tests/agents/test_controller_pipeline.py` (échoue sans le fix). Prochaine étape : commit du
tronçon 01, puis tronçon 02 (run live par Nico).
