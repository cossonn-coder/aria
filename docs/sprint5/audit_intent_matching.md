# Audit intent matching — dette #18

**Sprint 5 / T4-A — audit lecture seule, aucun fix.**

Bugs visés (run live, dont 4 ce matin post-T3) :

| Message utilisateur | Intent matché (faux) |
|---------------------|----------------------|
| "Les carottes en ragoût recette" | `carottes dans jardin` (jardin) |
| "Planifier des vacances en Normandie" | `Pourquoi elle ne germent pas` |
| "recette carotte citron pour 6 personnes ingrédients riches en fer" | `Pourquoi elle ne germent pas` |
| "Tu vas bien ?" (sprint 4) | `semis en intérieur` |

Hypothèse de départ : double mécanisme de matching (dette #3). Cet
audit valide/infirme et trace TOUTE la chaîne.

---

## 1. CARTOGRAPHIE COMPLÈTE

Fonctions/méthodes participant au matching d'intent dans `aria/`.

| # | Fichier:ligne | Signature | Rôle | Métrique | Seuil | Appelé par |
|---|---------------|-----------|------|----------|-------|------------|
| F1 | `intent/intent_recall_engine.py:49` | `IntentRecallEngine.resolve(message, intents, memory_context=None) -> (RecallDecision, scored)` | **Mécanisme principal.** Score chaque intent actif vs message, décide `attach`/`split`/`create`. | cosine(`embed(message)`, `intent.embedding`) | `0.45` (`self.threshold`, hard-coded au constructeur) | `IntentEngine.resolve` (F2) |
| F2 | `intent/intent_engine.py:71` | `IntentEngine.resolve(message, intents, memory_context=None)` | Délégation pure vers F1. | — | — | `LLMExecutionRouter._run_pipeline` étape 2 |
| F3 | `intent/intent_engine.py:81` | `IntentEngine._find_by_name(name)` | **Dedup CREATE.** Match strict insensitive sur `intent.name.lower() == name.lower()`. | string equality lower-case | exact | `IntentEngine.apply` (F5) si CREATE |
| F4 | `intent/intent_engine.py:94` | `IntentEngine._find_by_name_semantic(name, threshold=0.55) -> Optional[Intent]` | **Dedup CREATE sémantique.** Score nom canonique extrait vs intents actifs. Override CREATE → ATTACH si match. | cosine(`embed(name)`, `intent.embedding`) | `0.55` (param défaut) | `IntentEngine.apply` (F5) si CREATE et F3 a échoué |
| F5 | `intent/intent_engine.py:125` | `IntentEngine.apply(decision, message, intent_name=None) -> Intent` | Applique la décision F1 (`attach`/`create`/`split`) avec dedup F3+F4 sur CREATE. | dépend du chemin | — | `LLMExecutionRouter._run_pipeline` étape 3 |
| F6 | `llm/intent_namer.py:18` | `extract_intent_name(message, llm_router) -> str` | LLM extrait un nom canonique 2-5 mots. Appelé uniquement si `decision.action == "create"`. | LLM CHAT, prompt few-shot | — | `LLMExecutionRouter._run_pipeline` étape 3 |
| F7 | `intent/intent_compression_engine.py:29` | `IntentCompressionEngine.compress(intents)` | Fusion d'intents très proches sémantiquement (cluster cosine). | cosine | `0.78` | `IntentEngine.compression_cycle_if_needed` (toutes les 20 mutations) |
| F8 | `intent/intent_recall_engine.py:131` | `IntentRecallEngine._cosine(a, b)` | Helper cosine bas niveau. | cosine | — | F1 |
| F9 | `embedding/embedder.py:Embedder.encode` | `Embedder.encode(texts) -> np.ndarray` | Modèle `all-MiniLM-L6-v2` (`config.EMBEDDING_MODEL`), `normalize_embeddings=True`. | — | — | F1, F4, F7, intent_store load, intent creation |

### Relations (qui appelle qui)

```
LLMExecutionRouter._run_pipeline (execution/routers/llm_router.py:98)
├── étape 2 : IntentEngine.resolve (F2)
│              └── IntentRecallEngine.resolve (F1)
│                    └── _cosine (F8)
└── étape 3 : extract_intent_name (F6) si decision == CREATE
              └── IntentEngine.apply (F5)
                    ├── F3 _find_by_name (exact)
                    ├── F4 _find_by_name_semantic (cosine, threshold 0.55)
                    └── _create (génère intent.embedding via Embedder.encode du name)
```

`IntentEngine.compression_cycle_if_needed` (F7) tourne en arrière-plan
toutes les 20 mutations (`apply` ou `save`), seuil 0.78.

---

## 2. CODE INTÉGRAL DES FONCTIONS DE MATCHING

### F1 — `IntentRecallEngine.resolve` (intent_recall_engine.py:41-125)

```python
def __init__(self, embedder, threshold: float = 0.45):
    self.embedder = embedder
    self.threshold = threshold

def resolve(
    self,
    message: str,
    intents: List,
    memory_context: Optional[dict] = None,  # conservé pour compat call-site, ignoré
                                            # depuis F1 (sprint 3.1).
) -> Tuple[RecallDecision, List[Tuple]]:
    """
    Scoring purement sémantique (cosine). Pas de signal mémoire.
    """

    # 1. EMBEDDING MESSAGE
    msg_emb = self.embedder.encode([message])[0]

    # 2. FILTER ACTIVE INTENTS
    active_intents = [i for i in intents if i.status == "active"]
    if not active_intents:
        return RecallDecision(action="create"), []

    # 3. SCORING
    scored: List[Tuple] = []
    for intent in active_intents:
        if not hasattr(intent, "embedding") or intent.embedding is None:
            continue
        cosine = self._cosine(msg_emb, intent.embedding)
        final_score = cosine
        scored.append((intent, final_score))

    if not scored:
        return RecallDecision(action="create"), []

    # 4. BEST MATCH
    scored.sort(key=lambda x: x[1], reverse=True)
    best_intent, best_score = scored[0]

    # 5. DECISION LOGIC (STABLE TRIANGLE)

    # CASE 1 — strong match → attach
    if best_score >= self.threshold:
        return RecallDecision(
            action="attach",
            primary_intent_id=best_intent.id,
            score=best_score,
        ), scored

    # CASE 2 — ambiguity → split
    close = [s for s in scored if s[1] > self.threshold - 0.05]
    if len(close) >= 2:
        return RecallDecision(action="split", score=best_score), scored

    # CASE 3 — weak signal → create
    return RecallDecision(action="create", score=best_score), scored
```

Notes du code (commentaires existants) : F1 sprint 3.1 a retiré le
boost `mem_score` (+0.2 × hits_normalized). Aujourd'hui le score
final est strictement la cosine vs `intent.embedding`. La variable
`memory_context` est conservée pour compatibilité de signature mais
ignorée — à retirer si confirmé qu'on ne réintroduira jamais le
boost.

### F4 — `IntentEngine._find_by_name_semantic` (intent_engine.py:94-119)

```python
def _find_by_name_semantic(self, name: str, threshold: float = 0.55) -> Optional[Intent]:
    """
    Autorité finale pour les décisions CREATE : si un intent existant est
    sémantiquement proche du nom canonique extrait, on attache plutôt que
    de créer un doublon — même si le recall message-based n'a pas franchi
    le seuil (signal différent, moins stable pour les noms courts).
    """
    if not name:
        return None
    name_emb = np.array(self.embedder.encode([name])[0], dtype=np.float32)
    best_intent = None
    best_score = threshold
    for intent in self.intents.values():
        if intent.status != "active":
            continue
        if not hasattr(intent, "embedding") or intent.embedding is None:
            continue
        b = np.array(intent.embedding, dtype=np.float32)
        denom = np.linalg.norm(name_emb) * np.linalg.norm(b)
        if denom == 0:
            continue
        score = float(np.dot(name_emb, b) / denom)
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent
```

Cosine entre le **nom canonique extrait par LLM** (F6) et `intent.embedding`
(qui est l'embedding du **nom de l'intent existant**). Seuil 0.55 par défaut.

### F5 — `IntentEngine.apply` (intent_engine.py:125-192)

```python
def apply(self, decision, message: str, intent_name: str | None = None) -> Intent:
    name = intent_name or message[:60]

    if decision.action == IntentActionType.CREATE:
        # Déduplication par nom canonique — autorité finale pour CREATE.
        if intent_name:
            existing = self._find_by_name(intent_name)
            if existing:
                existing.add_action(message)
                self.compression_cycle_if_needed()
                return existing
            existing = self._find_by_name_semantic(intent_name)
            if existing:
                existing.add_action(message)
                self.compression_cycle_if_needed()
                return existing

        intent = self._create(name=name)
        intent.add_action(f"created_from_message:{message[:100]}")
        self.compression_cycle_if_needed()
        return intent

    if decision.action == IntentActionType.ATTACH:
        intent = self.get(decision.primary_intent_id)
        if intent is None:
            intent = self._create(name=name)
        intent.add_action(message)
        self.compression_cycle_if_needed()
        return intent

    if decision.action == IntentActionType.SPLIT:
        intent = self._create(name=name)
        intent.add_action(f"split_from_context:{message[:100]}")
        self.compression_cycle_if_needed()
        return intent

    raise ValueError(f"Unknown intent action: {decision.action}")
```

**Observation critique** : la dedup F3+F4 ne tourne que dans la branche
CREATE. Si F1 dit ATTACH (à un mauvais intent), F4 n'est jamais consulté.

### F8 — `_cosine` helper (intent_recall_engine.py:131-138)

```python
def _cosine(self, a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
```

Note : `Embedder.encode(..., normalize_embeddings=True)` produit déjà
des vecteurs unitaires, donc `denom == 1.0` en pratique et le cosine
revient à un dot product. Le code est néanmoins robuste à un embedder
non normalisé.

### F6 — `extract_intent_name` (llm/intent_namer.py)

```python
NAMER_PROMPT = """
Extrait le sujet principal de ce message en 2 à 5 mots maximum.
Réponds UNIQUEMENT avec le sujet, sans ponctuation, sans majuscule, sans explication.

Exemples :
- "j'ai déjà mis de la bière dans la liste ?" → liste de courses
- "je veux partir en normandie en train" → vacances normandie train
- "aide moi à apprendre docker" → apprentissage docker
- "écrit une liste de courses" → liste de courses

MESSAGE : {message}
"""

def extract_intent_name(message: str, llm_router: LLMRouter) -> str:
    try:
        response = llm_router.complete(
            prompt=NAMER_PROMPT.format(message=message),
            role=LLMRole.CHAT,
            temperature=0.1,
            max_tokens=20,
        )
        name = response.content.strip().lower()[:60]
        return name if name else message[:60]
    except Exception:
        return message[:60]
```

Tronqué à 60 chars — contrainte qui explique le `name` `'Je veux apprendre la validation fonctionnelle sur des capteu'` (truncation visible dans la persistance).

---

## 3. SCHÉMA DE FLUX (message Telegram → intent retenu)

```
[Telegram Bot]
    │ message texte
    ▼
[AriaKernel.handle()]
    ├── classify_operation(message, llm_router, bridge)
    │   → CognitiveOperation (ex FACT_RECALL, REASONING, ...)
    └── dispatch via _ROUTING_TABLE
            │
            ▼
   [LLMExecutionRouter.execute(payload)]
            │
            ▼
   [LLMExecutionRouter._run_pipeline()]
            │
   ───── ÉTAPE 1 : MÉMOIRE GLOBALE ─────────
   global_memories = bridge.retrieve_memories(message, n=top_k)
   memory_context  = MemoryContext(global, session={})
            │
   ───── ÉTAPE 2 : INTENT RECALL ───────────
   active_intents = intent_engine.list_attention_active()
   recall_decision, scored = intent_engine.resolve(
       message,
       active_intents,
       memory_context=global_memories,   # IGNORÉ par F1 depuis sprint 3.1
   )
            │
            │  IntentRecallEngine.resolve fait :
            │   1. msg_emb = embedder.encode([message])[0]
            │   2. filter intents.status == "active"
            │   3. for each intent : cosine(msg_emb, intent.embedding)
            │   4. sort desc, prendre best
            │   5. if best_score >= 0.45 → action="attach", primary_id=best.id
            │      elif >=2 above (0.45-0.05) → action="split"
            │      else → action="create"
            ▼
   ───── ÉTAPE 3 : MUTATION ────────────────
   if decision.action == "create":
       intent_name = extract_intent_name(message, llm_router)  # LLM CHAT
   else:
       intent_name = None

   intent = intent_engine.apply(decision, message, intent_name)
            │
            │  apply() :
            │   ATTACH → intent_engine.get(primary_id)
            │            (ou _create(name=message[:60]) si id introuvable)
            │   CREATE → si intent_name :
            │              _find_by_name(intent_name)         exact match
            │              _find_by_name_semantic(intent_name) cosine vs intents
            │              (seuil 0.55 sur nom canonique)
            │            sinon créer un nouveau via _create
            │   SPLIT  → toujours créer un nouveau
            │   intent.add_action(message)
            ▼
   ───── ÉTAPES 4 → 10 ─────────────────────
   session_memories = bridge.retrieve_by_intent(message, intent.id)
   ... (context_block, agents, persistence, decay, write_interaction)
```

**Décision finale d'intent** : c'est `intent.id` retourné par
`apply()`. Ce qui détermine cet id :

- Cas `attach` : `decision.primary_intent_id` = id du best F1, **pas
  de seconde validation**.
- Cas `create` + match `_find_by_name` : id de l'intent existant
  trouvé par exact match.
- Cas `create` + match `_find_by_name_semantic` : id de l'intent
  existant trouvé par cosine sur nom canonique (seuil 0.55).
- Cas `create` sans match : nouvel id généré par `_create`.
- Cas `split` : nouvel id (création systématique).

---

## 4. INVENTAIRE DES INTENTS ACTUELS

Source : `~/.aria/intents.json` (chemin fixé dans `intent_store.py:7`).

- **Total : 61 intents** — 60 active, 1 completed.
- **Champs persistés** : `id, name, description, status, next_action,
  actions_history`. **Embedding NON persisté** — recalculé à chaque
  boot via `embedder.encode([intent.name])[0]` (intent_store.py:40).
  Conséquence : un changement de modèle d'embedding invalide tous
  les vecteurs en RAM mais sans corruption disque.

### Intents les plus actifs (par actions_history)

| Actions | Nom | id[:8] |
|---------|-----|--------|
| 308 | sujets abordés | 75c6dea5 |
| 32  | voyage organisation | fad5d882 |
| 31  | construire une maison | b272e69e |
| 23  | **Pourquoi elle ne germent pas** | 82787f71 |
| 20  | liste de courses | d55f930e |
| 16  | fondations budget | 39c95ada |
| 16  | réservation voyage | e7180133 |
| 14  | gestion de la sécurité | d109348e |
| 11  | carottes dans jardin | 8828e7a1 |
| 11  | salutation | a1ed7be4 |
| 10  | semis en intérieur | 0e8b837b |

### Intents cités dans les bugs

| Nom | id[:8] | Status | Actions | Embedding |
|-----|--------|--------|---------|-----------|
| Pourquoi elle ne germent pas | 82787f71 | active | 23 | reconstruit au boot (F9) |
| carottes dans jardin | 8828e7a1 | active | 11 | idem |
| ensoleillement menthe | d5522f45 | active | 1 | idem |
| semis en intérieur | 0e8b837b | active | 10 | idem |
| Je veux apprendre la validation fonctionnelle sur des capteu | 117423da | active | 1 | idem (nom tronqué à 60 chars par `extract_intent_name`) |

---

## 5. DOUBLON OU PROXIMITÉ SÉMANTIQUE — RÉSULTAT INATTENDU

Calcul de la similarité cosinus entre les 60 noms d'intents actifs
(1770 paires), modèle `all-MiniLM-L6-v2` avec `normalize_embeddings=True`.

**Aucune paire au-dessus de 0.85.** **Aucune paire au-dessus de 0.70.**

### Top 10 paires (toutes valeurs)

| Score | Paire |
|-------|-------|
| 0.668 | `intents` ↔ `connaître intents` |
| 0.661 | `voyage organisation` ↔ `réservation voyage` |
| 0.649 | `jardin divisé` ↔ `jardin potager` |
| 0.635 | `recette rapide` ↔ `recette houmous` |
| 0.606 | `recettes santé culinaire` ↔ `recette rapide` |
| 0.596 | `jardin divisé` ↔ `secteur jardinage` |
| 0.589 | `jardinage plantes + jardinage légumes` ↔ `jardinage plantations` |
| 0.577 | `gestion de la sécurité` ↔ `gestion d erreur` |
| 0.576 | `jardin divisé` ↔ `carottes dans jardin` |
| 0.550 | `régime sportif` ↔ `régime escalade` |

**Implication clé** : sur cet embedding, des paires triviales comme
`voyage organisation` ↔ `réservation voyage` ne dépassent pas 0.67.
**L'espace de représentation est plat.** Le seuil 0.45 de F1 capture
donc de très loin tout intent vaguement français.

### Top score d'un intent "absorbant"

`Pourquoi elle ne germent pas` apparaît à plusieurs reprises dans le
top des paires "incohérentes" :
- 0.513 vs `gestion d erreur`
- 0.504 vs `gestion de la sécurité`
- 0.482 vs `visite du site`
- 0.477 vs `problème de germination`
- 0.456 vs `Je veux apprendre la validation fonctionnelle sur des capteu`

Le nom mélange un verbe générique (`Pourquoi`), un pronom (`elle`),
une négation (`pas`), et un mot-contenu (`germent`). Cocktail
attractif pour un modèle multilingue qui s'aligne sur le centroïde
français.

---

## 6. POINTS DE COMBINAISON DE SCORES

**Aujourd'hui : aucun.**

Avant le fix F1 (sprint 3.1, 1er mai 2026) :
```
final_score = cosine(msg, intent_emb) + 0.2 × hits_normalized
```
où `hits_normalized` venait de `memory_context`. Le boost favorisait
les rooms à fort volume mémoire — produisait des cascades de
mismatches (run live 1er mai : "choux rouges" → "construire une
maison"). Boost retiré commit `6d1c3c9`.

Aujourd'hui (intent_recall_engine.py:88) :
```python
cosine = self._cosine(msg_emb, intent.embedding)
final_score = cosine
```

Pas de pondération mémoire, pas de boost confidence, pas de penalty
sur la salience ou le decay. Pure cosine sur un embedding de nom
d'intent, point.

**Le bug n'est pas dans une formule cachée — il est dans la combinaison
seuil bas (0.45) + embedder peu discriminant (MiniLM-L6-v2) + noms
d'intents courts générant des vecteurs centraux.**

Note : `_find_by_name_semantic` (F4) utilise un seuil 0.55, plus
strict, mais sur un signal différent (nom canonique LLM, pas message
brut). Il n'est consulté que sur la branche CREATE, donc inactif quand
F1 a déjà décidé `attach`.

---

## 7. JEU DE CAS DE TEST DE RÉFÉRENCE

Cosine reproduite à la main avec le même embedder
(all-MiniLM-L6-v2, normalize_embeddings=True), dataset = 60 intents
actifs.

### Cas 1 — `Les carottes en ragoût recette`
- **Top intents par cosine vs message** :
  | Score | Intent |
  |-------|--------|
  | 0.642 | `carottes dans jardin` ← matché (≥ 0.45 → ATTACH) |
  | 0.545 | `recettes santé culinaire` |
  | 0.479 | `Pourquoi elle ne germent pas` |
  | 0.476 | `recette rapide` |
  | 0.472 | `semis en intérieur` |
- **Intent attendu sémantique** : `recettes santé culinaire` ou
  `recette rapide` (cuisine, pas jardin).
- **Diagnostic** : MiniLM s'accroche au mot lexical `carottes`, sans
  capter la nuance "ragoût/recette" (cuisine).

### Cas 2 — `Planifier des vacances en Normandie`
- **Top intents** :
  | Score | Intent |
  |-------|--------|
  | 0.466 | `Pourquoi elle ne germent pas` ← matché (≥ 0.45) |
  | 0.448 | `rotation des parcelles` |
  | 0.433 | `connaître intents` |
  | 0.417 | `secteur jardinage` |
  | 0.415 | `verger à réparer` |
- **Intent attendu** : `voyage organisation` (32 actions) ou
  `réservation voyage` (16 actions). **Aucun des deux n'apparaît dans
  le top 5.**
- **Diagnostic** : `voyage organisation` n'est pas en top 5 (score
  inférieur à 0.41 — pas mesuré). Le bruit MiniLM sur "Planifier" /
  "Normandie" / "vacances" ne s'aligne pas avec ces noms canoniques.
  Inversement, `Pourquoi elle ne germent pas` capte génériquement le
  français.

### Cas 3 — `recette carotte citron pour 6 personnes ingrédients riches en fer`
- **Top intents** :
  | Score | Intent |
  |-------|--------|
  | 0.540 | `recettes santé culinaire` |
  | 0.517 | `recette rapide` |
  | 0.482 | `carottes dans jardin` |
  | 0.440 | `gastronomie raffinement` |
  | 0.430 | `Pourquoi elle ne germent pas` |
  | 0.411 | `liste d ingrédients` |
- **Cohérent en top 1** ici (`recettes santé culinaire`) — ce cas
  reste correct par F1 stricto. Mais le log Nico indique un match
  vers `Pourquoi elle ne germent pas`. **Hypothèse** : le match est
  arrivé via un état antérieur des intents (avant/après une
  compression), ou via une variante du message. À confirmer avec le
  log live exact.

### Cas 4 — `Tu vas bien ?`
- **Top intents** :
  | Score | Intent |
  |-------|--------|
  | 0.496 | `semis en intérieur` ← matché (≥ 0.45) |
  | 0.485 | `gestion de la sécurité` |
  | 0.447 | `Pourquoi elle ne germent pas` |
  | 0.407 | `visite du site` |
  | 0.380 | `rotation des parcelles` |
- **Intent attendu** : `salutation` (id `a1ed7be4`, 11 actions).
  Score réel sur ce message non capté en top 5 (< 0.38).
- **Diagnostic** : message ultra-court (3 mots), MiniLM sort un
  vecteur "français générique", aligné sur n'importe quel intent qui
  a appris une part de centralité (`semis en intérieur` a 10 actions).

### Cas 5 — Conversation cuisine fragmentée (multi-tour, run live post-T3)

Conversation continue 11h11 → 11h19 autour d'une recette
carotte/citron/lentilles/épinards pour 6 personnes. Le matching
d'intent devrait idéalement s'attacher au même intent (la recette en
cours) sur les 4 tours. **Observation : 3 intents différents matchés,
dont un créé en cours de conversation.**

#### Tableau d'observation (intents matchés en run live)

| Tour | Heure | Message | intent_id | intent_name |
|------|-------|---------|-----------|-------------|
| 1 | 11:11 | "En fait c'est une recette carotte citron pour 6 personnes avec des ingrédients qui contiennent du fer qu'il me faut." | `82787f71` | Pourquoi elle ne germent pas |
| 2 | 11:16 | "Des lentilles et des épinards, le reste je peux acheter si besoin" | `82787f71` | Pourquoi elle ne germent pas |
| 3 | 11:17 | "Une recette carotte citron lentilles épinards pour 6 personnes" | `ad5423e7` | recettes santé culinaire |
| 4 | 11:19 | "Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à découper, un couteau de cuisine, un économe, un piano de cuisine 5 feux, des plats à gratin, des plats à quiche, les ingrédients de base de cuisine (huiles, vinaigres, épices, sel)" | `ed1bf159` (créé) | Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à |

#### Reproduction à la main (60 intents actifs, ed1bf159 exclu pour T1-T3 puisque créé à T4 — top 5 par tour)

**T1 (11:11)** :
| Score | Intent |
|-------|--------|
| 0.535 | `Pourquoi elle ne germent pas` ← matché (≥ 0.45 → ATTACH) |
| 0.493 | `recettes santé culinaire` |
| 0.455 | `recette rapide` |
| 0.452 | `Je veux apprendre la validation fonctionnelle sur des capteu` |
| 0.408 | `carottes dans jardin` |

**T2 (11:16)** :
| Score | Intent |
|-------|--------|
| 0.507 | `Pourquoi elle ne germent pas` ← matché (≥ 0.45 → ATTACH) |
| 0.493 | `Je veux apprendre la validation fonctionnelle sur des capteu` |
| 0.493 | `semis en intérieur` |
| 0.473 | `gestion de la sécurité` |
| 0.461 | `recettes santé culinaire` |

**T3 (11:17)** :
| Score | Intent |
|-------|--------|
| 0.575 | `recettes santé culinaire` ← matché (≥ 0.45 → ATTACH) |
| 0.546 | `carottes dans jardin` |
| 0.477 | `recette rapide` |
| 0.465 | `Je veux apprendre la validation fonctionnelle sur des capteu` |
| 0.431 | `Pourquoi elle ne germent pas` |

**T4 (11:19)** :
| Score | Intent |
|-------|--------|
| 0.441 | `recettes santé culinaire` |
| 0.412 | `liste de courses` |
| 0.406 | `secteur jardinage` |
| 0.392 | `semis en intérieur` |
| 0.387 | `Pourquoi elle ne germent pas` |

#### Diagnostic

- **T1 et T2** — ATTACH faux et persistant sur `Pourquoi elle ne
  germent pas`. Bug classique d'embedding plat (cf. §5 et cas 2-3) :
  un intent générique-français domine la cosine sur des messages
  cuisine sans rapport avec la germination.

- **T3** — ATTACH bascule vers `recettes santé culinaire` (top 1 à
  0.575). Sémantiquement plus juste, **mais incohérent avec les tours
  précédents** : l'intent fil rouge change en cours de conversation.
  Aucun signal de continuité (intent récent) n'est utilisé par
  `IntentRecallEngine.resolve` — un message N est traité
  indépendamment de N-1.

- **T4** — **SPLIT** déclenché (best=0.441 < seuil 0.45 ; 3 scores
  > 0.40 ⇒ branche `split` dans F1 ligne 113-119). Confirmé par
  l'`actions_history` de l'intent créé qui commence par
  `split_from_context:...` (intent_engine.py:193). Conséquences
  mécaniques précises :
  - F6 `extract_intent_name` n'est **pas** appelé (le pipeline ne le
    déclenche que pour `action == "create"`, llm_router.py:130-131).
  - `intent_name` reste `None`.
  - `IntentEngine.apply` branche SPLIT (intent_engine.py:191-195) fait
    `name = intent_name or message[:60]` — donc `name = message[:60]`,
    **truncation brute au caractère sur le message** : `Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à`.
  - F4 `_find_by_name_semantic` n'est **pas** consulté pour SPLIT
    (cf. F5, dedup réservée à la branche CREATE).
  - Un nouvel intent est créé avec ce nom illisible et 1 seule action.

  Le tour 4 est sémantiquement la suite directe de la conversation
  recette (inventaire de cuisine pour exécuter la recette des tours
  1-3), mais l'embedding du message long et liste-comma-séparée ne
  s'aligne avec aucun intent existant au-dessus du seuil ATTACH —
  d'où SPLIT.

