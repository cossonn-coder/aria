# ARIA — Reprise de session
**Mis à jour : 30 Avril 2026 — 12h45**
**État : sprint 1.3 livré, bugs en cascade découverts pendant test live**

---

## Contexte rapide

ARIA = kernel cognitif personnel local pour Nico. Single-user.
Bot Telegram + service systemd sur Debian (vDebianIA).
Voir doc projet complet pour l'archi détaillée.

Compte Claude Code : `dodgemyspoon@gmail.com` (Pro), session active dans
`~/Nextcloud/projects/aria` sur la Debian.

---

## Ce qui a été fait dans la session du 30/04 (matin + midi)

✅ **Sprint 0.2** — wiring kernel : `llm_execution_router` injecté dans `ImageExecutionRouter`
✅ **Logging structuré** — module `logger.py`, `PYTHONUNBUFFERED=1` dans aria.service
✅ **Bug NameError** dans cognitive trace de `execution/routers/llm_router.py` corrigé
✅ **Anthropic en dernier fallback** — config + ROUTING_TABLE (CHAT/PLANNING/REASONING/REFLECTION) avec `claude-haiku-4-5`. Clé dans `.env` sous `ANTHROPIC_API_KEY`
✅ **Claude Code installé** sur Debian, `CLAUDE.md` à la racine du repo
✅ **`.gitignore`** propre (`.claude/`, `.env`, `chroma_db/`, etc.)
✅ **Sprint 1.3 — Context builder token budget** : `cognition/context_builder.py` + 10 tests, intégré dans `LLMExecutionRouter` étape 4b, `AnalystAgent` refacto avec `{context_block}` unique
✅ **Migration MemPalace** wing=`aria` (719 entrées) → wing=`aria_episodic`
✅ **Cleanup 74 résidus de tests** (`test_intent` / "hello world")
✅ **Cleanup 15 intents poubelles** (65 → 50 dans `~/.aria/intents.json`)
✅ **Validation `aria_semantic`** opérationnel pour écriture/lecture

**Tests : 169/169 verts**

---

## 🔴 Bugs en cascade découverts pendant test live (12h30)

Logs temporaires actifs (à supprimer après fixes) :
- `execution/routers/llm_router.py` — log du `CTX_BLOCK` après build
- `agents/analyst_agent.py` — log du `PROMPT FINAL` avant LLM

### Bug A — Retrieval mémoire décorrélé de la query (BLOQUANT)

`retrieve_memories()` fait une recherche vectorielle **toutes rooms confondues** dans `aria_episodic`. Les rooms les plus peuplées (`general` 254, `agents` 144, `sujets abordés` 104) dominent par volume, pas par pertinence sémantique.

**Symptôme** : query "Pourquoi elle ne germent pas" (intent: carottes dans jardin) retourne :
- 3× "budget fondations" (identiques)
- 3× "vols et hôtel"
- "Génère un chat"
- **Zéro souvenir sur les carottes ou la germination**

L'intent `carottes dans jardin` n'a qu'1 entrée en mémoire — et c'est la réponse négative "Rien en mémoire sur les carottes". L'intent `liste de courses` aussi : 1 entrée, négative. La vraie liste Carottes/Beurre/Lait/Pain est dans `room=knowledge_ingest`, pas dans `room=<intent_id liste de courses>`.

### Bug B — `retrieve_by_intent` ne filtre pas par distance

Retourne `carottes dans jardin` avec `dist=0.92` (seuil pertinence ~0.8). Le filtre est appliqué dans `retrieve_memories` mais pas dans `retrieve_by_intent`.

### Bug C — Doublons massifs dans MemPalace

`budget fondations` × 3, `vols et hôtel` × 2, distances identiques → mêmes échanges stockés N fois (probable bug writer ou rechargement de tests qui ont écrit en prod).

### Bug D — LLM perroquette sa réponse négative

Quand le retrieval retourne "Désolé, rien en mémoire" comme premier souvenir, le LLM le reprend tel quel. Effet de boucle d'auto-confirmation.

### Bug E — Création d'intents en doublon (seuil attach trop bas ?)

Nouvel intent "Pourquoi elle ne germent pas" créé alors que "problème de germination" existe déjà.

### Bug F — Salience repart à 1.0 au rechargement

Pas persistée dans `intents.json`. Pas critique mais à noter.

---

## 🎯 Décision en attente

**Deux fixes indépendants identifiés. Ordre à valider :**

**Option A — Fix retrieval contextuel** (recommandé en premier)
Dans `LLMExecutionRouter._run_pipeline()`, `global_memories` devrait être filtré par l'intent résolu (`retrieve_by_intent` prioritaire sur `retrieve_memories` global, ou pondération hybride). C'est le fix avec le plus d'impact immédiat.

