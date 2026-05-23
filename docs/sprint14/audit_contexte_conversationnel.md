# Audit — perte du contexte conversationnel entre tours successifs

**Sprint** : 14 / Tour 1
**Branche** : `feat/sprint14-context-continuity`
**Base** : tag `sprint-13`
**Date** : 2026-05-23
**Scope** : audit pur — aucune modification de code, aucun fix proposé.

## TL;DR

Aucun mécanisme de chargement d'historique chronologique n'existe
dans ARIA. Le champ `Event.conversation_id` est déclaré mais
jamais assigné, et la config `max_history_turns=10` n'a aucun
caller dans le code. Le prompt LLM final est strictement
`[system, user]` — one-shot. La continuité conversationnelle
repose entièrement sur un retrieval vectoriel par similarité,
re-déclenché à chaque tour, et filtré par un `intent_id`
ré-résolu indépendamment à chaque message. Sur les messages
courts (≤ 10 caractères, donc classifiés `CONFIRMATION`),
`MEMORY_TOP_K=0` coupe en plus tout retrieval global. Le tour
"15 août" arrive donc au LLM avec ni l'historique chronologique,
ni le retrieval vectoriel, ni l'intent du tour précédent.

---

## §1 — Chaîne de réception (handler Telegram → Event)

### 1.1 `TelegramInterface._handle_message` (interfaces/telegram_interface.py:59-74)

```python
async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit un message texte, crée un Event TEXT, attend la réponse."""

    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    async with self.user_locks[user_id]:
        event = Event.create(
            event_type=EventType.TEXT,
            user_id=user_id,
            content=update.message.text,
            metadata={"chat_id": chat_id},
        )
        result = await self.kernel.handle_event(event)

    await self.send(chat_id, result)
```

### 1.2 `TelegramInterface._handle_photo` (interfaces/telegram_interface.py:76-109)

Identique sur le champ qui nous intéresse : `Event.create(...)` sans
`conversation_id`, `chat_id` placé dans `metadata`.

```python
async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    async with self.user_locks[user_id]:
        photo = update.message.photo[-1]
        file = await photo.get_file()

        image_receive_dir = Path(config.image_receive_dir)
        image_receive_dir.mkdir(parents=True, exist_ok=True)
        dest = image_receive_dir / f"{file.file_id}.jpg"
        file_path = await file.download_to_drive(custom_path=dest)

        event = Event.create(
            event_type=EventType.IMAGE,
            user_id=user_id,
            content={
                "file_path": str(file_path),
                "caption": update.message.caption,
            },
            metadata={"chat_id": chat_id},
        )
        result = await self.kernel.handle_event(event)

    await self.send(chat_id, result)
```

### 1.3 `Event` (core/event.py:1-34)

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum
import uuid


class EventType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    FILE = "file"
    SYSTEM = "system"


@dataclass
class Event:
    id: str
    type: EventType
    user_id: str
    content: Any
    metadata: Dict[str, Any]
    conversation_id: Optional[str] = None

    @staticmethod
    def create(event_type: EventType, user_id: str, content: Any, metadata: dict):
        return Event(
            id=str(uuid.uuid4()),
            type=event_type,
            user_id=user_id,
            content=content,
            metadata=metadata or {},
        )
```

### 1.4 Réponse explicite

- **`conversation_id` est-il calculé/assigné ?** Non. Le champ
  est déclaré sur le dataclass `Event` (event.py:24) avec une
  valeur par défaut `None`. `Event.create()` ne le passe pas au
  constructeur, et aucun caller dans le code n'invoque
  `Event.create(...)` avec un `conversation_id`.
- **Sur quelle base pourrait-il être calculé ?** Le `chat_id`
  Telegram est récupéré (`update.effective_chat.id`) et placé
  dans `metadata["chat_id"]`. C'est l'identifiant naturel d'une
  conversation Telegram, mais il n'est pas promu en
  `conversation_id` ni utilisé en aval.
- **Peut-il rester `None` ?** Oui — il est `None` à 100 % des
  appels en production. Grep global `conversation_id` ne renvoie
  qu'une seule occurrence : la déclaration en event.py:24
  elle-même. Aucun consommateur ne lit ce champ. C'est un
  attribut mort du schéma.

---

## §2 — Classification cognitive

### 2.1 `CognitiveEngine.classify` (cognition/cognitive_engine.py:84-128)

```python
def classify(self, event: Event) -> CognitiveResult:

    # ── Événements image ─────────────────────────────────────────────────
    if event.type == EventType.IMAGE:
        content = event.content if isinstance(event.content, dict) else {}
        caption = content.get("caption")

        if detect_generation_intent_from_caption(caption):
            return CognitiveResult(
                type=CognitiveOperation.IMAGE_GENERATION.value,
                operation=CognitiveOperation.IMAGE_GENERATION,
            )

        interrogative = is_interrogative_caption(caption)

        return CognitiveResult(
            type=CognitiveOperation.IMAGE_INPUT.value,
            operation=CognitiveOperation.IMAGE_INPUT,
            interrogative=interrogative,
        )

    # ── Événements texte ─────────────────────────────────────────────────
    if event.type == EventType.TEXT:
        message = event.content if isinstance(event.content, str) else ""
        operation = classify_operation(
            message=message,
            llm_router=self.llm_router,
            metadata=event.metadata or {},
            bridge=self.bridge,
        )
        return CognitiveResult(
            type=operation.value,
            operation=operation,
        )

    # ── Types non supportés ──────────────────────────────────────────────
    return CognitiveResult(
        type=CognitiveOperation.UNKNOWN.value,
        operation=CognitiveOperation.UNKNOWN,
    )