#### Implications pour T-C (sprint 6)

1. **Aucun signal de continuité conversationnelle** dans le matching.
   Levier supplémentaire à considérer en T-C : "intent récent (N-1,
   N-2)" comme préférence légère pour stabiliser un fil rouge.

2. **Pathologie de naming en branche SPLIT** — distincte de la dette
   #22 (truncation `extract_intent_name`). En SPLIT, le nom d'intent
   est `message[:60]` direct, sans aucune passe LLM canonisante.
   Sur des messages longs ou structurés, cela produit des intents au
   nom illisible et impossible à dédupliquer par F3/F4 dans des runs
   futurs. Voir surprise §9 #13 (nouvelle dette #23).

3. **Zone 0.40-0.45 trop peuplée sur l'embedder actuel.** Dès qu'un
   message contextuel n'a pas de target net, plusieurs intents
   tombent dans cette bande étroite et déclenchent SPLIT. Conséquence
   indirecte : chaque message un peu inhabituel crée un nouvel intent
   au lieu d'attacher à un fil existant. Lever le seuil ATTACH ne
   suffira pas — il faut aussi reconsidérer la sortie SPLIT (rendre
   plus exigeant le `len(close) >= 2`, ou supprimer SPLIT et
   défaulter à CREATE pour ne pas multiplier les intents fantômes).

