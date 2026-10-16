─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 24 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-16
**Tag de référence sortie**       : `sprint-23`
**État sprint 23**                : CLOS. Lecture d'URL collée (#69) en 3
  tronçons de code (`44a8b1b`, `6975fe4`, `7ce486f`) + run live 03 (OK,
  re-live C/D OK après tronçon 04). Détail : `docs/sprint23/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 23 (rappel synthétique)

- Opération `URL_READ` : toute URL `https?://` → `web_router`, prioritaire
  sur `web_search` et « court → CONFIRMATION » ; première URL seulement.
- `extract` Tavily (`format: "text"`), tranches de 100 000 car. coupées en
  fin de paragraphe, synthèse via `LLMRole.DIGEST` (DeepSeek → Haiku, sans
  Groq, `max_tokens=1000`) ; message enrichi de la synthèse délégué à
  `LLMExecutionRouter` REASONING + `skip_intent` (donc en historique).
- Lecture partielle : marqueur dans le message enrichi ; « oui » / « lis la
  suite » (`detect_url_resume`, via bridge) lit la tranche suivante.
- Réponses REASONING (AnalystAgent) : `max_tokens` 800 → 1500.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 24

À choisir par Nico en `/conception`. Candidats : #44 (génération d'images),
#68 (rappels / scheduler), #73 (Groq 413 / poids de l'historique).

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-16 (post sprint 23)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert — nouvelle quarantaine au run live sprint 23 (2026-10-16 13:39) |
| 32 | Digression Normandie → Belgique | à reconfirmer |
| 33 | Garde runbook `"mempalace-fork" in __file__` | ouvert, polish trivial |
| 35 | Tests dépendants de l'auto-sys.path pytest | ouvert |
| 36 | `LLMRouter.route()` inerte, jamais appelée | ouvert |
| 37 | `max_history_turns` compte des tours, l'API des messages | ouvert |
| 38 | Double présence épisodique / conversation dans le contexte | ouvert |
| 39 | executor/critic (phase `execution`) sans historique | ouvert |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouvert |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | ouvert |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouvert, cosmétique |
| 44 | Génération d'images hors service (Pollinations timeout / 401, HF mort) | ouvert, sprint dédié (clé à créer par Nico) |
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | ouvert |
| 56 | Mode enrichi : question en anglais → réponse en français (message enrichi majoritairement FR, `user.md` « Langue : français ») | ouvert, accepté par Nico |
| 58 | #51 option (b) : rattachement photo → intent sur correspondance forte | ouvert, seulement si perte de contexte projet constatée |
| 60 | Vision : lecture fine inventée (position d'échecs), limite modèle ; le LLM texte dit alors « je ne vois pas l'image » alors que la description est dans l'historique | ouvert, accepté (reformulée sprint 20) |
| 63 | Photo analysée deux fois après redémarrage (23:16:01 / 23:16:18) — rejeu Telegram ou double envoi | instrumentée sprint 21 (log `telegram_update`), à confirmer |
| 64 | `IntentActionType.IGNORE` déclaré, jamais utilisé | ouvert, polish |
| 65 | `aria.service` versionné pointe `/home/nico/projects/aria` (installé : Nextcloud) | ouvert |
| 66 | Découpage 4096 de `send()` coupe au milieu des mots (commentaire faux) | ouvert, polish |
| 67 | IPv6 VM → Telegram injoignable | ouvert, piste si timeouts persistent |
| 68 | Rappels différés + envoi proactif (scheduler) | ouvert, sprint dédié |
| 70 | Météo dédiée (aujourd'hui via `web_search`) | ouvert |
| 71 | `print()` dans `core/kernel.py` `_normalize` | ouvert, polish |
| 72 | Code sans caller apparent : `cognition/cognitive_dispatcher.py`, `execution/execution_plan_builder.py`, `cognition/dispatcher_types.py` | ouvert |
| 73 | Pression Groq : 2 × 429 en ~45 s [run live 22-03, n=1] ; depuis sprint 23, 413 Payload Too Large sur chaque réponse REASONING dès qu'une synthèse d'URL est dans l'historique (20 messages) → bascule DeepSeek, +3-4 s par réponse [run live 23-03, n=6] | ouvert, à arbitrer |

| 74 | Réponse hors sujet « Prochaine action : Résumer l'état actuel du projet potager… » à un message conversationnel (« lol non… ») [n=1, 2026-10-16] | ouvert, à diagnostiquer |
| 75 | Intent parasite `vacances normandie train` créé sur une question de suivi de lecture d'URL (« et la gastronomie normande… ») [n=1] | ouvert |
| 76 | Suite de lecture : la réponse refusionne la tranche 1 et parle de « trois parties » au lieu de deux [n=1] | ouvert, polish prompt |


Sujet de conception hors dettes (avis Claude, revue 2026-10-15) : pas de
consolidation mémoire (REFLECTION, `aria_semantic` #17,
`extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-23` (tag sur le commit de clôture
  documentaire).
- Branche sprint 24 à créer en conception, une fois la cible choisie.
- Prochaine étape : `/conception sprint 24`.
