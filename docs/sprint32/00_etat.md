# Sprint 32 — état de conception

**Phase** : CLOS (2026-10-23) — tronçon 01 validé au run live par Nico.
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
| 01 | `01_controleur_analyst_seul.md` — messages courts et non classés : analyst seul (#74, #113) | ✅ (354 tests verts, `f4d396c`) |
| 02 | `02_run_live.md` — run live (Nico), messages dans `run_live_messages.txt` | ✅ (2026-10-23, validé par Nico) |

## Run live (2026-10-23, 11:02-11:09, service redémarré avec `f4d396c`)

| Message | Durée réception → `pipeline done` | Appels de réponse | Résultat |
|---|---|---|---|
| 1. partie AaronDias16 | 74 s | deepseek-v4-pro ×1 | analyse + 5 images ✓ |
| 2. `salut` | 6 s ✓ (sprint 31 : 13 s) | deepseek-flash ×1, payload 36 813 car. ✓ | pas de « Prochaine action » (Nico) ✓ |
| 3. `ok merci pour les tomates cerises` | 7 s | deepseek-flash ×1, payload 36 648 car. | changement de sujet correct, intent `plantation tomates balcon est` ✓ |

Plus aucune ligne `payload 319 023` / `161 407` (encore présentes au passage de 09:52, sur
l'ancien code). Nico n'a pas transmis le chat Telegram : l'absence de « Prochaine action »
repose sur son coup d'œil et sur le journal (un seul appel LLM, donc ni executor ni critic).

Constats :
- Le `salut` résout encore l'intent `jeux echecs` (`memory_write … intent_name=jeux echecs`),
  sans effet visible désormais.
- Le `salut` envoie toujours ≈ 37 000 car. d'historique à DeepSeek (Groq sauté) : relève de #37.

## Dettes

- Fermées : #74, #113 (rediagnostiquée : prompt executor/critic).
- Sans objet après le tronçon 01 : #39, #41, #55 → executor/critic sans chemin, à ranger avec #72.
- Nouvelle #114 : `actions_history` stocke les messages entiers (blocs d'analyse ≈ 9 000 car.),
  `intents.json` à 327 Ko et en croissance ; plus envoyé au LLM, disque seulement.

## §REPRISE

Sprint clos. Suite : `docs/sprint33/context_kickoff_sprint_33.md`, puis `/conception sprint 33`.