---

## 8. DETTE #3 — DEUX MÉCANISMES EN PARALLÈLE ?

**Réponse : oui, mais pas en concurrence.** Ils s'enchaînent.

### Mécanisme A — `IntentRecallEngine.resolve` (F1)

- Entrée : **message brut**.
- Score : cosine(message_emb, intent.embedding).
- Seuil : 0.45.
- Sortie : décision `attach` / `split` / `create`.
- **Toujours appelé** (étape 2 du pipeline).

### Mécanisme B — `IntentEngine._find_by_name_semantic` (F4)

- Entrée : **nom canonique LLM** (`extract_intent_name`).
- Score : cosine(name_emb, intent.embedding).
- Seuil : 0.55.
- Sortie : `Optional[Intent]` — si trouvé, override CREATE en ATTACH.
- **Appelé seulement si A a décidé `create` ET nom canonique non vide**
  (étape 3 du pipeline, dans `apply`).

### Ordre & arbitre

A décide en premier. Si A dit `attach` (best_score ≥ 0.45) → A
gagne, l'attache se fait sur l'intent identifié par A, **B n'est
jamais consulté**.

Si A dit `create` → B est consulté avec le nom canonique. Si B
trouve un intent existant → l'intent existant est réutilisé (dedup
de création). Sinon, un nouvel intent est créé.

