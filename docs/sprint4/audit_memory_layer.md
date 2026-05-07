# Audit couche mémoire — ARIA Sprint 4
**Date : 2 mai 2026**
**Branche : feat/sprint2-image-pipeline**
**État MemPalace au moment de l'audit (count_memory_by_wing.py) :**
```
mempalace_drawers: total=375, wings={'aria_classifier': 162, 'aria_episodic': 143, 'aria': 70}
mempalace_closets: total=32, wings={'aria': 32}
```

---

## 1. Cartographie des points d'accès mémoire dans ARIA

### Légende

- **API utilisée** : le module et la méthode appelés, au niveau le plus bas
- **Type** : read | write | inspect
- **Wing** : valeur passée en production (hardcodé ou dynamique)
- **Room** : valeur passée (hardcodé ou issue d'un paramètre)

### Tableau exhaustif

| # | Fichier:ligne | Caller | API utilisée | Type | Wing | Room | Notes |
|---|---|---|---|---|---|---|---|
| R1 | `memory/mempalace_store.py:7` | `search()` | `mempalace.searcher.search_memories()` | read | dynamique (param, défaut `"aria"`) | dynamique | Défaut wing=`"aria"` potentiellement trompeur ; ce fichier est le seul adaptateur vers `search_memories` |
| R2 | `memory/mempalace_bridge.py:87` | `MempalaceBridge.retrieve_memories()` | `self._store()` → `mempalace_store.search()` | read | `"aria_episodic"` | dynamique (param `room`) | Filtre distance>0.8 et room!="general". Demande n×2 puis tronque à n. |
| R3 | `memory/mempalace_bridge.py:139` | `MempalaceBridge.retrieve_by_intent()` | `self._store()` → `mempalace_store.search()` | read | `"aria_episodic"` | `intent_id` (param) | Recall ciblé par projet. Pas de filtre distance. |
| R4 | `memory/mempalace_bridge.py:182` | `MempalaceBridge.retrieve_semantic()` | `self._store()` → `mempalace_store.search()` | read | `"aria_semantic"` | `subject` (param, optionnel) | Faits stables sur l'utilisateur. |
| R5 | `cognition/cognitive_classifier.py:262` | `_search_cache()` | `memory.mempalace_store.search()` **importé directement** | read | `"aria_classifier"` | None (aucun filtre room) | **BYPASS** : importe mempalace_store sans passer par le bridge — viole la règle documentée dans mempalace_bridge.py ("Aucun agent, aucun router n'importe mempalace_store directement"). Seuil similarity>0.92. |
| R6 | `execution/routers/image_router.py:272` | `ImageExecutionRouter._build_generation_context()` | `self.mempalace_bridge.retrieve_memories()` | read | `"aria_episodic"` | None | Via bridge. n=3. |
| R7 | `cognition/context_builder.py:58` | `build_context_block()` | `bridge.retrieve_semantic()` | read | `"aria_semantic"` | None | Via bridge. n=5. |
| R8 | `execution/routers/llm_router.py:111` | `LLMExecutionRouter._run_pipeline()` step 1 | `self.mempalace_bridge.retrieve_memories()` | read | `"aria_episodic"` | None | Via bridge. n=MEMORY_TOP_K[operation]. |
| R9 | `execution/routers/llm_router.py:146` | `LLMExecutionRouter._run_pipeline()` step 4 | `self.mempalace_bridge.retrieve_by_intent()` | read | `"aria_episodic"` | `intent.id` | Via bridge. Null si pas d'intent résolu. |
| W1 | `memory/mempalace_writer.py:92` | `store_interaction()` | `mempalace.palace.get_collection()` | write | `"aria_episodic"` (**base**, overridable par `**metadata`) | `intent_id` (param) | **BYPASS** : appelle `mempalace.palace.get_collection()` directement (pas via searcher). Wing posé en base dans le dict meta, mais `**(metadata or {})` appliqué après → overridable par n'importe quel caller. |
| W2 | `memory/mempalace_writer.py:136` | `store_image_artifact()` | `mempalace.palace.get_collection()` | write | `"aria_episodic"` (hardcodé, non overridable) | `intent_id or "general"` | **BYPASS** : accès direct. Wing dans meta avant le spread `**metadata` → non overridable (pas de champ wing dans les métadonnées caller). |
| W3 | `memory/mempalace_writer.py:209` | `store_semantic_fact()` | `mempalace.palace.get_collection()` | write | `"aria_semantic"` (hardcodé, non overridable) | `subject` (param) | **BYPASS** : accès direct. Wing hardcodé avant spread. |
| W4 | `execution/routers/llm_router.py:212` | `LLMExecutionRouter._run_pipeline()` step 10 | `store_interaction()` | write | `"aria"` (**DRIFT** — cf. note) | `intent.id` | **DRIFT BUG (dette #11)** : passe `metadata={"wing": "aria", "room": intent.id, ...}`. Le `**metadata` dans `store_interaction()` écrase le wing par défaut `"aria_episodic"` → toutes les interactions LLM atterrissent dans wing `"aria"`. Confirmed par count_memory_by_wing : 70 entrées dans `"aria"`, `"aria_episodic"` stagne. |
| W5 | `cognition/cognitive_classifier.py:281` | `_store_cache()` | `store_interaction()` | write | `"aria_classifier"` (intentionnel) | `"classifier_cache"` | Même mécanisme **-unpacking que W4. Ici intentionnel : le classifier veut écrire dans son propre wing. Révèle que `store_interaction` est utilisée comme writer générique, pas seulement épisodique. |
| W6 | `execution/routers/ingestion_router.py:49` | `IngestionExecutionRouter.execute()` | `store_interaction()` | write | `"aria_episodic"` (pas d'override wing dans metadata) | `"knowledge_ingest"` | Router **désactivé** depuis sprint 3.0 (non branché dans `_ROUTING_TABLE`). Code mort archivé pour future commande `/ingest`. |
| W7 | `media/image_service.py:10` | `ImageService.store_generated()` | `store_interaction()` | write | `"aria_episodic"` (pas d'override wing explicite, mais `**img.metadata` pourrait en introduire un) | `img.intent_id or "image_generation"` | Classe **non utilisée en prod** (uniquement dans `tests/images/test_image_generation.py` et `test_image_input.py`). Doublon fonctionnel avec W2 (`store_image_artifact` via image_router.py). |
| W8 | `media/image_service.py:21` | `ImageService.store_input()` | `store_interaction()` | write | `"aria_episodic"` (même réserve que W7) | `"image_input"` | Même statut que W7 — tests seulement, pas utilisé dans le pipeline prod. |
| I1 | `scripts/count_memory_by_wing.py` | `main()` | `chromadb.PersistentClient()` + `col.count()` + `col.get()` | inspect | toutes | toutes | **Accès direct ChromaDB** sans passer par mempalace. Script diagnostique, pas dans le pipeline prod. |

---

## 2. Inventaire des APIs publiques MemPalace

### Note préliminaire sur l'absence de `__all__`

`mempalace/__init__.py` n'exporte que `__version__`. Aucune API n'est formellement déclarée publique via `__all__`. La distinction public/interne ci-dessous est déduite de la documentation README, des docstrings, et des conventions de nommage (préfixe `_` = privé).

---

### 2.1 API publique (documentée, utilisable par un client)

#### `mempalace.searcher`

| Signature | Catégorie | Description |
|---|---|---|
| `search_memories(query, palace_path, wing=None, room=None, n_results=5, max_distance=0.0) → dict` | **searcher** | Recherche hybride (vecteur + BM25 + closet boost). Retourne `{"query", "filters", "total_before_filter", "results": [...]}`. Chaque result : `text, wing, room, source_file, similarity, distance, effective_distance, closet_boost, matched_via`. C'est l'API programmatique principale. |
| `build_where_filter(wing=None, room=None) → dict` | **searcher** | Construit le filtre ChromaDB `$and` pour wing/room. Utilitaire partagé avec searcher et layers. |
| `search(query, palace_path, wing=None, room=None, n_results=5) → None` | **searcher (CLI)** | Version avec print to stdout. Non utilisable programmatiquement (retourne None). |

#### `mempalace.palace`

| Signature | Catégorie | Description |
|---|---|---|
| `get_collection(palace_path, collection_name="mempalace_drawers", create=True) → collection` | **lifecycle** | Retourne la collection ChromaDB. Point d'accès bas niveau — expose directement l'objet collection ChromaDB. Formellement public (aucun underscore, documenté), mais constitue un accès de bas niveau. |
| `get_closets_collection(palace_path, create=True) → collection` | **lifecycle** | Alias `get_collection("mempalace_closets")`. |

#### `mempalace.layers`

| Signature | Catégorie | Description |
|---|---|---|
| `MemoryStack(palace_path=None, identity_path=None)` | **stack** | Stack 4 couches unifiée. Interface principale haut niveau. |
| `MemoryStack.wake_up(wing=None) → str` | **stack** | Génère le texte d'amorçage L0+L1 (~600-900 tokens). Injecte dans system prompt. |
| `MemoryStack.recall(wing=None, room=None, n_results=10) → str` | **stack (L2)** | Rappel on-demand filtré par wing/room. Retourne texte formaté. |
| `MemoryStack.search(query, wing=None, room=None, n_results=5) → str` | **stack (L3)** | Recherche sémantique profonde. Retourne texte formaté. |
| `MemoryStack.status() → dict` | **stack** | État des couches + comptage total drawers. |
| `Layer0(identity_path=None)` | **stack** | Couche identité (~100 tokens). Lit `~/.mempalace/identity.txt`. |
| `Layer0.render() → str` | **stack** | Retourne le texte d'identité. |
| `Layer1(palace_path=None, wing=None)` | **stack** | Couche histoire essentielle (~500-800 tokens). Auto-générée depuis palace. |
| `Layer1.generate() → str` | **stack** | Génère le texte L1 depuis ChromaDB. |
| `Layer2(palace_path=None)` | **stack** | Couche on-demand (~200-500 tokens). Filtré wing/room. |
| `Layer2.retrieve(wing=None, room=None, n_results=10) → str` | **stack** | Récupère les drawers filtrés. |
| `Layer3(palace_path=None)` | **stack** | Couche deep search (illimité). |
| `Layer3.search(query, wing=None, room=None, n_results=5) → str` | **stack** | Recherche sémantique, retourne texte formaté. |
| `Layer3.search_raw(query, wing=None, room=None, n_results=5) → list` | **stack** | Même recherche, retourne liste de dicts bruts. |

---

### 2.2 API "interne mais accessible" (importable, non underscore, non documentée comme publique)

| Module | Éléments | Note |
|---|---|---|
| `mempalace.palace` | `build_closet_lines()`, `upsert_closet_lines()`, `purge_file_closets()`, `file_already_mined()`, `mine_lock()` | Utilitaires internes au miner. Pas destinés aux clients. |
| `mempalace.backends.chroma` | `ChromaBackend`, `ChromaCollection` | Couche d'adaptation ChromaDB. Pas exposée dans README. |
| `mempalace.config` | `MempalaceConfig` | Lit `~/.mempalace/config.json`. Utile pour obtenir le `palace_path` par défaut. |

### 2.3 Modules privés / détails d'implémentation

`miner.py`, `convo_miner.py`, `normalize.py`, `dialect.py`, `knowledge_graph.py`, `palace_graph.py`, `mcp_server.py`, `onboarding.py`, `entity_registry.py`, `entity_detector.py`, `general_extractor.py`, `room_detector_local.py`, `spellcheck.py`, `split_mega_files.py`, `dedup.py`, `repair.py`, `exporter.py`, `fact_checker.py`, `migrate.py`.

Ces modules font partie de la chaîne d'ingestion CLI et du serveur MCP. Non destinés à être importés directement par un client.

---

## 3. Écarts entre usage actuel et API publique

| Point | Statut | API cible (si applicable) |
|---|---|---|
| R1 `mempalace_store.py` — wraps `search_memories` | **OK** | C'est l'API publique correcte. Seul problème : le défaut `wing="aria"` hérité d'un usage pré-ARIA. |
| R2–R4 `MempalaceBridge.*` — lit via `self._store()` | **OK** | Passe bien par `search_memories`. Wings correctement spécifiés dans la bridge. |
| R5 `cognitive_classifier._search_cache()` — importe `mempalace_store.search` directement | **BYPASS** | Devrait lire via `MempalaceBridge.retrieve_memories(wing="aria_classifier")` ou une méthode dédiée. Viole la règle de la bridge comme point d'accès unique en lecture. |
| R6–R9 — lecture via `mempalace_bridge` | **OK** | Conformes à l'architecture. |
| W1 `store_interaction()` — appelle `mempalace.palace.get_collection()` | **BYPASS** | Pas d'API publique d'écriture dans MemPalace. `get_collection()` est le seul point d'entrée bas niveau disponible. **GAP** : MemPalace n'expose pas de méthode `write_memory()` programmatique. |
| W2 `store_image_artifact()` — idem | **BYPASS + OK** | Même bypass que W1, mais wing correctement hardcodé. |
| W3 `store_semantic_fact()` — idem | **BYPASS + OK** | Même bypass. Wing correct. |
| W4 `llm_router.py` step 10 — `store_interaction(metadata={"wing": "aria", ...})` | **DRIFT** | Bug : wing="aria" écrase "aria_episodic". Correction : supprimer les clés `wing` et `room` du dict `metadata` passé à `store_interaction()` — ces champs appartiennent au schéma interne du writer, pas au caller. |
| W5 `cognitive_classifier._store_cache()` — `store_interaction(metadata={"wing": "aria_classifier", ...})` | **DRIFT (intentionnel)** | Le comportement est correct pour le cache classifier, mais révèle que `store_interaction` est utilisée comme writer générique multi-wing — rôle non prévu dans son interface. **GAP** : il manque un `store_classifier_cache()` séparé, ou une API d'écriture générique `store(text, wing, room, type, metadata)`. |
| W6 `ingestion_router.py` — `store_interaction()` | **OK (code mort)** | Router désactivé. Aucune action requise. |
| W7–W8 `media/image_service.py` | **GAP** | Classe non utilisée en prod. Doublon avec `store_image_artifact()`. Pas de migration nécessaire, mais à supprimer ou documenter explicitement comme dead code. |
| I1 `scripts/count_memory_by_wing.py` — accès direct ChromaDB | **BYPASS (acceptable)** | Script diagnostique, hors pipeline. Accès direct intentionnel pour l'inspection. |

### Résumé des catégories

| Catégorie | Points | Commentaire |
|---|---|---|
| **OK** | R2, R3, R4, R6, R7, R8, R9, W2 (wing), W3, W6 (code mort) | Conformes à l'architecture ou neutres |
| **DRIFT** | W4 (BUG actif), W5 (intentionnel), R1 (défaut wing) | W4 est la dette #11 — cause principale du stagnation aria_episodic |
| **BYPASS** | R5, W1, W2, W3, I1 | Tous les writes contournent searcher (GAP MemPalace : pas d'API write publique) |
| **GAP** | W1/W2/W3 (écriture), W5 (store dédié classifier), W7/W8 (dead code) | MemPalace n'offre pas d'API write programmatique |

---

## 4. Invariants à préserver pendant la migration

### Données existantes

- **143 entrées wing=`aria_episodic`** — interactions et images historiques correctement routées. À conserver intactes.
- **162 entrées wing=`aria_classifier`** — cache du classificateur cognitif. Actif en prod (lookup similarity>0.92). À conserver.
- **70 entrées wing=`aria`** — interactions LLM réelles mal routées depuis le début (bug W4 actif). Contiennent des souvenirs légitimes de Nico. Décision de migration à prendre (§5).
- **32 entrées closets wing=`aria`** — index secondaire des closets. Correspondent aux 70 drawers `aria`. Liés à la décision de migration des 70 entrées.

### Comportements observés à protéger

- **Fix F1 sprint 3.1** : scoring cosine pur dans `IntentRecallEngine`. Aucune migration mémoire ne doit réintroduire un boost mem_score.
- **Cache classifier** (R5/W5) : la wing `aria_classifier` doit rester lisible avec similarity>0.92. Si le wing change, le cache devient silencieusement inutilisable.
- **Recall par intent** (R3) : `retrieve_by_intent(intent_id)` filtre sur `room=intent_id, wing="aria_episodic"`. Si les interactions existantes (70 wing=`aria`) sont migrées vers `aria_episodic`, elles deviendraient accessibles — comportement souhaitable ou à évaluer.

### Tests à maintenir verts

- `tests/mempalace/test_mempalace_bridge.py` — contrat de la bridge (retrieve_memories, retrieve_by_intent, retrieve_semantic)
- `tests/mempalace/test_mempalace_writer.py` — contrat des writers
- `tests/mempalace/test_mempalace_bridge_intent.py` — retrieve_by_intent avec intent_id
- `tests/memory/test_memory_layers.py` — couches mémoire
- `tests/memory/test_idempotent_writer.py` — idempotence doc_id
- `tests/execution/test_llm_execution_router.py` — pipeline step 10
- `tests/execution/test_pipeline_memory_isolation.py` — isolation mémoire entre pipelines
- `tests/cognition/test_intent_recall.py` — recall intents via bridge

---

## 5. Questions ouvertes pour l'architecte

**Q1 — Les 70 entrées wing=`aria` : migrer ou laisser ?**

Ces 70 interactions sont des souvenirs réels de Nico, écrits dans le mauvais wing depuis le début. Options :
- a) Migrer vers `aria_episodic` (script de migration) → elles deviennent visibles au retrieval
- b) Laisser en place et corriger seulement les nouvelles écritures → perte progressive de contexte historique
- c) Supprimer (ne correspondent à aucun intent actif)

Le script `scripts/migrate_wing_aria_to_episodic.py` existe déjà dans le repo — signe que la migration (option a) était déjà envisagée.

**Q2 — `store_interaction()` comme writer générique multi-wing : acceptable ou à remplacer ?**

Actuellement, `store_interaction()` sert à la fois pour les interactions épisodiques (wing=`aria_episodic`) et le cache classifier (wing=`aria_classifier`). Le mécanisme `**(metadata or {})` permet ce double usage mais rend le schéma implicite et fragile (bug W4 en est la preuve).

Option A : créer `store_classifier_cache()` séparé dans `mempalace_writer.py`.
Option B : créer une fonction `store(text, wing, room, type, ...)` générique qui force les paramètres fondamentaux en position nommée (pas overridable par spread).

**Q3 — `media/image_service.py` : supprimer ou conserver ?**

`ImageService` n'est pas utilisée dans le pipeline prod. Elle est référencée dans 2 fichiers de tests (`test_image_generation.py`, `test_image_input.py`). Si ces tests testent le pipeline prod, il y a un problème. Si ces tests testent `ImageService` directement, ils testent du code mort.

**Q4 — Défaut `wing="aria"` dans `mempalace_store.py` : artefact ou intention ?**

`memory/mempalace_store.py:9` : `wing: str = "aria"`. Ce défaut est hérité d'un usage antérieur à la taxonomie wings ARIA (aria_episodic, aria_semantic, aria_classifier). En production, ce défaut n'est jamais utilisé car tous les appelants passent un wing explicite. À corriger (`wing: str = "aria_episodic"`) ou supprimer le défaut (rendre le paramètre obligatoire).

**Q5 — `MemoryStack` de `mempalace.layers` : pertinent pour sprint 4 ?**

`MemoryStack` offre une API unifiée 4 couches (L0 identité + L1 histoire + L2 on-demand + L3 search). ARIA n'utilise aucune de ces classes. Le sprint 4 vise à migrer vers l'API publique MemPalace. `MemoryStack` est-elle la bonne API cible pour le retrieval, ou `search_memories()` seul suffit pour le cas ARIA (single-user, pas d'identité statique) ?

**Q6 — `cognitive_classifier.py` bypass du bridge : violation de règle ou exception acceptable ?**

Le commentaire du bridge dit "Aucun agent, aucun router n'importe mempalace_store directement". `cognitive_classifier.py` n'est ni un agent ni un router — c'est un composant cognitif. La règle s'applique-t-elle ? Si oui, faire passer le classifier par la bridge. Si non, documenter l'exception.

**Q7 — Élément surprenant : `scripts/migrate_wing_aria_to_episodic.py`**

Ce script existe et son nom suggère que la migration wing=`aria` → `aria_episodic` était déjà planifiée avant cet audit. Il n'a pas été lu dans ce tour (hors périmètre initial). À lire en kickoff pour voir si la migration est déjà codée.