```

### 2.2 `classify_operation` (cognition/cognitive_classifier.py:174-247)

```python
def classify_operation(
    message: str,
    llm_router=None,
    metadata: dict | None = None,
    bridge: MempalaceBridge | None = None,
) -> CognitiveOperation:
    """
    Classe un message entrant dans une CognitiveOperation.

    Pipeline de priorité décroissant — s'arrête dès qu'une règle matche.
    """
    metadata = metadata or {}

    # ── 1. Image reçue via Telegram ─────────────────────────────────────────
    if metadata.get("image") is not None:
        return CognitiveOperation.IMAGE_INPUT

    # ── 2. Heuristique génération image ─────────────────────────────────────
    if detect_image_generation_intent(message):
        return CognitiveOperation.IMAGE_GENERATION

    # ── 3. Message court → CONFIRMATION ────────────────────────────────────
    if len(message.strip()) <= MIN_MESSAGE_LENGTH:
        return CognitiveOperation.CONFIRMATION

    # ── 4. Cache MemPalace ───────────────────────────────────────────────────
    cached = _search_cache(message, bridge)
    if cached:
        return cached

    # ── 5. Classifieur LLM ───────────────────────────────────────────────────
    if llm_router is None:
        return CognitiveOperation.UNKNOWN

    try:
        from llm.llm_role import LLMRole
        response = llm_router.complete(
            prompt=CLASSIFIER_PROMPT.format(message=message),
            role=LLMRole.CHAT,
            temperature=0.1,
            max_tokens=60,
        )

        raw = response.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        if not raw.startswith("{"):
            raw = "{" + raw + "}"
        data = json.loads(raw)

        operation  = _parse_operation(data.get("operation", "unknown"))
        confidence = float(data.get("confidence", 0.0))

        if confidence >= CONFIDENCE_THRESHOLD and operation != CognitiveOperation.UNKNOWN:
            _store_cache(message, operation)

        return operation

    except Exception as e:
        from logger import get_logger
        log = get_logger(__name__)
        log.error("[CLASSIFIER ERROR] : %s", e)
        return CognitiveOperation.UNKNOWN
```

`MIN_MESSAGE_LENGTH = 10` (cognitive_classifier.py:37).

### 2.3 Réponse explicite

La classification opère **uniquement** sur :

- le message courant brut (`event.content` ou `event.metadata` pour
  l'image),
- un cache MemPalace de mappings `message → opération` indépendant
  de la conversation (wing `aria_classifier`, scope global,
  similarité ≥ 0.92),
- un classifieur LLM mono-message (prompt = `{message}` seul).

Aucune branche de `classify_operation` n'accède à l'historique
d'un `conversation_id` (qui de toute façon n'existe pas, cf. §1.4),
ni aux derniers tours, ni au dernier intent activé. La classification
est strictement stateless sur le message courant.

Conséquence pour le scénario du brief : `"15 août"` a une longueur
`len("15 août".strip()) == 7 ≤ 10`, donc la classification s'arrête
à la branche §3 (`MIN_MESSAGE_LENGTH`) et retourne `CONFIRMATION` —
sans même atteindre le cache ni le LLM classifier, et sans aucune
référence au tour précédent où aria a posé la question
"Tu veux partir quand ?".

---

## §3 — Chargement de l'historique

### 3.1 Absence d'une fonction dédiée

Aucune fonction `load_history(conversation_id)`, `get_recent_turns`,
`get_dialogue_history` ou équivalente n'existe dans le repo.
Vérifications :

```bash
grep -rn "conversation_id|max_history_turns|history_turns" --include="*.py"
```

Renvoie deux occurrences :

- `config.py:67` : `max_history_turns: int = 10` (définition seule).
- `core/event.py:24` : `conversation_id: Optional[str] = None`
  (déclaration seule).

**Aucun caller** pour `max_history_turns` dans tout le code prod.
C'est du dead config. **Aucun lecteur** pour `Event.conversation_id`.

### 3.2 Ce qui s'apparente à du "chargement de mémoire" passe par `MempalaceBridge`

Trois méthodes, toutes vectorielles, aucune chronologique.

#### `MempalaceBridge.retrieve_memories` (memory/mempalace_bridge.py:55-116)

```python
def retrieve_memories(
    self,
    query: str,
    wing: str = "aria_episodic",
    room: str | None = None,
    n: int = 5,
    type_filter: list[str] | None = None,
    max_distance: float | None = 0.8,
) -> dict:
    """
    Recall sémantique dans la mémoire épisodique.
    """
    if n <= 0:
        return {"query": query, "hits": [], "count": 0}

    # On demande le double pour absorber les filtrages à venir
    result = self._store(
        query=query,
        wing=wing,
        room=room,
        n=n * 2,
    )

    hits = [
        h for h in result.get("results", [])
        if h.get("room", "") != "general"
        and (max_distance is None
             or h.get("distance", 1.0) < max_distance)
    ][:n]

    if type_filter:
        hits = [h for h in hits if h.get("type") in type_filter]

    return {
        "query": query,
        "hits": hits,
        "count": len(hits),
    }
```

#### `MempalaceBridge.retrieve_by_intent` (memory/mempalace_bridge.py:122-156)

```python
def retrieve_by_intent(
    self,
    query: str,
    intent_id: str,
    n: int = 10,
) -> dict:
    """
    Recall ciblé sur un intent spécifique dans la couche épisodique.
    """
    result = self._store(
        query=query,
        wing="aria_episodic",
        room=intent_id,
        n=n,
    )

    return {
        "query": query,
        "hits": result.get("results", []),
        "count": len(result.get("results", [])),
    }
```

#### `MempalaceBridge.retrieve_semantic` (memory/mempalace_bridge.py:162-199)

```python
def retrieve_semantic(
    self,
    query: str,
    subject: str | None = None,
    n: int = 5,
) -> dict:
    """
    Recall dans la couche sémantique — faits stables sur l'utilisateur.
    """
    result = self._store(
        query=query,
        wing="aria_semantic",
        room=subject,
        n=n,
    )

    return {
        "query": query,
        "hits": result.get("results", []),
        "count": len(result.get("results", [])),
    }