Si A dit `split` → un nouvel intent est créé sans dedup (B ignoré
même si nom canonique existe).

### Conséquence pour les bugs observés

Tous les bugs listés en CONTEXTE ont franchi le seuil 0.45 de A.
**B n'a aucun rôle dans le bug**. La correction T-C devra cibler A
en priorité (raise threshold, change embedder, add re-rank, …).

B reste utile pour éviter les doublons d'intents qui auraient le
même nom canonique. Mais son seuil (0.55) sur le même embedder plat
soulève la même question.

---

## 9. SURPRISES / POINTS D'ATTENTION

1. **L'espace d'embedding est plat.** Aucune paire d'intents > 0.85
   sur 1770 comparaisons, top à 0.668. Le seuil F1 = 0.45 capture
   mécaniquement tout intent légèrement aligné avec le français
   moyen. **C'est la racine fonctionnelle de la dette #18.**

2. **`all-MiniLM-L6-v2` est un modèle généraliste anglais-fort**
   (multilingue OK mais sub-optimal en FR). Pour des noms d'intents
   FR courts (1-3 mots), il produit des vecteurs proches du
   centroïde de la langue. Candidats T-C : `paraphrase-multilingual-mpnet-base-v2`,
   `intfloat/multilingual-e5-base`, `BAAI/bge-m3`. Plus lourds mais
   beaucoup plus discriminants en FR.