**Option B — Fix doublons MemPalace**
Script de dédoublonnage. Polluent les résultats, gaspillent le budget context. Moins urgent mais sera utile.

**Option C** — Bug D (filtrage négatifs + tri par distance + renforcement règles prompt) reste pertinent mais inutile tant que A n'est pas fait.

---

## Fichiers à uploader pour reprendre

**Toujours utiles :**
- `config.py`
- `core/event.py`
- `cognition/cognitive_context.py`
- `execution/operation.py`
- `soul.md`
- Ce document

**Pour bug A (retrieval) :**
- `execution/routers/llm_router.py`
- `memory/mempalace_bridge.py`
- `cognition/context_builder.py`
- `agents/analyst_agent.py`

**Pour bug B (doublons) :**
- `memory/mempalace_writer.py`
- `memory/mempalace_store.py`

**Pour bug E (intents en doublon) :**
- `intent/intent_engine.py`
- `intent/intent_recall_engine.py`
- `intent/intent_decision.py`

---

## État git

Branche : `feat/sprint2-image-pipeline`
Pushée jusqu'au commit `c2983e2` (sprint 1.3 intégration).

Commits locaux non pushés à vérifier :
- Scripts de diagnostic et migration mémoire
- Cleanup intents
- Logs temporaires (à supprimer avant commit final)

---

## Ressources clés

- `.env` : `/home/nico/Nextcloud/projects/aria/.env` (Debian)
- MemPalace : `/home/nico/.mempalace/palace`
- Intents : `~/.aria/intents.json`
- Backup intents : `~/.aria/intents.json.backup.20260430-124110`
- Service : `sudo systemctl restart aria.service`
- Logs : `sudo journalctl -u aria -f -o cat`

Anthropic API : pay-as-you-go, Haiku-4.5, ~0.0007$ par appel.
Plan Pro = Claude Code + claude.ai (séparé de l'API).

---

## Premier message à envoyer dans la nouvelle session Claude

> Reprise sur ARIA, sprint 2 bugs en cascade découverts en test live.
> Voici le context.md complet [PIÈCE JOINTE].
> 
> J'ai validé l'option A : on fix d'abord le retrieval mémoire contextuel.
> Les logs CTX_BLOCK + PROMPT FINAL sont toujours actifs, on les retire 
> en dernier.
> 
> Avant de proposer un plan, lis le diagnostic complet du bug A dans 
> context.md et demande-moi les fichiers dont tu as besoin.

---

## Dettes identifiées sprint 2

1. **mem_score normalisation biaisée par doublons** ✓ RÉSOLU (cleanup MemPalace)
   ~~Confirmé en prod : query "vols pour Paris" boost +1.0 pour `construire une
   maison` (7 hits parasites) vs +0.286 pour `réservation voyage`.~~
   Cleanup effectué : aria_episodic 724 → 118, suppression rooms test,
   wing `aria` orphelin (66) et `general`/`agents` (399 archives obsolètes).
   Idempotence ajoutée dans `store_interaction` (fenêtre 60s sha256).
   Le boost mem_score peut désormais opérer sur des données propres.

2. **Cosine recalculé O(N) à chaque CREATE** (`intent/intent_engine.py:_find_by_name_semantic`)
   Négligeable à 50 intents, à indexer si croissance.

3. **Deux mécanismes de matching d'intent en parallèle**
   (`intent_recall_engine.resolve` + `intent_engine._find_by_name_semantic`)
   À unifier sprint 3.

4. **Marge fragile sur scoring nu** (`tests/intent/test_intent_dedup.py:test_regression_bug_e_real_embeddings`)
   Score 0.4889 vs seuil 0.45 — robuste seulement avec mem_score actif et propre.

5. **Suivi des opérations sur la donnée** (dette de processus)
   Pendant le sprint 2 cleanup, les comptages ont mélangé `col.count()` (toutes wings)
   et `col.get(where=wing=...)` (wing isolée). 23 entrées n'ont pas pu être tracées
   dans la chronologie des suppressions. Pour les futurs scripts touchant la donnée
   prod : logger chaque ID supprimé dans un fichier audit, et toujours mesurer
   before/after par wing+room avec filtre explicite.

---

### Backlog reporté sprint 3+

- **Métacognition** : Aria doit pouvoir lire son propre code source. Reconstruire
  proprement via une wing dédiée (`aria_self`) avec ingestion contrôlée du repo,
  plutôt que via collage manuel sur Telegram.
- **Idempotence sur store_image_artifact et store_semantic_fact** : ces fonctions
  utilisent encore uuid4. À aligner si elles deviennent exposées aux retries.
- **Unification des deux mécanismes de matching d'intent** (`recall_engine` +
  `_find_by_name_semantic`) en une seule autorité.
- **Précalcul des normes d'embedding** dans `Intent.embedding` pour O(1) au lieu de O(N).