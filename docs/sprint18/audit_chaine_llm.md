# Sprint 18 — audit de la chaîne de fallback LLM

Date : 2026-10-15. Code lu sur `feat/sprint18-llm-catalog` (= `sprint-17`).
Mesures : appels réels aux API depuis la VM, le 2026-10-15 vers 17 h.

## 1. Code concerné

### 1.a `llm/llm_router.py`

- `ROUTING_TABLE` (l. 40-151) : 4 rôles → liste ordonnée de providers.
  Chaque entrée : `provider`, `model`, `base_url`, `api_key` (lambda).
  Noms de modèles **mixtes** : certains via `config.*_model`, d'autres en
  dur dans la table.

| Rôle | Chaîne actuelle (ordre) |
|---|---|
| CHAT | groq, groq_2, groq_3 (`config.groq_model`) → mistral (`config.mistral_model`) → openrouter `meta-llama/llama-3.3-70b-instruct:free` → cerebras `llama3.1-8b` → anthropic `claude-haiku-4-5` |
| PLANNING | mistral → cerebras `llama-3.3-70b` → openrouter `meta-llama/llama-3.3-70b-instruct:free` → anthropic |
| REASONING | cerebras (`config.cerebras_model`) → openrouter `google/gemma-3-27b-it:free` → anthropic |
| REFLECTION | mistral → openrouter `nvidia/nemotron-3-super-120b-a12b:free` → anthropic |

- `DEFAULT_CHAIN = ROUTING_TABLE[LLMRole.CHAT]` (l. 154).
- `complete()` (l. 240-301) : parcourt la chaîne ; skip si provider en
  cache 429 ; `_call` ; sur exception → log `[LLM FALLBACK]`, cache si
  429, `sleep(1)`, provider suivant. Toute exception déclenche le
  fallback ; **un retour sans exception est un succès, quel que soit le
  contenu**.
- `_call()` (l. 315-425) : branche `anthropic` (API Messages, log
  `[LLM] Anthropic (…) a répondu.`) ; sinon format OpenAI-compatible
  `{base_url}/chat/completions`, payload figé `model/messages/temperature/
  max_tokens`, headers OpenRouter spécifiques. Contenu lu par
  `data["choices"][0]["message"]["content"]` (l. 417), **sans log de
  succès** pour les providers OpenAI-compatibles.

### 1.b `config.py`

l. 19-26 : clés `groq_api_key{,_2,_3}`, `mistral_api_key`,
`cerebras_api_key`, `sambanova_api_key`, `openrouter_api_key`,
`anthropic_api_key`, `hf_token`. **Pas de `deepseek_api_key`** (la clé
`DEEPSEEK_API_KEY` est dans `.env`, lue seulement par `bin/`).
l. 30-34 : `groq_model`, `cerebras_model`, `gemini_model` (inutilisé),
`mistral_model`, `sambanova_model` (inutilisé).
l. 38-42 : modèles vision (`groq_vision_model`, `openrouter_vision_models`).

### 1.c Callers de `LLMRouter.complete` (rôle, `max_tokens`)

| Caller | Rôle | max_tokens |
|---|---|---|
| `agents/analyst_agent.py:48` | rôle de l'opération (`cognition/cognitive_context.py:38-46` : CHAT sauf PLANNING→PLANNING, REASONING→REASONING) | 800 |
| `agents/planner_agent.py:46` | PLANNING | 600 |
| `agents/critic_agent.py:49` | CHAT | 300 |
| `agents/executor_agent.py:51` | CHAT | 200 |
| `cognition/cognitive_classifier.py:224` | CHAT | 60 |
| `llm/intent_namer.py:22` | CHAT | 20 |

**`LLMRole.REFLECTION` n'a aucun caller** (grep exhaustif) : chaîne morte.

### 1.d Hors `ROUTING_TABLE`

- `llm/image_router.py:30-58` `VISION_ROUTING_TABLE` : groq ×3
  `config.groq_vision_model` (`meta-llama/llama-4-scout-17b-16e-instruct`)
  puis OpenRouter `config.openrouter_vision_models`.
- `scripts/check_keys.py` : script de dev, modèles en dur
  (`mistral-small-latest`, `mistralai/mistral-7b-instruct:free`, …).
- `bin/write-deepseek.py:32` : `MODEL_FAST = "deepseek-v4-flash"` (outil de dev).

## 2. État des providers (mesuré)

| Provider | Constat | Preuve |
|---|---|---|
| groq ×3 | les 3 clés valides (`/models` 200). `llama-3.3-70b-versatile` retiré → 404. Dispo texte : `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, `allam-2-7b`. | appel réel : `qwen/qwen3.8-27b` 200 en 0,24 s [n=1], `gpt-oss-120b` 200 en 0,42 s [n=1] |
| cerebras | **402 payment_required** sur tous les modèles listés (`gpt-oss-120b`, `qwen-3.8-27b`) : l'offre gratuite de la clé n'existe plus. | appel réel |
| mistral | **429 code 1300** même sur une requête de 3 tokens isolée → quota épuisé (pas une rafale). `mistral-small-latest` et `mistral-small-2603` listés. | appel réel |
| openrouter | Les 2 modèles `meta-llama/llama-3.3-70b-instruct:free` et `google/gemma-3-27b-it:free` n'existent plus. 14 modèles `:free` listés aujourd'hui (dont `google/gemma-4-31b-it:free`, `nvidia/nemotron-3-super-120b-a12b:free`). `gemma-4-31b-it:free` → 429 à l'essai ; `nemotron-3-super` → 200 en 7,9 s [n=1] mais contenu vide (raisonnement a mangé 300 tokens). | `/models` + appels réels |
| deepseek | clé valide. Modèles : `deepseek-flash`, `deepseek-v4-pro` (`deepseek-v4-flash` répond aussi, alias non listé). 200 en 1,8-3,0 s [n=1 par modèle]. OpenAI-compatible, `base_url` `https://api.deepseek.com`. | appels réels |
| anthropic | `claude-haiku-4-5` répond (run live sprint 17). | journalctl |