3. **L'embedding d'un intent est calculé sur `intent.name` seul**
   (intent_engine.py:63 et intent_store.py:40). Pas de description,
   pas d'extraits d'actions_history. Pour un intent à 308 actions
   (`sujets abordés`), c'est dommage : il y a beaucoup de signal
   ignoré.

4. **`IntentCompressionEngine` est inactif en pratique.** Seuil
   0.78 sur un espace dont le max observé est 0.668. Aucune
   compression ne s'est jamais déclenchée. La dette `actions_history`
   non bornée s'accumule (308 actions sur `sujets abordés`).

5. **Doublon de classe `RecallDecision` vs `IntentRecallDecision`.**
   - `intent_recall_engine.py:12-24` définit `RecallDecision`
     (`action: str`).
   - `intent_decision.py:32-35` définit `IntentRecallDecision`
     (`action: IntentActionType`).
   - F5 (`apply`) compare `decision.action == IntentActionType.CREATE`
     mais reçoit en pratique le premier (string `"create"`). Marche
     par hasard car `IntentActionType` hérite de `str`. Pas un bug
     actif, mais signal de confusion.
   - `IntentRecallDecision` et `RecallResult` (intent_decision.py)
     ne sont importés nulle part en prod. Dead code candidat.

6. **`memory_context` ignoré par F1 depuis sprint 3.1.** Le
   paramètre est conservé pour compat mais le commentaire du
   fichier le signale comme "à retirer". À nettoyer en T-D si on
   confirme qu'on ne réintroduit pas le boost.