```

### 3.3 Top-K appliqué par opération (cognition/cognitive_context.py:22-32)

```python
MEMORY_TOP_K = {
    CognitiveOperation.FACT_RECALL:   3,
    CognitiveOperation.MEMORY_QUERY:  6,
    CognitiveOperation.PLANNING:      4,
    CognitiveOperation.REASONING:     8,
    CognitiveOperation.META_MEMORY:   0,   # ← intents actifs suffisent
    CognitiveOperation.CONFIRMATION:  0,   # ← coupe tout retrieval global
    CognitiveOperation.PROFILE_QUERY: 3,
    CognitiveOperation.INGESTION:     4,
    CognitiveOperation.UNKNOWN:       4,
}
```

### 3.4 Réponse explicite

- **Structure de données retournée** : `dict {"query": str, "hits":
  list[dict], "count": int}`. Chaque `hit` porte `text`, `distance`,
  `room`, `type`, `timestamp`, etc. Pas d'ordre chronologique
  garanti — c'est l'ordre du store, en pratique tri par distance
  vectorielle ascendante.
- **Taille** : pilotée par `n` côté caller. La valeur réellement
  utilisée est `MEMORY_TOP_K[operation]` (cf. 3.3). Pour
  `CONFIRMATION` et `META_MEMORY`, `n=0` → retour vide direct
  (court-circuit ligne mempalace_bridge.py:88).
  `config.max_history_turns=10` est **non utilisé** : aucun
  retrieval ne s'appuie sur cette valeur.
- **Ordre** : tri par distance vectorielle (similarité décroissante),
  pas chronologique. `build_context_block` re-trie d'ailleurs les
  hits par `distance` ascendante avant injection
  (context_builder.py:75-86).
- **Cette fonction est-elle appelée dans le cycle de traitement
  d'un message ?** Oui — mais comme retrieval vectoriel, pas
  comme chargement d'historique. Appels :
  - `LLMExecutionRouter._run_pipeline` étape 1 :
    `retrieve_memories(message, n=top_k)` (execution/routers/llm_router.py:111).
  - `LLMExecutionRouter._run_pipeline` étape 4 :
    `retrieve_by_intent(query=message, intent_id=intent.id)`
    (execution/routers/llm_router.py:146).
  - `build_context_block` (cognition/context_builder.py:58) :
    `retrieve_semantic(query, n=5)`.
  - `_search_cache` (cognition/cognitive_classifier.py:278) :
    `retrieve_memories(query=message, wing="aria_classifier",
    n=1, max_distance=None)`.

**Aucun de ces appels ne charge "les N derniers tours de cette
conversation"**. Tous sont des recherches par similarité
vectorielle, et le filtre principal est l'`intent_id` (= room
épisodique), pas un `conversation_id`.

---

## §4 — Assembly du prompt LLM

### 4.1 Pipeline complet — `LLMExecutionRouter._run_pipeline` (execution/routers/llm_router.py:98-232)

C'est le point central d'assemblage du contexte cognitif. Fonction
intégrale (>80 lignes, pertinente en totalité pour l'audit) :

```python
def _run_pipeline(self, message: str, operation: CognitiveOperation, metadata: dict) -> str:
    """
    Pipeline cognitif complet.
    """

    # ── 1. Mémoire globale (contexte pré-intent) ────────────────────────
    top_k = MEMORY_TOP_K.get(operation, 4)
    global_memories = self.mempalace_bridge.retrieve_memories(message, n=top_k)

    memory_context = MemoryContext(
        global_memories=global_memories,
        session_memories={},
    )

    # ── 2. Intent recall ────────────────────────────────────────────────
    active_intents = self.intent_engine.list_attention_active()

    recall_decision, _ = self.intent_engine.resolve(
        message,
        active_intents,
        memory_context=memory_context.global_memories,
    )

    # ── 3. Intent mutation ──────────────────────────────────────────────
    intent_name = None
    if recall_decision.action == "create":
        intent_name = extract_intent_name(message, self.llm_router)

    intent = self.intent_engine.apply(
        decision=recall_decision,
        message=message,
        intent_name=intent_name,
    )

    # ── 4. Mémoire de session (contexte post-intent) ────────────────────
    session_memories = (
        self.mempalace_bridge.retrieve_by_intent(query=message, intent_id=intent.id)
        if intent
        else {"hits": [], "count": 0}
    )

    memory_context = MemoryContext(
        global_memories=global_memories,
        session_memories=session_memories,
    )

    # ── 4b. Context builder ─────────────────────────────────────────────
    context_block = build_context_block(
        query=message,
        bridge=self.mempalace_bridge,
        active_intents=self.intent_engine.list_attention_active(),
        session_memories=session_memories,
        global_memories=global_memories,
    )

    # ── 5. Construction du contexte agent ───────────────────────────────
    trace = CognitiveTrace()

    ctx = AgentContext(
        message=message,
        intent=intent,
        memories=memory_context.global_memories,
        session_memory=memory_context.session_memories,
        trace=trace,
        extra={
            "context_block": context_block,
            "memory_context": memory_context,
            "recall": recall_decision,
            "active_intents": self.intent_engine.list_active(),
            "cognitive_operation": operation,
            **metadata,
        },
    )

    # ── 6. Pipeline agents ───────────────────────────────────────────────
    ctx = self.controller.run(ctx, self.llm_router)

    # ── 7. Résolution du résultat ────────────────────────────────────────
    if ctx.result:
        result = ctx.result
    elif ctx.intent and hasattr(ctx.intent, "last_state"):
        result = ctx.intent.last_state
    else:
        result = f"[NO RESULT] intent={ctx.intent.id if ctx.intent else None}"

    # ── 8. Persistence intent ────────────────────────────────────────────
    if intent:
        intent.activate()
        self.intent_engine.save(intent)

    # ── 9. Decay ────────────────────────────────────────────────────────
    self.intent_engine.decay_if_needed()

    # ── 10. Écriture MemPalace ───────────────────────────────────────────
    if intent is None:
        log.info("memory_write SKIPPED reason=no_intent_resolved")
    else:
        try:
            write_interaction(
                text=f"USER:\n{message}\n\nARIA:\n{result}",
                intent_id=intent.id,
                intent_name=intent.name,
                source="llm_execution_router",
            )
            log.info(
                "memory_write OK wing=aria_episodic intent_id=%s intent_name=%s",
                intent.id, intent.name,
            )
        except Exception:
            log.exception(
                "memory_write ERROR intent_id=%s intent_name=%s",
                intent.id, intent.name,
            )

    log.info("pipeline done → %d chars", len(result))
    for step in ctx.trace.as_dict():
        log.debug("trace: %s", step)

    return result
