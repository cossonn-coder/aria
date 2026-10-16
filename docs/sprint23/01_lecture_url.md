# Sprint 23 — Tronçon 01 : lecture d'URL collée

Branche : `feat/sprint23-lecture-url`. Lire d'abord `CLAUDE.md` (règles
inviolables 1-6) et `docs/sprint23/00_etat.md`. Contexte détaillé :
`docs/sprint23/audit_lecture_url.md`.

## Objectif

Un message Telegram contenant une URL `http(s)://` est lu : ARIA récupère
la page entière (Tavily `/extract`), en produit une synthèse via un LLM
**hors Groq**, puis répond à partir de cette synthèse. C'est la synthèse
(pas la page) qui part dans l'historique de conversation. Une page de plus
de 100 000 caractères est lue par tranches : ARIA annonce la lecture
partielle et propose de lire la suite (la reprise elle-même = tronçon 02).

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `llm/llm_role.py` | membre `DIGEST = "digest"` |
| `llm/llm_router.py` `ROUTING_TABLE` (~l. 82) | `LLMRole.DIGEST` → chaîne **sans les 3 entrées Groq** de `_text_chain(config.deepseek_model)` : DeepSeek puis Anthropic Haiku |
| `cognition/cognitive_context.py` | membre `URL_READ = "url_read"` ; constante partagée `URL_PARTIAL_MARKER = "[Lecture partielle :"` (relue par le classifier au tronçon 02) |
| `core/kernel.py` `_ROUTING_TABLE` | `CognitiveOperation.URL_READ.value : "web_router"` |
| `web/tavily_search.py` | fonction `extract(url)` |
| `execution/routers/web_router.py` | branche `URL_READ` dans `execute()` + handler |
| `cognition/cognitive_classifier.py` | heuristique `detect_url(message)` en tête des heuristiques texte |

## Comportement attendu

### `extract(url)` — `web/tavily_search.py`

`POST https://api.tavily.com/extract`, même auth Bearer que `search`,
`json={"urls": [url], "format": "text"}`, timeout 30 s. Réponse vérifiée
par appel réel (audit §3, §7) :
`{"results": [{"url","title","raw_content","images"}], "failed_results": [{"url","error"}], ...}`.
Une URL injoignable donne HTTP 200 avec `results` vide et l'URL dans
`failed_results` → lever une exception (le router la traite en échec).
Retour : `{"title", "url", "content"}` (`content` = `raw_content`).

### Classifier

`detect_url(message)` : première URL `https?://\S+` du message (ponctuation
finale `.,;:!?)»` retirée), ou `None`. Dans `classify_operation`, placée
**avant** `detect_web_search_intent` (une URL + « cherche en ligne » = lecture
d'URL) et donc avant la règle « court → CONFIRMATION » → `URL_READ`. Pas de
catégorie LLM, `CLASSIFIER_PROMPT` inchangé. Mettre à jour le commentaire
d'en-tête qui liste l'ordre du pipeline.

### Handler `URL_READ` — `web_router.py`

Structurer le handler autour d'une fonction de lecture d'**une tranche**
paramétrée par `(url, start, message, metadata)` : le tronçon 02 la
réutilisera avec `start > 0`. Ici, `start = 0` et `url = detect_url(message)`.

1. `extract(url)` → texte complet de longueur `total`.
2. Tranche : `text[start : start + 100_000]` (constante module
   `_SLICE_MAX_CHARS = 100_000`). Si la page continue au-delà, **couper en
   fin de paragraphe** : dernier `"\n"` de la tranche ; à défaut, dernière
   fin de phrase (`". "`) ; à défaut, dernier espace. Jamais au milieu d'un
   mot. `end = start + longueur effective`. (En `format: "text"` les
   paragraphes sont séparés par un simple `"\n"`, mesuré.)
3. Synthèse : `llm_router.complete(prompt=…, role=LLMRole.DIGEST,
   temperature=0.3, max_tokens=1000)`. Le prompt contient la tranche, le
   titre, l'URL et le message de Nico : synthèse fidèle en français,
   orientée par sa consigne s'il en donne une (sinon résumé général), sans
   rien inventer.
4. Message enrichi, puis délégation identique à `_handle_search` :
   `llm_execution_router.execute({"op_type": REASONING, "content": enriched,
   "metadata": {**metadata, "skip_intent": True}})`. `enriched` contient :
   - `[Synthèse de la page « <titre> » — <url> (caractères <start>-<end> sur <total>) :\n<synthèse>]`
   - si `end < total` : le marqueur exact
     `[Lecture partielle : <url> caractères <start>-<end> sur <total>]`
     (préfixe = `URL_PARTIAL_MARKER`, format à parser au tronçon 02) et la
     consigne : dire qu'il a lu les caractères `start` à `end` sur `total`,
     donner la synthèse / la réponse, puis **proposer de lire la suite** ;
   - sinon la consigne : répondre à partir de cette synthèse et citer l'URL ;
   - puis le message original.
5. Échec (exception d'`extract` ou de la synthèse) : `log.warning`, puis
   consigne type sprint 22 : « [Page illisible : dis-le à Nico en une
   phrase.] » + message, délégué de la même façon.

### Logs (feedback de calibrage, rien sur Telegram)

- `log.info("url_read OK url=%s page_chars=%d start=%d end=%d digest_tokens=%s", …)`
  — `digest_tokens` lu dans `response.usage` (`completion_tokens` pour
  DeepSeek, `output_tokens` pour Anthropic ; `None` si absent).
- `log.warning("url_read digest hit max_tokens=%d url=%s", …)` quand
  `digest_tokens >= 1000` (synthèse probablement coupée → curseur à monter).
- `log.warning("url_read FAILED url=%s error=%s", …)` en échec.

## Règles d'architecture

Le router n'écrit rien en mémoire (l'historique est écrit par
`LLMExecutionRouter`, règle 1) ; il ne lit rien au tronçon 01. Il retourne
ce que retourne `LLMExecutionRouter` (`{"text"}`, règle 4). Kernel : une
ligne de table de routing, rien d'autre.

## Tests à ajouter (cas nominal, fakes, pas de réseau)

- `tests/web/test_tavily_search.py` : `extract` normalise `results[0]` ;
  `results` vide → exception.
- `tests/execution/test_web_router.py` (sur le modèle existant) :
  - page courte → délégation REASONING + `skip_intent`, synthèse et URL dans
    `content`, **pas** de marqueur, `complete` appelé avec `role=LLMRole.DIGEST` ;
  - page de 250 000 car. faite de paragraphes → marqueur présent, `end`
    ≤ 100 000 et `text[end-1]` ou `text[end]` est un `"\n"` (coupe en fin de
    paragraphe) ;
  - `extract` qui lève → consigne « Page illisible ».
- `tests/cognition/` : message avec URL (y compris avec « cherche en ligne »)
  → `URL_READ` ; `detect_url` retire la ponctuation finale.
- `tests/llm/` (ou à côté des tests du router LLM existants) : la chaîne
  `DIGEST` ne contient aucun provider commençant par `groq`.

## Hors scope (ne pas faire)

- Reprise « lis la suite » / « oui » : tronçon 02.
- Mode `query` / `chunks_per_source` de Tavily, nettoyage HTML, cache de pages.
- Plusieurs URL par message (seule la première est lue).
- Toucher `LLMExecutionRouter`, `CLASSIFIER_PROMPT`, `soul.md`, le prompt
  AnalystAgent, `_handle_search`.
- Retirer Groq des autres rôles.

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests ci-dessus présents et verts.