7. **Pas de logging des scores d'intent.** `IntentRecallEngine.resolve`
   retourne `(decision, scored)` mais le caller (LLMExecutionRouter
   étape 2) ignore `scored` (`recall_decision, _ = ...`). Aucun log
   ne mentionne le top 3 ou le score retenu — donc impossible
   d'auditer post-mortem un mauvais match sans rejouer le calcul.
   **Instrumentation indispensable en T-B.**

8. **`Pourquoi elle ne germent pas`** apparaît systématiquement haut
   sur des messages aberrants (cf. §7). Probablement candidat à
   renommage/fusion en T-C, indépendamment du fix de seuil.

9. **`_find_by_name` exact (F3) est insensible à la casse mais
   sensible à l'espacement et aux apostrophes.** `extract_intent_name`
   produit déjà du `.lower()` 60-char, mais aucune normalisation
   d'espacement ni Unicode. Probablement OK en pratique (le LLM
   produit du français standard) mais à noter.

10. **Le truncation à 60 chars de `extract_intent_name`** produit
    des noms tronqués comme `Je veux apprendre la validation
    fonctionnelle sur des capteu`. Sémantiquement préservé en
    général, mais l'embedding du nom tronqué diffère subtilement.
    Côté `_find_by_name`, deux exécutions du namer sur le même
    message peuvent produire deux noms différents (LLM
    stochastique → temperature=0.1 limite mais ne supprime pas).

