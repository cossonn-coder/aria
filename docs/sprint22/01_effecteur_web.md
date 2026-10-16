# Sprint 22 — Tronçon 01 : effecteur web (Tavily + `web_router`)

À lire avant : `CLAUDE.md`, `docs/sprint22/00_etat.md`,
`docs/sprint22/audit_monde_exterieur.md` (§2, §3, §7, §8).

## Objectif

Donner à ARIA une opération `web_search` exécutée par un nouveau router
`web_router` : il formule une requête, interroge Tavily, construit un message
enrichi avec les résultats et délègue la réponse au pipeline cognitif texte
(`LLMExecutionRouter`), exactement comme le mode vision enrichi.
La **classification** (qui émet `web_search`) est le tronçon 02 : ici, rien
dans `cognition/cognitive_classifier.py`.

## Fichiers à toucher (vérifiés au code, `main` @ `ea845e2`)

1. `cognition/cognitive_context.py` — ajouter `WEB_SEARCH = "web_search"` à
   l'enum `CognitiveOperation`. **Ne pas** l'ajouter à `MEMORY_TOP_K` ni à
   `LLM_ROLE_MAP` : le router web délègue en `REASONING`, jamais en `WEB_SEARCH`.
2. `config.py` — champ `tavily_api_key: str = ""`, lu dans `__post_init__`
   via `os.getenv("TAVILY_API_KEY", "")` (même style que les autres clés).
3. **Nouveau** `web/__init__.py` (vide) + `web/tavily_search.py` :
   - `search(query: str, max_results: int = 5) -> list[dict]` ;
   - `httpx.post("https://api.tavily.com/search", headers={"Authorization": f"Bearer {config.tavily_api_key}"}, json={"query": query, "max_results": max_results, "search_depth": "basic"}, timeout=15.0)`, `raise_for_status()` ;
   - retourne `[{"title", "url", "content"}]` lus dans `data["results"]`
     (format **vérifié** par un appel réel le 2026-10-16 : HTTP 200, clés
     `results[].title/url/content/score/id/raw_content`, auth Bearer OK) ;
   - clé vide → lève une exception (le router la traite comme un échec).
   - Commentaire d'en-tête : ce module est le seul à connaître le fournisseur ;
     changer de moteur = changer ce fichier.
4. **Nouveau** `execution/routers/web_router.py` — classe
   `WebExecutionRouter(BaseRouter)`, modèle : `ImageExecutionRouter`
   (`execution/routers/image_router.py`, aiguillage sur `payload["op_type"]`
   l. 83 ; délégation enrichie l. 159-218).
   - Constructeur : `llm_router` (LLMRouter), `mempalace_bridge`
     (MempalaceBridge), `llm_execution_router` (LLMExecutionRouter).
   - `execute(payload)` : si `op_type == "web_search"` → `_handle_search` ;
     sinon `ValueError` (le dispatcher la transforme en `failed`). C'est le
     point d'extension : une capacité future = une branche + un handler.
   - `_handle_search(payload)` :
     a. **Requête** : lit le dernier échange via
        `self.mempalace_bridge.load_conversation_history(conversation_key, n=2)`
        (`conversation_key = str(metadata.get("chat_id", "default"))`, même
        convention que `llm_router.py`), puis un appel
        `self.llm_router.complete(prompt=…, role=LLMRole.CHAT, temperature=0.1, max_tokens=40)`
        qui produit une requête de recherche courte à partir du dernier
        échange + du message. Indispensable pour « source ? » (la requête est
        le sujet du tour précédent). Si l'appel lève → requête = message brut.
     b. **Recherche** : `search(query)` ; extraits tronqués à 500 caractères.
        Log INFO `web_search OK provider=tavily results=%d query=%r`.
     c. **Message enrichi** :
        ```
        [Résultats web pour « <query> » :
        1. <title> — <url>
           <extrait>
        …]
        [Consigne : réponds à partir de ces résultats et termine par la liste
        des URL utilisées ; si les résultats ne répondent pas à la question,
        dis-le.]

        <message original>
        ```
     d. **Échec** (exception de `search`, ou 0 résultat) : log WARNING
        `web_search FAILED query=%r error=%s`, et message enrichi =
        `[Recherche web indisponible : dis-le à Nico en une phrase, puis réponds
        si tu peux en précisant que ce n'est pas vérifié.]` + message original.
        Pas d'erreur remontée à l'utilisateur.
     e. **Délégation** : `return self.llm_execution_router.execute({"op_type": CognitiveOperation.REASONING.value, "content": enriched, "metadata": {**metadata, "skip_intent": True}})`.
   - Le router n'écrit **rien** en mémoire (l'écriture conversation est faite
     par `LLMExecutionRouter`, règle 1).
5. `core/kernel.py` :
   - `_ROUTING_TABLE` : ajouter `CognitiveOperation.WEB_SEARCH.value : "web_router"`.
   - `_build_dispatcher` : `registry.register("web_router", WebExecutionRouter(llm_router=llm_router, mempalace_bridge=mempalace_bridge, llm_execution_router=llm_execution_router))`,
     après la construction de `llm_execution_router`.

## Tests à ajouter (cas nominal + échec, rien de plus)

`tests/execution/test_web_router.py`, avec fakes (pas de réseau) — s'inspirer
de `tests/images/test_interrogative_vision_pipeline.py` :
1. nominal : `search` monkeypatché → 2 résultats ; fake `llm_router` qui
   renvoie une requête ; fake `llm_execution_router` qui capture son payload.
   Vérifier : `op_type == "reasoning"`, `skip_intent is True`, le contenu
   contient les URL et le message original, le retour est celui du fake.
2. échec : `search` lève → le contenu délégué contient
   `Recherche web indisponible`, aucune exception remontée.
3. `tests/web/test_tavily_search.py` : `httpx.post` monkeypatché → parse
   `results` en liste de dicts `title/url/content`.

`pytest tests/ -q` vert.

## Hors scope (NE PAS faire)

- Rien dans `cognition/cognitive_classifier.py` (tronçon 02).
- Pas de lecture d'URL, pas de météo, pas de registre/plugin de capacités.
- Pas de retry, pas de cache des résultats, pas de fallback vers un autre moteur.
- Ne pas corriger le `print()` de `kernel._normalize` (dette notée).
- Ne pas toucher au prompt AnalystAgent ni à `soul.md`.

## Critère de fin

Tests ci-dessus verts + suite complète verte ; un `ExecutionOperation`
`web_search` passé au dispatcher construit par `_build_dispatcher` atteint
`WebExecutionRouter`.