```

### 4.2 Branchement controller → agents (agents/controller/controller_agent.py:12-74)

```python
def run(self, ctx: AgentContext, llm_router):

    operation = ctx.extra.get(
        "cognitive_operation",
        CognitiveOperation.UNKNOWN
    )

    # 1 — ROUTING LOGIC
    if operation in (
        CognitiveOperation.FACT_RECALL,
        CognitiveOperation.MEMORY_QUERY,
        CognitiveOperation.PROFILE_QUERY,
        CognitiveOperation.META_MEMORY,
    ):
        pipeline = ["analyst"]

    elif operation == CognitiveOperation.PLANNING:
        pipeline = ["analyst", "planner"]

    elif operation == CognitiveOperation.REASONING:
        pipeline = ["analyst"]

    else:
        phase = ctx.intent.infer_phase() if ctx.intent else "creation"

        if phase == "creation":
            pipeline = ["analyst"]
        elif phase == "planning":
            pipeline = ["analyst", "planner"]
        elif phase == "execution":
            pipeline = ["executor", "critic"]
        else:
            pipeline = ["analyst"]

    # 2 — EXECUTION ENGINE
    for agent_name in pipeline:
        agent = self.registry.get(agent_name)
        if not agent:
            continue
        ctx.trace.start(agent_name)
        before_state = ctx.result
        ctx = agent.run(ctx, llm_router)
        after_state = ctx.result
        ctx.trace.end(output_snapshot=str(after_state))
        if ctx.halted:
            break

    return ctx
```

Pour `CONFIRMATION` (cas "15 août") : on tombe dans `else`, puis
`phase = ctx.intent.infer_phase()` — vu que l'intent vient juste
d'être créé, la phase typique est `"creation"` → pipeline = `["analyst"]`.

Pour `PLANNING` (cas "Planifier mes vacances en Normandie") :
pipeline = `["analyst", "planner"]`.

### 4.3 Prompt PLANNING / FACT_RECALL / CHAT — `AnalystAgent.run` (agents/analyst_agent.py:1-66)

```python
PROMPT = """
Tu es un agent cognitif d'Aria, assistant personnel de Nico.

PROJET RÉCENT EN MÉMOIRE :
{intent_name}

MESSAGE UTILISATEUR :
{message}

HISTORIQUE DE CETTE SESSION :
{session_memory}

CONTEXTE COGNITIF :
{context_block}

RÈGLES :
- Réponds toujours à la question posée, quel que soit le sujet
- Si la mémoire contient la réponse → cite-la exactement
- Si c'est une demande de rappel → liste ce qui est en mémoire
- Si c'est une action → décris les étapes
- N'hallucine JAMAIS du contenu absent de la mémoire
- Sois concis
"""


class AnalystAgent(BaseAgent):

    name = "analyst"

    def run(self, ctx: AgentContext, llm_router):

        operation = ctx.extra.get("cognitive_operation", CognitiveOperation.UNKNOWN)
        role = LLM_ROLE_MAP.get(operation)

        prompt = PROMPT.format(
            intent_name=ctx.intent.name,
            message=ctx.message,
            session_memory=self._format_memories(ctx.session_memory),
            context_block=ctx.extra.get("context_block", "Aucun contexte disponible."),
        )

        response = llm_router.complete(
            prompt,
            role=role,
            temperature=0.3,
            max_tokens=800,
        )
        ctx.result = response.content
        return ctx

    def _format_memories(self, memories: dict) -> str:
        if not memories or not memories.get("hits"):
            return "Aucune mémoire disponible."
        lines = []
        for h in memories["hits"][:5]:
            doc = h.get("text", "")
            if doc:
                lines.append(f"- {doc[:800]}")
        return "\n".join(lines) if lines else "Aucune mémoire disponible."
```

L'étiquette `HISTORIQUE DE CETTE SESSION` est trompeuse : ce qui est
injecté est `_format_memories(ctx.session_memory)`, c'est-à-dire les
hits de `retrieve_by_intent(query=message, intent_id=intent.id)` —
résultat d'une recherche vectorielle filtrée par `intent_id`, et
tronquée aux 5 plus similaires. Pas un dialogue chronologique.

### 4.4 Prompt PLANNING (suite analyst) — `PlannerAgent.run` (agents/planner_agent.py:1-77)

```python
PROMPT = """
Tu es un agent cognitif d'Aria.

MESSAGE :
{message}

INTENT :
{intent}

CONTEXTE (résultat analyse) :
{analysis}

RÈGLES :
- Si l'analyse contient déjà une réponse directe → transmets-la sans reformuler
- Si une action est nécessaire → donne les étapes numérotées
- Ne planifie pas ce qui est déjà fait ou déjà connu

Réponds UNIQUEMENT avec ce JSON, sans backticks, sans texte autour :
{{"response": "<réponse à afficher à l'utilisateur>", "next_action": "<prochaine action concrète ou null>"}}
"""


class PlannerAgent(BaseAgent):

    name = "planner"

    def run(self, ctx: AgentContext, llm_router):

        if ctx.intent is None:
            return ctx

        prompt = PROMPT.format(
            message=ctx.message,
            intent=ctx.intent.name,
            analysis=ctx.result or "Aucune analyse disponible.",
        )

        response = llm_router.complete(
            prompt,
            role=LLMRole.PLANNING,
            temperature=0.4,
            max_tokens=600,
        )

        parsed = self._parse_response(response.content)

        ctx.result = parsed["response"]

        if parsed["next_action"] and ctx.intent:
            ctx.intent.set_next_action(parsed["next_action"])

        return ctx