11. **Aucun test unitaire ne couvre les cas de bug listés.**
    `tests/cognition/test_intent_recall.py` et
    `tests/cognition/test_intent_engine.py` testent la mécanique de
    décision (seuils, branchements) mais pas la qualité sémantique
    du matching sur cas réels. Un fixture `expected_intent` /
    `forbidden_intents` par message-test serait un garde-fou
    naturel pour T-D.

12. **`extra={..., "active_intents": ...}` côté `AgentContext`**
    (LLMExecutionRouter étape 5) passe la liste d'intents actifs
    aux agents. Ces derniers peuvent en théorie influencer la
    réponse — mais ce signal n'est PAS rebouclé sur le matching
    (qui a déjà eu lieu en étape 2). Pas un bug, juste à savoir.

13. **Pathologie de naming en branche SPLIT — dette #23 (nouvelle).**
    Distincte de la dette #22 (truncation côté `extract_intent_name`).
    Quand F1 retourne `action="split"`, le pipeline `LLMExecutionRouter`
    n'appelle PAS `extract_intent_name` (llm_router.py:130-131 ne le
    déclenche que sur `action == "create"`), donc `intent_name=None`.
    `IntentEngine.apply` branche SPLIT (intent_engine.py:191-195)
    bascule alors sur `name = intent_name or message[:60]` — soit
    une **truncation brute au caractère sur le message original**,
    sans passe LLM canonisante. Côté dedup, F3/F4 ne sont pas non
    plus consultés pour SPLIT. Effet observé sur le cas 5 (T4) :
    intent créé avec name `Dans ma cuisine j'ai : Une cocotte, une
    poêle, une planche à`, illisible et impossible à dédupliquer
    par futurs F3 exact-match. Sur l'embedder plat actuel, la zone
    0.40-0.45 est suffisamment peuplée pour que SPLIT se déclenche
    régulièrement → multiplication d'intents fantômes au naming
    inutilisable. T-C sprint 6 doit traiter cette branche : soit
    appeler `extract_intent_name` aussi pour SPLIT, soit retirer
    purement SPLIT et défaulter à CREATE (qui passe par F4 dedup).
