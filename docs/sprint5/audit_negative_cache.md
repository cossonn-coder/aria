# Audit cache négatif providers — dette #8

**Sprint 5 / T3 — Phase 1, audit avant fix.**

Objectif : éviter de retenter un provider LLM qui vient de renvoyer
un 429, pendant un TTL court (5 min). Skipper directement vers le
suivant. Bénéfice attendu : −2-4 s de latence/message quand un
provider est en quota.

## A.1 — Localisation de la fallback chain

`llm/llm_router.py:40-151`. Une `ROUTING_TABLE: dict[LLMRole, list[provider_cfg]]`
définit la chaîne ordonnée par rôle. Chaque entrée porte
`provider`, `model`, `base_url`, `api_key` (lambda).

`LLMRouter.complete()` (ligne 161) itère séquentiellement la chaîne du
rôle demandé jusqu'au premier succès. Sleep 1 s entre tentatives sauf
après le dernier provider. **Une seule fonction de fallback, linéaire,
non récursive.** Aucune autre logique de routing dans le module.

Ordre par rôle (résumé) :

| Rôle       | Chaîne                                                                 |
|------------|------------------------------------------------------------------------|
| CHAT       | groq → groq_2 → groq_3 → mistral → openrouter → cerebras → anthropic   |
| PLANNING   | mistral → cerebras → openrouter → anthropic                            |
| REASONING  | cerebras → openrouter → anthropic                                      |
| REFLECTION | mistral → openrouter → openrouter (autre modèle) → anthropic           |

**Anthropic est en queue partout** — fallback de dernier recours,
toujours essayé même si tout le reste est cached. Pas de risque de
deadlock "tous skippés".

## A.2 — Détection actuelle des 429

Aujourd'hui : aucune. Le `try/except Exception` (llm_router.py:182)
catch tout indistinctement et passe au provider suivant.

`httpx.post(...).raise_for_status()` lève `httpx.HTTPStatusError` sur
toute réponse 4xx/5xx, avec `e.response.status_code` exposé. La
distinction se fait donc proprement :

- `isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429`
  → mettre en cache.
- Toutes les autres exceptions (5xx, timeouts, ConnectError, etc.)
  → fallback comme avant, **pas de cache**.

Ce contrat respecte la consigne T3 §C : un crash temporaire
(`ConnectError`, `TimeoutException`, 500) ne bloque pas un provider
pour 5 min — seul un 429 explicite déclenche le cache.

## A.3 — Granularité du cache

Décision : **clé = `provider_cfg["provider"]`** (string unique par
slot dans la table).

Justification :

- Les quotas free tier sont par **clé API** (par compte), pas par
  modèle. Un 429 sur Cerebras `llama-3.3-70b` s'applique à
  `llama3.1-8b` aussi (même clé).
- Groq utilise 3 clés différentes pour CHAT (`groq`, `groq_2`,
  `groq_3`). Le champ `provider` les distingue déjà — pas besoin
  de monter d'un cran.
- Un même provider peut servir plusieurs rôles avec des modèles
  différents (Cerebras `llama3.1-8b` en CHAT, `llama-3.3-70b` en
  PLANNING, `qwen-3-235b` en REASONING). Si on cachait par
  `(provider, role)` ou `(provider, model)`, un 429 sur le rôle
  CHAT ne skipperait pas Cerebras pour PLANNING — alors qu'il
  s'agit du même quota côté serveur. Faux gain.

Donc **clé simple = provider name**. Un 429 → tout le provider
skipped pour TTL secondes, peu importe le rôle.

## A.4 — Callers de la fallback chain

`LLMRouter` est instancié **une seule fois** dans
`core/kernel.py:108` puis injecté partout (planner_agent,
cognitive_classifier, LLMExecutionRouter, etc.). Tous les callers
partagent la même instance.

Conséquence design : le cache négatif est un **attribut d'instance**
(`self._negative_cache: dict[str, float]`). Pas besoin de variable
module-level ni de singleton manuel — l'injection assure le partage.

## Décision design

| Aspect       | Choix                                                          |
|--------------|----------------------------------------------------------------|
| Structure    | `dict[str, float]` — `{provider: expires_at_monotonic}`       |
| Localisation | Attribut d'instance `LLMRouter._negative_cache`               |
| Clé          | `provider_cfg["provider"]` (string, unique par slot)          |
| Valeur       | `time.monotonic() + ttl` (immune aux changements d'horloge)   |
| TTL          | `config.negative_cache_ttl_seconds`, défaut 300 (5 min)       |
| Insertion    | Sur `httpx.HTTPStatusError` avec `status_code == 429`         |
| Lookup       | Avant chaque tentative dans la boucle `complete()`            |
| Purge        | Lazy : entrée expirée supprimée au lookup                     |
| Concurrence  | Pas de Lock (GIL + opérations dict atomiques en Python)       |

Aucun blocage révélé. Fallback chain linéaire, single instance, un
seul point d'insertion. Phase 2 (fix) peut suivre.