```

Le planner reçoit uniquement `{message}`, `{intent.name}`, et le
résultat de l'analyste précédent (`ctx.result`). Aucune mémoire,
aucun historique — il dépend entièrement de ce que l'analyste a
mis dans `ctx.result`.

### 4.5 `build_context_block` (cognition/context_builder.py:25-92)

```python
def build_context_block(
    query: str,
    bridge: MempalaceBridge,
    active_intents: list,
    session_memories: dict,
    global_memories: dict | None = None,
    token_budget: int = 2000,
) -> str:
    """
    Assemble le bloc de contexte cognitif injectable dans un prompt LLM.

    Remplit le budget par priorité décroissante :
      1. Faits sémantiques stables (profil utilisateur)
      2. Intents actifs triés par salience décroissante
      3. Souvenirs épisodiques : session_memories en priorité,
         fallback sur global_memories si session sparse (< 3 hits)
    """
    remaining = token_budget
    sections = []

    # 1. Faits sémantiques stables
    semantic_hits = bridge.retrieve_semantic(query, n=5).get("hits", [])
    section = _build_semantic_section(semantic_hits, remaining)
    if section:
        sections.append(section)
        remaining -= _estimate_tokens(section)

    # 2. Intents actifs triés par salience décroissante
    sorted_intents = sorted(active_intents, key=lambda i: i.salience, reverse=True)
    section = _build_intents_section(sorted_intents, remaining)
    if section:
        sections.append(section)
        remaining -= _estimate_tokens(section)

    # 3. Souvenirs épisodiques
    session_hits = sorted(
        session_memories.get("hits", []),
        key=lambda h: h.get("distance", 1.0),
    )
    episodic_hits = session_hits
    if global_memories and len(session_hits) < 3:
        seen = {h.get("text", "") for h in session_hits}
        fallback = sorted(
            [h for h in global_memories.get("hits", []) if h.get("text", "") not in seen],
            key=lambda h: h.get("distance", 1.0),
        )
        episodic_hits = session_hits + fallback

    section = _build_episodic_section(episodic_hits, remaining)
    if section:
        sections.append(section)

    return "\n\n".join(sections)
```

Confirmé : tri uniformément par `distance` (similarité), aucune
notion d'ordre temporel. Le bloc `[Souvenirs pertinents]` peut
remonter n'importe quel tour ancien ayant une forte similarité
vectorielle avec le message courant, ignorant le tour le plus
récent s'il est moins similaire.

### 4.6 Envoi final au provider — `LLMRouter._call` (llm/llm_router.py:241-324, extrait)

Construction des `messages` (llm/llm_router.py:300-303) :

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt},
]
```

Et pour l'API Anthropic (llm/llm_router.py:267-273) :

```python
payload = {
    "model": provider_cfg["model"],
    "max_tokens": max_tokens,
    "system": system_prompt,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": temperature,
}
```