Nota : au run live sprint 17, la chaîne REFLECTION (nemotron) n'a jamais
été appelée ; les 404 OpenRouter venaient tous de `llama-3.3-70b-instruct:free`.

## 3. Piège : les modèles à raisonnement

`gpt-oss-120b` (groq), `deepseek-flash` / `deepseek-v4-*` et `nemotron`
raisonnent avant de répondre, et ce raisonnement **consomme
`max_tokens`**. Mesure avec `max_tokens=20` (budget d'`intent_namer`) :

| Modèle | Paramètre | content | finish |
|---|---|---|---|
| groq `openai/gpt-oss-120b` | — | `''` | length |
| groq `openai/gpt-oss-120b` | `reasoning_effort: low` | `'**Balcon'` (tronqué) | length |
| groq `qwen/qwen3.8-27b` | — | `'Jardin balcon tomates'` | stop |
| deepseek `deepseek-flash` | — | `''` | length |
| deepseek `deepseek-flash` | `thinking: {type: disabled}` | `'**Potager balcon tomates**'` | stop |

Conséquence avec le code actuel : un `content` vide (ou `None`) est
retourné **comme un succès** par `_call` (l. 417-425) → pas de fallback,
le caller reçoit une chaîne vide (classifier et `intent_namer` à 60 et 20
tokens sont les plus exposés). Un modèle à raisonnement ne peut entrer
dans la chaîne que si (a) son raisonnement est désactivé par paramètre,
ou (b) un contenu vide déclenche le fallback.

`_call` ne permet aujourd'hui aucun paramètre de payload par provider
(payload figé l. 407-412).

## 4. Vision (hors périmètre demandé, constaté au passage)

- groq `meta-llama/llama-4-scout-17b-16e-instruct` absent de `/models`
  → vision groq probablement cassée.
- OpenRouter `nvidia/nemotron-nano-12b-v2-vl:free` et
  `baidu/qianfan-ocr-fast:free` absents des 14 `:free` listés.
- Non testé par appel réel. Vision = `llm/image_router.py`, chemin
  distinct.

## 5. Constats annexes (dettes)

- `config.gemini_model`, `sambanova_model`, `sambanova_api_key` : config
  morte (déjà notée sprint 16, non ouverte).
- `LLMRole.REFLECTION` : aucun caller.
- `bin/write-deepseek.py` utilise un alias non listé (`deepseek-v4-flash`),
  fonctionne aujourd'hui.
- `scripts/check_keys.py` teste des modèles retirés.

## 6. Couverture des agents et des callers (revue 2026-10-15, question de Nico)

Agents (`agents/`) : `AnalystAgent`, `PlannerAgent`, `ExecutorAgent`,
`CriticAgent`. `BaseAgent` est la classe abstraite (+ `AgentContext`),
`AgentRegistry` (`registry_agent.py`) le conteneur, `AgentController`
(`agents/controller/controller_agent.py`) choisit le pipeline :

| Opération / phase | Pipeline |
|---|---|
| FACT_RECALL, MEMORY_QUERY, PROFILE_QUERY, META_MEMORY, REASONING | analyst |
| PLANNING, ou phase d'intent `planning` | analyst → planner (planner écrase `ctx.result`) |
| autres, phase `execution` | executor → critic |
| autres, phase `creation` ou inconnue | analyst |

Tous les appels LLM de prod (grep `.complete(` exhaustif) :

| Appelant | Rôle | max_tokens | Chaîne après sprint 18 |
|---|---|---|---|
| AnalystAgent | CHAT / PLANNING / REASONING selon l'opération | 800 | texte |
| PlannerAgent | PLANNING | 600 | texte |
| ExecutorAgent | CHAT | 200 | texte |
| CriticAgent | CHAT | 300 | texte |
| cognitive_classifier | CHAT | 60 | texte |
| intent_namer | CHAT | 20 | texte |
| `LLMRouter.route()` (l. 451) | CHAT | 1000 | texte (inerte, #36) |
| Vision `ImageRouter.handle_input` | — | 512 | vision |
| Vision mode enrichi (caption interrogative) | → LLMExecutionRouter REASONING | 800 | vision puis texte |

Les 4 rôles reçoivent la même structure de chaîne : tout appelant est
couvert. Avec la réflexion désactivée sur DeepSeek et `qwen3.8-27b` qui
ne raisonne pas, les petits budgets (20, 60) sont servis (audit §3).

Constat annexe : la sortie de `CriticAgent` (`ctx.extra["critique"]`)
n'est lue nulle part → appel LLM sans effet.
`execution/routers/image_router.py:158` : commentaire « REASONING … Cerebras
qwen-3-235b », périmé après le sprint.

## 7. Génération d'images (mesuré 2026-10-15)

| Provider | Constat |
|---|---|
| Pollinations `https://image.pollinations.ai/prompt/…` | DNS OK, **aucune réponse en 90 s** (timeout client à 60 s) |
| Pollinations, nouvelle API `gen.pollinations.ai` | **401** : nécessite désormais une clé |
| HF `api-inference.huggingface.co` | **domaine inexistant** (DNS KO) |
| HF `router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell` | **410** « model deprecated … no longer supported by provider hf-inference » |

→ La génération d'images est entièrement hors service.
