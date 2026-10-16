# Sprint 23 — Audit : lecture d'URL collée (#69)

Date : 2026-10-16. Base : `main` @ `7a3864e` (tag `sprint-22`).

## 1. Constat : aucune lecture d'URL aujourd'hui

Grep `extract|raw_content|http` hors `venv/` et tests : seuls les appels
HTTP sortants existants (providers LLM, vision, image, `web/tavily_search.py`
qui n'appelle que `/search`). Aucune détection d'URL dans le classifier ni
dans `interfaces/telegram_interface.py`.

Chemin actuel d'un message « https://… » (> 10 car.) :
`classify_operation` → heuristique web (`_WEB_SEARCH_PHRASES`, pas de match)
→ heuristique image → longueur > 10 → cache `aria_classifier` → LLM
`CLASSIFIER_PROMPT` (aucune catégorie URL) → probablement `reasoning` /
`unknown` → `llm_router` : le LLM voit l'URL en texte et ne peut pas la lire
(il invente ou répond qu'il n'a pas accès).

## 2. Point d'extension prévu (sprint 22)

`execution/routers/web_router.py:8-9` : « une capacité future (lecture
d'URL, météo…) = une branche dans execute() + un handler + un module
fournisseur ». Aiguillage sur `payload["op_type"]` (`web_router.py:48-54`).

Ajouter une capacité touche donc :

| Fichier | Ajout |
|---|---|
| `cognition/cognitive_context.py:19` | membre `CognitiveOperation` (ex. `URL_READ`) |
| `core/kernel.py:47-59` `_ROUTING_TABLE` | `URL_READ → "web_router"` |
| `execution/routers/web_router.py` | branche `execute()` + `_handle_url()` |
| `web/tavily_search.py` (ou module voisin) | `extract(url)` |
| `cognition/cognitive_classifier.py` | heuristique de détection, avant la règle « court → CONFIRMATION » |

`MEMORY_TOP_K` / `LLM_ROLE_MAP` (`cognitive_context.py`) n'ont pas d'entrée
`WEB_SEARCH` : sans objet, le web_router délègue en `REASONING`. Même chose
attendue pour `URL_READ`.

## 3. API Tavily `/extract` — vérifiée par appel réel (2026-10-16)

`POST https://api.tavily.com/extract`, `Authorization: Bearer <clé>`,
`json={"urls": [...]}` → HTTP 200 :

```
{"results": [{"url", "title", "raw_content", "images"}],
 "failed_results": [{"url", "error": "Failed to fetch url"}],
 "response_time", "request_id"}
```

- URL injoignable → **pas d'exception HTTP** : elle atterrit dans
  `failed_results`, `results` vide. Le module doit traiter ce cas en échec.
- `raw_content` = markdown de la page **brute** : la page Wikipédia
  « Moteur Stirling » fait **85 044 car.**, menus et navigation inclus
  (« [Aller au contenu](#bodyContent) … Menu principal … »). Troncature
  obligatoire avant injection.

## 4. Chaîne de délégation et effet sur l'historique

`_handle_search` (`web_router.py:59-96`) enrichit le message puis appelle
`llm_execution_router.execute({"op_type": REASONING, "content": enriched,
"metadata": {..., "skip_intent": True}})`.

Dans `LLMExecutionRouter._run_pipeline` (`execution/routers/llm_router.py`) :

- `:112` `retrieve_memories(message)` — la requête vectorielle est le
  message **enrichi** (l'embedder tronque à 512 tokens, sans gravité).
- `:138-141` `skip_intent` → `intent = None` → `:250` pas d'écriture
  épisodique (`memory_write SKIPPED`). Bon pour une page web.
- `:272` `write_conversation_turn(conversation_key, "user", message)` —
  **le message enrichi est écrit dans `aria_conversation`**, puis rechargé
  aux tours suivants (`:126`, `n = max_history_turns × 2 = 20` messages,
  `config.py:71`).

Conséquence pour la lecture d'URL : le contenu tronqué de la page est
renvoyé au LLM pendant les 10 tours suivants. Coût en tokens à chaque tour,
mais c'est aussi ce qui permet une question de suivi (« et que dit
l'article sur X ? ») sans relire la page. Même mécanisme, déjà en prod, pour
`web_search` (≈ 2,5 k car. par recherche).

Règles inviolables : le router n'écrit rien (écriture par
`LLMExecutionRouter`, règle 1), lecture de l'historique par le bridge
(règle 2), router retourne ce que retourne `LLMExecutionRouter`
(`{"text"}`, règle 4). Rien à changer côté kernel hors table de routing.

## 5. Classification

`classify_operation` (`cognitive_classifier.py:213-263`) : l'heuristique
web est en position 2 (avant image et « court »). Une URL est détectable de
façon déterministe (`https?://\S+`) : pas besoin de catégorie LLM ni de
toucher `CLASSIFIER_PROMPT`. Le cache `aria_classifier` n'est pas consulté
pour un message attrapé par heuristique.

Cas frontaliers :
- URL seule sans instruction (cf. taxonomie sprint 6, `audit_taxonomy.md:665`
  « copier-coller sans instruction → demander l'intention »).
- URL + « cherche en ligne … » : les deux heuristiques matchent.
- Plusieurs URL dans le message.
- Lien image (`.jpg`) ou PDF : Tavily extrait ce qu'il peut, hors scope.

## 6. Dettes adjacentes repérées (hors scope)

- Message enrichi stocké dans `aria_conversation` (§4) : coût tokens
  récurrent, déjà vrai pour `web_search` (rejoint #73).

## 7. Mesures complémentaires (2026-10-16, page Wikipédia « Moteur Stirling », n=1)

| Requête `/extract` | Taille | Début du contenu utile |
|---|---|---|
| défaut (markdown) | 79 889 car. | car. 16 378 (menus + liens interlangues avant) |
| `format: "text"` | 36 780 car. | car. 1 634 |
| `query` + `chunks_per_source: 3` | 2 388 car. | immédiat (passages ciblés) |

Synthèse de la page `format: "text"` entière via `deepseek-flash`
(`_text_chain(...)[3]`, sans Groq) : 10 337 tokens prompt, 230 tokens
réponse, 2,7 s, synthèse fidèle.

Chaîne LLM : `_text_chain` (`llm/llm_router.py:40-80`) = groq ×3 →
DeepSeek → Anthropic Haiku, pour les 4 rôles. Aucun moyen d'exclure Groq
pour un appel sans nouveau rôle dans `ROUTING_TABLE` (`:82-87`).