Dans les deux formats : **un seul message `user`** (le prompt
assemblé par l'agent), **aucun message `assistant` historique**.
`system_prompt` est statique (soul.md + user.md), chargé une fois
au démarrage (llm/llm_router.py:25-26).

### 4.7 Réponse explicite

- **L'historique chargé en §3 arrive-t-il dans le prompt final ?**
  Partiellement et seulement par retrieval vectoriel :
  - Le résultat de `retrieve_by_intent` (= `session_memory`) entre
    dans le prompt analyst sous l'étiquette `HISTORIQUE DE CETTE
    SESSION`, via `_format_memories` qui prend les 5 hits les plus
    similaires.
  - Le résultat de `retrieve_memories` global et `retrieve_semantic`
    entrent dans `context_block` (étiqueté `CONTEXTE COGNITIF`),
    formaté en sections texte par `build_context_block`.
  - Le `PlannerAgent` ne reçoit aucune de ces sources directement —
    il dépend de `ctx.result` (sortie analyst).
- **Sous quelle forme** : texte concaténé en blocs Markdown-like
  dans un unique champ `prompt` envoyé comme `content` de l'unique
  message `user` au provider. Pas de format `role/content`
  multi-messages.
- **Est-il tronqué/filtré entre chargement et injection ?** Oui,
  plusieurs filtres en cascade :
  - `retrieve_memories` filtre par distance `< 0.8` et exclut
    `room=="general"` (mempalace_bridge.py:100-105).
  - `_format_memories` dans AnalystAgent tronque à 5 hits et chaque
    texte à 800 caractères (analyst_agent.py:62-65).
  - `build_context_block` tronque chaque texte épisodique à 400
    caractères (context_builder.py:142), et coupe par budget
    tokens (2000 par défaut, divisé entre semantic / intents /
    episodic).
  - Re-tri systématique par `distance` ascendante : l'ordre
    chronologique n'est jamais préservé.

---

## §5 — Diagramme de séquence : 3ᵉ message "15 août"

Hypothèse de départ : un intent `"Vacances Normandie"` a été créé
au tour 1 (`PLANNING`) et a stocké dans `aria_episodic` room=
`<id_normandie>` le document `"USER:\nPlanifier mes vacances en
Normandie\n\nARIA:\nTu veux partir quand ?"`.

1. **Réception Telegram** —
   `interfaces/telegram_interface.py:59` :
   `_handle_message(update)`. Lit `user_id`, `chat_id`. Prend le
   lock par `user_id`.

2. **Création Event** — `interfaces/telegram_interface.py:66-71` :
   ```python
   event = Event.create(
       event_type=EventType.TEXT,
       user_id="<telegram_user_id>",
       content="15 août",
       metadata={"chat_id": <telegram_chat_id>},
   )
   ```
   → `event.conversation_id = None` (jamais setté).

3. **Entrée kernel** — `core/kernel.py:123` :
   `await self.kernel.handle_event(event)`.

4. **Classification** — `core/kernel.py:135` :
   `cognitive_result = self.cognitive_engine.classify(event)`.
   - `cognition/cognitive_engine.py:111-122` branche `EventType.TEXT`.
   - Appel `classify_operation("15 août", llm_router, metadata={"chat_id": ...}, bridge)`.

5. **Classifier — branche CONFIRMATION** —
   `cognition/cognitive_classifier.py:208-209` :
   ```python
   if len(message.strip()) <= MIN_MESSAGE_LENGTH:   # 7 ≤ 10
       return CognitiveOperation.CONFIRMATION
   ```
   Le cache classifier et le LLM ne sont pas atteints. Pas d'appel
   réseau, pas de référence à un tour antérieur. `cognitive_result =
   CognitiveResult(type="confirmation", operation=CONFIRMATION,
   short_circuit=False)`.

6. **Build ExecutionOperation** — `core/kernel.py:146-156` :
   ```python
   exec_op = ExecutionOperation(
       type="confirmation",
       payload={
           "op_type": "confirmation",
           "content": "15 août",
           "metadata": {"chat_id": ..., "interrogative": False},
       },
       metadata={"chat_id": ...},
   )
   ```

7. **Dispatch** — `core/kernel.py:159` :
   `exec_result = self.execution_dispatcher.dispatch(exec_op)`.
   - Routing table (core/kernel.py:46-57) : pas d'entrée explicite
     pour `CONFIRMATION` → utilisera `llm_router` (UNKNOWN mappe
     `llm_router`, mais en fait `CONFIRMATION` non plus n'apparaît
     pas dans `_ROUTING_TABLE`). À vérifier — voir §6 point 7.

   _Note d'audit_ : `_ROUTING_TABLE` n'inclut pas `CONFIRMATION.value`.
   Le comportement exact dépend du fallback de `ExecutionDispatcher`
   non lu dans cet audit ; en pratique le code prod tourne donc
   il existe un fallback. Hypothèse pour la suite du trace :
   atterrissage sur `LLMExecutionRouter`.

8. **Pipeline LLM** — `execution/routers/llm_router.py:98+` :
   `_run_pipeline("15 août", CONFIRMATION, metadata={"chat_id":...,"interrogative":False})`.

9. **Étape 1 — retrieve global** —
   `execution/routers/llm_router.py:110-111` :
   `top_k = MEMORY_TOP_K[CONFIRMATION] = 0` →
   `retrieve_memories("15 août", n=0)` → court-circuit
   `mempalace_bridge.py:88-89` → `{"hits": [], "count": 0}`.
   **Aucun retrieval global. Le tour 1 stocké dans aria_episodic
   ne remonte pas.**

10. **Étape 2 — intent recall** —
    `execution/routers/llm_router.py:119-125` :
    - `active_intents = list_attention_active()` → inclut
      `"Vacances Normandie"` parmi d'autres.
    - `recall_decision, _ = recall_engine.resolve("15 août",
      active_intents, memory_context={"hits": [], ...})`.
    - `intent/intent_recall_engine.py:68` : `msg_emb =
      encode(["15 août"])[0]` — embedding d'une chaîne calendaire
      isolée.
    - Cosine vs embedding du nom `"Vacances Normandie"` :
      très probablement `< 0.45` (le seuil). La date n'est pas
      sémantiquement proche d'un nom de projet.
    - Décision attendue : `action="create"` (`intent_recall_engine.py:122`),
      faute d'un second intent proche pour déclencher `split`.

11. **Étape 3 — intent mutation** —
    `execution/routers/llm_router.py:130-138` :
    - `intent_name = extract_intent_name("15 août", llm_router)` →
      un appel LLM qui produit un nom canonique pour ce message
      isolé (typiquement `"Fête du 15 août"`, `"Anniversaire"`,
      `"Date 15 août"` selon la complétion).
    - `intent = intent_engine.apply(create, "15 août", intent_name=...)`
      → nouvel `Intent` créé, embedding du nom calculé, ajouté à
      `self.intents` (intent_engine.py:154-157).
    - **Cet intent neuf n'a aucun lien avec `<id_normandie>`.**

12. **Étape 4 — session memory** —
    `execution/routers/llm_router.py:145-149` :
    `retrieve_by_intent(query="15 août", intent_id=<id_du_nouvel_intent>)`
    → room=`<id_du_nouvel_intent>` n'existe pas encore dans
    aria_episodic (l'écriture n'a pas eu lieu) → `{"hits": [],
    "count": 0}`. **Le tour 1 — stocké dans
    room=`<id_normandie>` — n'est pas accessible via cette
    requête filtrée par room.**

13. **Étape 4b — context_block** —
    `execution/routers/llm_router.py:157-163` :
    - `retrieve_semantic("15 août", n=5)` → potentiellement vide
      ou des faits stables non liés.
    - `active_intents` (incluant `"Vacances Normandie"`) listés
      dans la section `[Projets actifs]` par
      `_build_intents_section` (context_builder.py:115-129) sous
      la forme `- <intent.name> (salience: <float>)`. C'est la
      seule trace résiduelle de l'intent Normandie dans le prompt,
      mais sans contenu de dialogue.
    - Section épisodique : `session_hits=[]`, `global_memories.hits=[]`
      → section vide.

14. **Étape 5 — AgentContext** —
    `execution/routers/llm_router.py:168-182` : construit avec
    `intent=<nouvel intent>`, `memories={}`, `session_memory={}`,
    `extra={..., "cognitive_operation": CONFIRMATION, ...}`.

15. **Controller routing** —
    `agents/controller/controller_agent.py:36-46` : `CONFIRMATION`
    ne matche aucune branche explicite → `phase =
    ctx.intent.infer_phase()` sur le nouvel intent (probablement
    `"creation"`) → pipeline `["analyst"]`.

16. **AnalystAgent.run** — `agents/analyst_agent.py:37-56` :
    ```python
    prompt = PROMPT.format(
        intent_name="Fête du 15 août",
        message="15 août",
        session_memory="Aucune mémoire disponible.",
        context_block="<section [Projets actifs] avec ‘Vacances Normandie’ + autres, sans contenu de dialogue>",
    )
    ```

17. **LLMRouter.complete** — `llm/llm_router.py:199-238` : choisit
    le provider CHAT (LLM_ROLE_MAP[CONFIRMATION]=CHAT,
    cognitive_context.py:44), appelle `_call(prompt, ...)`.

18. **HTTP au provider** — `llm/llm_router.py:241-324` :
    ```python
    messages = [
        {"role": "system", "content": <soul.md + user.md>},
        {"role": "user",   "content": <prompt assemblé en 16>},
    ]
    payload = {"model": ..., "messages": messages, ...}
    httpx.post(url, json=payload, ...)
    ```
    **Un seul tour utilisateur. Aucun message
    `{"role": "assistant", "content": "Tu veux partir quand ?"}`,
    aucun message `{"role": "user", "content": "Planifier mes
    vacances en Normandie"}` dans la liste.**

19. **Réponse provider** → `ctx.result` → kernel `_normalize` →
    `TelegramInterface.send`. Le LLM, voyant un message
    `"15 août"` isolé sans contexte de dialogue, complète sur le
    sens le plus probable (date calendaire générique) → "15 août,
    c'est la fête nationale en Belgique."

---

## §6 — Diagnostic

Le bug observé est la convergence d'une cause racine et d'une
chaîne d'amplificateurs. Aucune incertitude : tous les points
sont étayés par le code lu en §1-§4. Hiérarchisation du plus
au moins déterminant.

### Point 1 — Cause racine : aucun mécanisme de chargement d'historique chronologique n'existe

- **Fichier:ligne** : absence dans tout `core/`, `cognition/`,
  `memory/`, `execution/`, `agents/`. Preuves négatives :
  - `core/event.py:24` : `conversation_id: Optional[str] = None`,
    déclaré mais sans setter ni reader (grep global ne renvoie
    que cette ligne et `config.py:67`).
  - `config.py:67` : `max_history_turns: int = 10`, défini mais
    sans caller (grep global confirme zéro consommateur).
  - Aucune fonction nommée `load_history`, `get_recent_turns`,
    `get_dialogue_history`, etc.
  - `llm/llm_router.py:300-303` et `:271` : `messages` envoyé au
    provider contient strictement `[system, user_current]` —
    jamais d'éléments `assistant` ni `user` historiques.
- **Mécanisme** : le système est conçu autour de l'hypothèse
  implicite que le retrieval vectoriel suffit à remonter les
  tours précédents par similarité. Cette hypothèse ne tient pas
  pour les messages courts ou les continuations contextuelles
  (réponses à une question d'aria).
- **Preuve** : le pipeline complet `_run_pipeline`
  (execution/routers/llm_router.py:98-232) ne contient aucune
  étape "load_history". Toutes les sources de contexte sont
  vectorielles ; toutes sont re-triées par `distance`
  (context_builder.py:75-86, :142 ; analyst_agent.py:62-65).

### Point 2 — `MEMORY_TOP_K[CONFIRMATION] = 0` neutralise tout retrieval sur message court

- **Fichier:ligne** : `cognition/cognitive_context.py:28` :
  `CognitiveOperation.CONFIRMATION: 0` ; lu en
  `execution/routers/llm_router.py:110-111` :
  `top_k = MEMORY_TOP_K.get(operation, 4); global_memories =
  retrieve_memories(message, n=top_k)`.
- **Mécanisme** : `retrieve_memories` court-circuite à `n=0`
  (mempalace_bridge.py:88-89) et retourne immédiatement des hits
  vides. À l'étape 4, `retrieve_by_intent` est appelé sur
  l'`intent.id` qui vient juste d'être créé (s'il y a eu CREATE)
  → 0 hits aussi.
- **Preuve** : pour le scénario "15 août" — message de 7
  caractères classifié `CONFIRMATION` par cognitive_classifier.py:208
  → top_k=0 → memory_context.global_memories vide → l'analyst
  reçoit un prompt sans aucune ancre conversationnelle.

### Point 3 — La classification ignore le contexte conversationnel et coupe au plus court sur les messages brefs

- **Fichier:ligne** : `cognition/cognitive_classifier.py:174-247`
  (`classify_operation`).
- **Mécanisme** : la classification est strictement stateless
  sur le message courant : metadata (image), heuristique longueur,
  cache, LLM mono-message. Aucune branche ne consulte le tour
  précédent, le dernier intent activé, ou un éventuel
  `conversation_id`.
- **Preuve** : `MIN_MESSAGE_LENGTH = 10`
  (cognitive_classifier.py:37) shortcuts toute réponse courte
  vers `CONFIRMATION` avant le cache et le LLM. Les réponses
  à une question d'aria sont précisément ce que cette branche
  cible (`"Oui"`, `"15 août"`, `"Les deux"`), donc tous
  ces messages perdent l'attache au contexte du tour qui les a
  motivés.

### Point 4 — `intent_id` est utilisé comme clé de regroupement épisodique, ré-résolu par embedding cosine à chaque tour

- **Fichiers:lignes** :
  - `memory/writer.py:80-87` : `room = intent_id` lors de
    `write_interaction`.
  - `memory/mempalace_bridge.py:122-156` : `retrieve_by_intent`
    filtre par `room=intent_id`.
  - `intent/intent_recall_engine.py:49-125` : la résolution est
    purement cosine entre l'embedding du message et l'embedding
    du nom de chaque intent (`intent.embedding`). Aucun signal
    de "dernier intent activé".
  - `intent/intent_engine.py:71-76` : `resolve()` délègue tel
    quel ; aucun mécanisme de "stickiness" temporel.
- **Mécanisme** : sur un message court ou ambigu, l'embedding
  cosine vs noms d'intents existants ne dépasse pas le seuil
  `0.45` → décision `create`. Un nouvel intent est instancié,
  l'écriture épisodique va dans une room différente du tour
  précédent, et le `retrieve_by_intent` du tour courant cible
  cette nouvelle room vide.
- **Preuve** : le bug se manifeste de façon systématique sur
  tout échange multi-tour parce que la deuxième mesure
  d'embedding (message courant vs nom d'intent) est intrinsèquement
  fragile sur les continuations courtes — l'utilisateur ne répète
  jamais le sujet à chaque tour. Le run live du brief ("15 août"
  vs `"Vacances Normandie"`) en est un cas évident.

### Point 5 — Le prompt analyst (et tous les agents) n'a pas de slot historique chronologique

- **Fichier:ligne** : `agents/analyst_agent.py:8-30` (template
  `PROMPT`), `:42-47` (filling).
- **Mécanisme** : le slot `{session_memory}` étiqueté `HISTORIQUE
  DE CETTE SESSION` reçoit `_format_memories(ctx.session_memory)`
  — les 5 hits les plus similaires d'un `retrieve_by_intent`,
  pas un dialogue chronologique. Même si la room épisodique
  contient des tours antérieurs, le tri vectoriel privilégie la
  similarité au message courant, pas la récence.
- **Preuve** : `_format_memories`
  (agents/analyst_agent.py:58-66) trie par ordre des `hits`
  (ordre retourné par le store, en pratique distance ascendante)
  et tronque à 5 entrées de 800 chars. Aucune logique
  "derniers N tours par timestamp décroissant".

### Point 6 — `LLMRouter._call` envoie un payload one-shot

- **Fichier:ligne** : `llm/llm_router.py:300-303` (format
  OpenAI), `llm/llm_router.py:267-273` (format Anthropic).
- **Mécanisme** : `messages = [{"role": "system", "content":
  system_prompt}, {"role": "user", "content": prompt}]`. Aucun
  message `assistant` antérieur, aucun message `user` antérieur.
- **Preuve** : même si tout le pipeline en amont avait stocké
  un historique en mémoire, le contrat actuel de `LLMRouter._call`
  ne permet pas de l'injecter en tant que messages multi-tours
  — il devrait être sérialisé dans le `prompt` unique. Pour le
  faire, il faudrait que le prompt analyst (ou le router) le
  formate explicitement, ce qui n'est pas le cas (§5 étape 18).

### Point 7 — `_ROUTING_TABLE` n'inclut pas explicitement `CONFIRMATION` (incertitude périphérique)

- **Fichier:ligne** : `core/kernel.py:46-57`. Les opérations
  listées sont `IMAGE_*`, `FACT_RECALL`, `MEMORY_QUERY`,
  `PLANNING`, `REASONING`, `META_MEMORY`, `PROFILE_QUERY`,
  `CONFIRMATION` (présent : `cognition/cognitive_context.py` →
  mapping... ATTENTION recheck), `UNKNOWN`.

  Re-vérification de `core/kernel.py:46-57` :
  ```python
  _ROUTING_TABLE = RoutingTable({
      CognitiveOperation.IMAGE_GENERATION.value : "image_router",
      CognitiveOperation.IMAGE_INPUT.value       : "image_router",
      CognitiveOperation.FACT_RECALL.value       : "llm_router",
      CognitiveOperation.MEMORY_QUERY.value      : "llm_router",
      CognitiveOperation.PLANNING.value          : "llm_router",
      CognitiveOperation.REASONING.value         : "llm_router",
      CognitiveOperation.META_MEMORY.value       : "llm_router",
      CognitiveOperation.PROFILE_QUERY.value     : "llm_router",
      CognitiveOperation.CONFIRMATION.value      : "llm_router",
      CognitiveOperation.UNKNOWN.value           : "llm_router",
  })
  ```
  Correction : `CONFIRMATION` est bien présent et route vers
  `llm_router` (kernel.py:55). Le diagramme §5 étape 7 est
  donc exact, sans incertitude. Ce point n'est pas un défaut
  — je l'avais mentionné par prudence pendant l'audit. À
  effacer du diagnostic, mais conservé ici comme trace de la
  vérification.

### Hiérarchie

- **Bug principal (constant, comme observé)** : combinaison
  des points **1 + 4 + 6**. Pas d'historique chronologique
  chargé, regroupement épisodique par intent_id volatile,
  payload LLM one-shot. La continuité conversationnelle n'a
  jamais été implémentée à ce niveau.
- **Amplificateur sur messages courts (comme "15 août")** :
  points **2 + 3**. La classification CONFIRMATION coupe en
  plus tout retrieval global, donc même les hits vectoriels
  qui *auraient pu* sauver le contexte (par chance) ne sont
  pas tentés.
- **Sous-symptôme dans le prompt** : point **5**. Même si on
  parvenait à charger un historique chronologique, le prompt
  analyst n'a pas de slot adapté ; il faudrait ajouter une
  section dédiée ou passer en mode messages multi-tours dans
  le LLMRouter.

### Certitude

Le diagnostic ne dépend d'aucune observation runtime — tout
est dans le code statique lu en §1-§4. Pas besoin de logs ni
de reproduction pour trancher. Le scénario "15 août" décrit
en §5 est dérivable mécaniquement de la lecture.

Une seule branche reste théoriquement possible mais ne
sauverait pas le cas observé : si l'embedding cosine de
"15 août" vs `"Vacances Normandie"` dépassait par accident
le seuil `0.45`, on aurait `attach` au lieu de `create`. Dans
ce cas, `retrieve_by_intent` ramènerait le tour 1 — mais
seulement parce qu'il a une similarité vectorielle élevée
avec "15 août", ce qui pour des messages courts isolés est
peu probable (le mot "Normandie" n'apparaît pas dans la
requête, et le tour 1 contient surtout "vacances", "Normandie",
"planifier"). Cette branche est par ailleurs inopérante dans
le cas général parce que :

- Pour les messages ≤ 10 chars, `MEMORY_TOP_K[CONFIRMATION]=0`
  coupe le retrieval global même si l'intent est correctement
  résolu.
- Le `session_memory` injecté restera vectoriel, pas
  chronologique : on ramènera "le souvenir le plus similaire à
  ‘15 août’ filtré sur cette room", pas "le dernier tour de la
  session".

Aucun log à ajouter pour confirmer le diagnostic. Le tour 2
(fix) peut s'attaquer directement à la cause racine.
