# Sprint 33 — état de conception

**Phase** : B — conception figée (2026-10-23), prête pour `/sprint-auto sprint 33`.
**Branche** : `feat/sprint33-historique`.

## Décisions arrêtées

- Q1 cible = historique trop lourd sur un `salut` (#37/#38). Raison : seul gain visible
  (latence, coût, Groq réutilisable) ; #72 et #114 restent en dettes. (2026-10-23)
- Q2 correctif = plafond 1 500 car. par message + budget total 6 000 car., rempli du plus
  récent au plus ancien, à l'étape 1b de `llm_router.py` (après la lecture bridge).
  Raison : payload simulé 11 504 car. → Groq répond ; un seul point de code ; bridge,
  écriture et lecteurs n=2 inchangés. Nico accepte la perte de détail sur les suivis
  d'analyse (seule la tête du bloc de faits reste). (2026-10-23)
- Q3 run live = partie puis `salut` → plus de `provider groq skipped (payload …)`, Groq
  répond ; une question de suivi sur la partie reste correcte. (2026-10-23)
- Détails pris par défaut (conception) : constantes de module dans `llm_router.py`
  (idiome `GROQ_MAX_PAYLOAD_CHARS`), pas de clé config ; message coupé suffixé ` […]` ;
  arrêt au premier message qui dépasse le budget (fenêtre contiguë) ; log
  `conversation_history loaded` enrichi de `chars=`.

## Questions ouvertes

(aucune)

## Constats d'audit (détail : `audit_historique.md`)

- 36 813 car. sur `salut` : historique 31 237, dont 26 683 (85 %) = 3 messages user enrichis
  d'échecs (8 636 / 8 940 / 9 107). Hors historique : 5 571.
- Cause : le message ENRICHI (échecs, web, page) est écrit comme tour `user` par
  `llm_router.py:285` et relu tel quel ; `skip_history` ne protège que l'analyse elle-même.
- #37 (nommage) et #38 (doublon épisodique, borné 400 car./souvenir) ne sont pas la cause.
- Lecteurs directs n=2 (reprise URL, `source ?`, classifier) dépendent du contenu enrichi
  stocké : ne pas toucher à l'écriture ni au bridge.

## Repères pré-audit (grep 2026-10-23, à approfondir après choix)

- #37 : `execution/routers/llm_router.py:123-135` charge `max_history_turns * 2` messages
  (`config.max_history_turns = 10`) via `bridge.load_conversation_history`.
- #72 : fichiers sans caller prod hors registre : `agents/executor_agent.py`,
  `agents/critic_agent.py`, `cognition/cognitive_dispatcher.py`,
  `cognition/dispatcher_types.py`, `execution/execution_plan_builder.py` ; référencés par
  `agents/registry_agent.py`.
- #114 : `intent/intent_engine.py:145-193` appelle `add_action(message)` avec le message entier
  (seuls les `created_from` / `split_from` sont tronqués à 100 car.). Seul lecteur restant :
  `executor_agent.py` (plus appelé) + scripts.

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_plafond_historique.md` — plafond 1 500 car./message + budget 6 000 car. (étape 1b `llm_router.py`) | ⏳ |
| 02 | `02_run_live.md` — run live (Nico), messages dans `run_live_messages.txt` | ⏳ |

## Dettes (à reporter à la clôture)

- #37 : reformulée « nommage seul, sans effet sur le volume » (conversion × 2 faite).
- #38 : reste ouverte, bornée (400 car./souvenir), pas la cause.
- Volume d'historique sur un `salut` : fermé par ce sprint si le run live passe.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_historique.md`. Conception figée : lancer
`/sprint-auto sprint 33` (tronçon 01), puis run live par Nico (tronçon 02).
