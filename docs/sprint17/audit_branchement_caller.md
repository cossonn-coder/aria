─────────────────────────────────────────────────────────────────────────
ARIA — Sprint 17, tour 1 : audit branchement caller (A3, fil rouge #34)
─────────────────────────────────────────────────────────────────────────

**Date**      : 2026-05-25
**Branche**   : `feat/sprint17-conversation-wiring` (depuis `sprint-16`)
**Cadre**     : tour 1 du sprint 17 (A3 — branchement caller).
  Audit pur, aucun code production modifié. Tranche les
  cinq décisions du kickoff §"Décisions à trancher au tour 1"
  plus les trois décisions ajoutées par la trame du brief
  (sections 4, 5, 6 ci-dessous).

─────────────────────────────────────────────────────────────────────────

## 0. Synthèse exécutive (à lire en premier)

Quatre constats critiques émergent de la cartographie. Trois
contredisent ou nuancent fortement le kickoff sprint 17 et
appellent une décision architecte avant ouverture du tour 2.

### 0.1 — Constat C1 (bloquant) : le bridge prod n'est pas câblé pour la lecture

`core/kernel.py:111` instancie le `MempalaceBridge` de
production **sans** le callable `get_by_metadata` :

```python
mempalace_bridge = MempalaceBridge(store=mempalace_search)
```

Or `MempalaceBridge.load_conversation_history` lève
`RuntimeError("get_by_metadata callable required …")` quand
le second argument est absent (`memory/mempalace_bridge.py:243-247`).

→ Un appel de l'agent à `bridge.load_conversation_history(...)`
en prod aujourd'hui plante immédiatement. Le sprint 17 doit
**modifier `core/kernel.py:108-112` pour injecter
`get_by_metadata`** depuis `memory.mempalace_store`. Une ligne
de fix, mais c'est une intervention dans `core/` qui dépasse
strictement le périmètre `agents/` annoncé par le kickoff.

### 0.2 — Constat C2 (bloquant) : `write_conversation_turn` n'est appelée nulle part en prod

Grep exhaustif `write_conversation_turn` sur le repo :

```
memory/writer.py:173:  def write_conversation_turn(  # déclaration
tests/memory/test_writer.py:*  # 7 tests unitaires
```

**Zéro caller de production.** L'écriture mémoire d'un échange
est aujourd'hui faite par `write_interaction` dans
`execution/routers/llm_router.py:212-217`, sous wing
`aria_episodic`, avec un texte concaténé `f"USER:\n{message}\n\nARIA:\n{result}"`.

Conséquences :
- La wing `aria_conversation` est **vide** en palace prod.
- `load_conversation_history(conversation_key, n=N)` retournera
  systématiquement `[]` tant qu'on n'a pas câblé `write_conversation_turn`.
- Le branchement lecture-seule serait donc opérationnellement
  inerte : ARIA chargerait toujours un historique vide, l'A3
  ne fermerait pas le fil rouge #34.

Le kickoff sprint 17 §"Hors-scope strict" écrit :

> Pas de modification de `write_conversation_turn` (le writer
> du sprint 15) — il continue d'être appelé à l'endroit actuel.

**L'endroit actuel n'existe pas.** C'est exactement la classe
de constat que la "leçon 9" du kickoff demande de remonter en
tour 1 (le brief architecte peut se tromper sur la réalité du
code).

→ Le sprint 17 doit **AUSSI câbler l'écriture conversationnelle**,
pas uniquement la lecture. Position d'audit développée §2.b et
arbitrage final §7 (décision D5).

### 0.3 — Constat C3 (non-bloquant) : sprint 16 a manqué 2 callers prod de `complete`

`docs/sprint16/audit_llm_router.md` §3.a liste 4 callers prod
(`analyst_agent.py:49`, `planner_agent.py:44`,
`cognitive_classifier.py:222`, `intent_namer.py:20`). Il en
manque deux :

- `agents/executor_agent.py:49` (prompt unique avec slot HISTORIQUE)
- `agents/critic_agent.py:47` (prompt unique pour critique)

Soit **6 callers prod** au total. Sans incidence sur sprint 17
(le brief cible uniquement Analyst), mais à signaler en dette
adjacente (cf. §8.3).

### 0.4 — Constat C4 (non-bloquant) : le slot "HISTORIQUE DE CETTE SESSION" est un misnomer

Le slot HISTORIQUE actuel d'AnalystAgent est alimenté par
`ctx.session_memory` (cf. §1.b), qui contient les hits d'un
`retrieve_by_intent(query=message, intent_id=intent.id)`
(`execution/routers/llm_router.py:146`). **Ce ne sont PAS des
messages de conversation**, ce sont des recalls vectoriels
épisodiques filtrés par `intent_id`, formatés en bullet-list
de 800 chars max. Le slot porte un nom trompeur depuis avant
sprint 15.

→ Sa disparition au sprint 17 (remplacé par le canal `messages`
natif) ne supprime PAS le retrieval épisodique par intent : ce
même `session_memories` continue d'alimenter `context_block`
via `build_context_block` (`execution/routers/llm_router.py:161`).
Pas de perte d'information. Confirmé §6.a.

### 0.5 — Verrou supplémentaire à respecter

Le test garde-fou `tests/agents/test_analyst_prompt_guard.py`
lit la constante `PROMPT` du module et vérifie quatre ancres :
absence de `"domaine actuel"` et `"uniquement dans le domaine"`,
présence de `"quel que soit le sujet"` et `"projet récent en mémoire"`,
longueur > 200 caractères.

→ Le nouveau system prompt construit côté caller au sprint 17
doit préserver ces quatre ancres. Constat injecté dans
l'arbitrage de composition (D8).

─────────────────────────────────────────────────────────────────────────

## 1. Cartographie du caller actuel (Section 1 du brief)

### 1.a — Code intégral du caller AnalystAgent

Le cible kickoff parle d'`AnalystAgent.process` ; la méthode
réelle est `AnalystAgent.run` (héritage `BaseAgent.run`).
Aucun helper interne — toute la construction du prompt vit
inline dans `run` plus un seul helper privé `_format_memories`.

`agents/analyst_agent.py` (intégral, 66 lignes) :

```python
# aria/agents/analyst_agent.py

from agents.base_agent import BaseAgent, AgentContext
from cognition.cognitive_context import LLM_ROLE_MAP, CognitiveOperation



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

Le PROMPT est une `f-string` avec 5 slots, formatée d'un coup
ligne 42-47. Aucun helper de second niveau pour la construction
du prompt — pas de `_build_system_prompt` ou équivalent à
préserver.

### 1.b — Origine du slot HISTORIQUE DE CETTE SESSION

Le slot est alimenté ligne 45 :

```python
session_memory=self._format_memories(ctx.session_memory),
```

`ctx.session_memory` est posé par `execution/routers/llm_router.py`,
ligne 145-149 dans `_run_pipeline` :

```python
session_memories = (
    self.mempalace_bridge.retrieve_by_intent(query=message, intent_id=intent.id)
    if intent
    else {"hits": [], "count": 0}
)
```

Puis ligne 172 :

```python
ctx = AgentContext(
    message=message,
    intent=intent,
    memories=memory_context.global_memories,
    session_memory=memory_context.session_memories,  # ← ici
    …
)
```

`retrieve_by_intent(query, intent_id, n=10)` est une recherche
**vectorielle** dans `wing=aria_episodic` filtrée sur
`room=intent_id` (`memory/mempalace_bridge.py:130-164`). Ce
n'est pas un historique conversationnel — c'est un recall
sémantique des souvenirs épisodiques pertinents pour la
requête courante, scopés à l'intent résolu.

`_format_memories` (`agents/analyst_agent.py:58-66`) prend
les 5 premiers hits, tronque chacun à 800 chars, et formate
en bullets `"- {text}"`. Si zéro hit, renvoie
`"Aucune mémoire disponible."`.

→ Le slot HISTORIQUE actuel **n'est ni chronologique ni
conversationnel**. C'est de la recall épisodique. Sa
suppression au sprint 17 (D4, §7) ne casse pas une fonction
existante : le retrieval épisodique sera toujours présent via
`context_block` (cf. §6).

### 1.c — Origine des slots CONTEXTE COGNITIF (intent, session, context_block)

Le slot `PROJET RÉCENT EN MÉMOIRE` (`{intent_name}`) provient
de `ctx.intent.name`, l'intent résolu par
`intent_engine.resolve` puis `intent_engine.apply`
(`execution/routers/llm_router.py:121-138`).

Le slot `CONTEXTE COGNITIF` (`{context_block}`) provient de
`ctx.extra["context_block"]`, posé ligne 156-163 :

```python
context_block = build_context_block(
    query=message,
    bridge=self.mempalace_bridge,
    active_intents=self.intent_engine.list_attention_active(),
    session_memories=session_memories,
    global_memories=global_memories,
)
```

`build_context_block` (`cognition/context_builder.py:25-92`,
93 lignes intégral) assemble trois sections sous budget tokens
2000 (par défaut) :

1. **`[Profil utilisateur stable]`** — faits sémantiques
   (`bridge.retrieve_semantic(query, n=5)`), priorité maximale.
2. **`[Projets actifs]`** — intents actifs triés par salience
   décroissante.
3. **`[Souvenirs pertinents]`** — épisodique : `session_memories`
   en priorité (filtré par `intent_id`), avec fallback
   `global_memories` si la session a < 3 hits, en excluant les
   doublons par `text`.

Le bloc `[Souvenirs pertinents]` peut donc contenir partiellement
les mêmes hits que ceux que `_format_memories` formate sous
slot HISTORIQUE. **Double alimentation depuis la même source**
(`session_memories`), avec formatages différents (préfixe
`-`, troncature 400 vs 800 chars, header différent). Confirmé
§6.a.

### 1.d — Inventaire des callers prod de `LLMRouter.complete`

Grep `\.complete(` sur le repo hors `venv`, `__pycache__`,
`tests/` :

| Fichier:ligne | Forme actuelle | Migration sprint 17 ? |
|---|---|---|
| `agents/analyst_agent.py:49` | `complete(prompt, role, temperature=0.3, max_tokens=800)` | **OUI** (cible exclusive) |
| `agents/planner_agent.py:44` | `complete(prompt, role=LLMRole.PLANNING, …)` | NON (legacy) |
| `agents/executor_agent.py:49` | `complete(prompt=…, role=LLMRole.CHAT, …)` | NON (legacy) |
| `agents/critic_agent.py:47` | `complete(prompt=…, role=LLMRole.CHAT, …)` | NON (legacy) |
| `cognition/cognitive_classifier.py:222` | `complete(prompt=…, role=LLMRole.CHAT, temperature=0.1, max_tokens=60)` | NON (legacy) |
| `llm/intent_namer.py:20` | `complete(prompt=…, role=LLMRole.CHAT, …)` | NON (legacy) |

→ **6 callers prod**, dont 2 manqués par l'audit sprint 16
(executor, critic). Seul Analyst migre au sprint 17 ;
les 5 autres restent en forme legacy `prompt=...`. Le router
sprint 16 supporte les deux formes côte à côte par xor strict
(`llm/llm_router.py:249-260`), aucune migration forcée.

Pas de caller via `LLMRouter.route()` (méthode inerte
identifiée sprint 16 §9.e — vestige hors-scope, dette
candidate #36).

─────────────────────────────────────────────────────────────────────────

## 2. Contrat exact des fonctions sprint 15 (Section 2 du brief)

### 2.a — `MempalaceBridge.load_conversation_history` (intégral)

`memory/mempalace_bridge.py:213-272` (intégral) :

```python
def load_conversation_history(
    self,
    conversation_key: str,
    n: int = 10,
) -> list[dict]:
    """
    Restitution chronologique (oldest → newest) des n derniers tours
    d'une conversation. Format prêt à être passé en `messages` au
    provider LLM au sprint 16.

    Lecture non-vectorielle : filtre metadata pur sur wing/room,
    puis tri Python sur metadata.timestamp. ChromaDB ne trie pas
    nativement sur .get() — c'est délibéré côté caller (cf. audit
    sprint 15 §5.3).

    Args:
        conversation_key : clé d'indexation de la conversation
                           (chat_id Telegram stringifié côté caller).
        n                : nombre maximum de tours retournés
                           (les plus récents). n<=0 → liste vide.

    Returns:
        liste de {"role": str, "content": str, "timestamp": str}
        triée par timestamp croissant. Liste vide si conversation
        inconnue ou n<=0.

    Raises:
        RuntimeError : si le bridge a été construit sans get_by_metadata
                       (injection optionnelle au constructeur).
    """
    if self._get_by_metadata is None:
        raise RuntimeError(
            "get_by_metadata callable required for conversation history; "
            "inject at construction"
        )

    if n <= 0:
        return []

    from config import config as _config

    where = {"$and": [
        {"wing": "aria_conversation"},
        {"room": conversation_key},
    ]}

    result = self._get_by_metadata(_config.mempalace_path, where) or {}
    docs = result.get("documents") or []
    metas = result.get("metadatas") or []

    turns = [
        {
            "role": (meta or {}).get("role", ""),
            "content": doc or "",
            "timestamp": (meta or {}).get("timestamp", ""),
        }
        for doc, meta in zip(docs, metas)
    ]
    turns.sort(key=lambda t: t["timestamp"])
    return turns[-n:]
```

**Contrat extrait** :

| Aspect | Valeur exacte |
|---|---|
| Signature | `(self, conversation_key: str, n: int = 10) -> list[dict]` |
| Param `n` | Borne SUPÉRIEURE — **les n DERNIERS tours**, pas une fenêtre depuis le début. `n<=0` → `[]` immédiatement |
| Unité de `n` | **MESSAGES**, pas turns (paires). Un slice `turns[-n:]` sur une liste de docs ChromaDB, chaque doc = un message. Mismatch avec le nom `config.max_history_turns` — cf. §5 |
| Ordre de la liste retournée | **Chronologique croissant** (oldest → newest), via `turns.sort(key=...)`. Garantie explicite |
| Clés du dict | `"role"`, `"content"`, `"timestamp"` — strictement ces trois, jamais d'autres |
| Type des valeurs | tous `str`. Si `meta` est `None`, `(meta or {})` protège — les valeurs absentes deviennent `""` |
| Conversation inconnue | Liste vide `[]` (pas d'exception). Le filtre `where` ne matchera rien |
| Bridge sans `get_by_metadata` | `RuntimeError` immédiate — pas de fallback silencieux |
| `_config.mempalace_path` | Lu au moment de l'appel, pas au constructeur (`from config import config as _config` intra-fonction) — permet de monkeypatch en test |
| Filtre ChromaDB | `{"$and": [{"wing": "aria_conversation"}, {"room": conversation_key}]}` |

Tests vérifiants existants (`tests/memory/test_mempalace_bridge_conversation.py`,
141 lignes vérifiées) : conversation inconnue → `[]`, ordre
chronologique préservé, cap à `n`, isolation par
`conversation_key`, RuntimeError si pas injecté. **Aucun test
ne vérifie le champ `role`** côté valeurs — il dépend de ce
que `write_conversation_turn` a effectivement écrit.

### 2.b — `write_conversation_turn` (intégral) et le risque de tour orphelin

`memory/writer.py:170-209` (intégral) :

```python
_ALLOWED_CONVERSATION_ROLES = {"user", "assistant"}


def write_conversation_turn(
    conversation_key: str,
    role: str,
    content: str,
    *,
    extra: dict | None = None,
) -> None:
    """
    Stocke un tour conversationnel dans aria_conversation.

    wing="aria_conversation" et room=conversation_key sont structurels
    et non overridables (invariant W4). role et timestamp sont en
    métadonnée pour permettre tri chronologique et filtrage par rôle
    côté lecture.

    role doit valoir "user" ou "assistant" — toute autre valeur déclenche
    ValueError (pas de "system" à ce stade ; cf. sprint 15 audit §arbitrage 2).
    """
    if role not in _ALLOWED_CONVERSATION_ROLES:
        raise ValueError(
            f"role must be one of {sorted(_ALLOWED_CONVERSATION_ROLES)} "
            f"(got {role!r})"
        )

    col = get_collection(config.mempalace_path)
    doc_id = uuid4().hex

    meta = {
        **(extra or {}),
        "wing": "aria_conversation",
        "room": conversation_key,
        "type": "conversation_turn",
        "timestamp": _now_iso(),
        "role": role,
    }
    _validate(meta)
    col.upsert(documents=[content], ids=[doc_id], metadatas=[meta])
```

**Contrat extrait** :

- **Une écriture par message**, pas par paire user+assistant.
  Pour persister un tour complet, le caller fait DEUX appels :
  `write_conversation_turn(key, "user", msg)` puis
  `write_conversation_turn(key, "assistant", reply)`.
- `role` validé strict — `"user"` ou `"assistant"` uniquement.
  `"system"` rejeté avec `ValueError`. Décision sprint 15
  §arbitrage 2.
- `doc_id = uuid4().hex` — **pas d'idempotence** (contrairement
  à `write_interaction` qui utilise `_idempotent_doc_id`).
  Deux appels identiques produisent deux entrées distinctes.
- `wing/room/type` posés APRÈS spread `extra` (invariant W4).

**Appelée à quel moment dans le cycle process actuel ?**
**Nulle part en prod**. Constat C2 (§0.2). L'écriture mémoire
effective d'un tour reste `write_interaction` dans
`execution/routers/llm_router.py:212-217`, qui écrit UN seul
document concaténé `f"USER:\n{message}\n\nARIA:\n{result}"` sous
`wing=aria_episodic` après résolution complète de la réponse
LLM.

**Risque de tour orphelin si on câble naïvement au sprint 17** :
le pattern "deux appels successifs" expose à un trou si un
crash survient entre les deux. Trois schémas possibles, analysés
§7 (D5).

### 2.c — Compatibilité des rôles avec la validation router sprint 16

`memory/writer.py:170` : `_ALLOWED_CONVERSATION_ROLES = {"user", "assistant"}`.
Strict. Aucun rôle tiers possible côté écriture.

`llm/llm_router.py:215` : `valid_roles = {"user", "assistant", "system"}`.
La validation router accepte un sur-ensemble. **Strictement
compatible** : tout ce qui sort de `load_conversation_history`
passe `_validate_messages` sans risque.

Cas de bord à noter : si le palace contient des entrées
résiduelles avec un `meta.role` ne valant ni `"user"` ni
`"assistant"` (par exemple une migration future ou une
contamination cross-wing accidentelle), `load_conversation_history`
les retournera quand même (la lecture ne filtre pas par rôle).
Aujourd'hui non-sujet — la wing est vide. Mais à `n` non
borné par `role`, on a une ligne de défense supplémentaire à
envisager côté caller pour sprint 18+ (pas dans le périmètre
sprint 17). Dette adjacente §8.

─────────────────────────────────────────────────────────────────────────

## 3. Origine de `chat_id` dans le contexte cognitif (Section 3 du brief)

### 3.a — Flux Event → CognitiveContext → AnalystAgent

**Production** :

```
TelegramInterface._handle_message:62-71
  ├─ chat_id = update.effective_chat.id        # int natif Telegram
  └─ Event.create(metadata={"chat_id": chat_id}, …)
       │
       ▼
core/kernel.py:handle_event:135-156
  ├─ event passé tel quel à cognitive_engine.classify(event)
  └─ ExecutionOperation construit avec :
       payload.metadata = {**event.metadata, "interrogative": ...}
       op.metadata      = event.metadata
       │
       ▼
execution_dispatcher.dispatch(exec_op)
  → LLMExecutionRouter.execute(payload)
       │
       ▼
LLMExecutionRouter._run_pipeline:165-182
  └─ AgentContext(
       …,
       extra={
         "context_block": …,
         "memory_context": …,
         …,
         "cognitive_operation": operation,
         **metadata,           # ← chat_id ici
       },
     )
```

→ Côté agent, le `chat_id` vit dans `ctx.extra["chat_id"]`. Il
n'est PAS exposé via `ctx.event` (l'AgentContext n'a pas de
champ `event`, cf. `agents/base_agent.py:14-43`).

**Type** : `int` natif (`update.effective_chat.id` est un
entier 64 bits). Posé tel quel en metadata, **pas stringifié**
au transport. Le caller sprint 17 doit donc faire
`str(ctx.extra["chat_id"])` au moment de construire
`conversation_key`. Cohérent avec la décision sprint 15 §7.2
(le store voit `conversation_key: str`, le caller mappe).

### 3.b — Disponibilité sur tous les chemins atteignant AnalystAgent

Recensement des chemins menant à AnalystAgent (via
`AgentController.run`) :

| Chemin | EventType | `chat_id` présent ? |
|---|---|---|
| TEXT standard | `EventType.TEXT` | OUI — `_handle_message:70` pose `metadata={"chat_id": chat_id}` |
| Caption interrogative sur image (mode enrichi) | `EventType.IMAGE` → `ImageExecutionRouter._handle_input_enriched:178-182` → `LLMExecutionRouter.execute({"metadata": payload.get("metadata", {})})` | OUI — `metadata` propagée intacte depuis `_handle_photo:105` |
| VOICE, FILE, SYSTEM | aucune interface ne les produit aujourd'hui | N/A |

Les deux chemins atteignant AnalystAgent transportent
`chat_id` de bout en bout. **Pas de cas où Analyst recevrait
un ctx sans chat_id en prod.** Pour les tests, une fixture
explicite devra le poser (cf. §8 dettes adjacentes — pas
forcément trivial pour tous les tests existants).

### 3.c — Arbitrage : accès direct ou helper ?

Trois options :

| Option | Coût | Réutilisabilité | Couplage |
|---|---|---|---|
| **A — accès direct** : `key = str(ctx.extra.get("chat_id", "default"))` inline dans Analyst | Quasi-nul (une ligne) | Faible — chaque caller futur duplique | Très faible — pas de nouveau symbole |
| **B — helper property sur AgentContext** : `ctx.conversation_key` | Moyen (modif `base_agent.py`, AgentContext + tests existants à ajuster) | Forte — n'importe quel agent y accède | Modéré — AgentContext devient conscient du concept "conversation" |
| **C — helper module-level** : `from agents._context_keys import conversation_key_of(ctx)` | Faible (nouveau module mince) | Moyenne — un import à connaître | Faible |

Le calibrage CLAUDE.md (sprint perso, exigence faible, "le
moins exigeant entre deux niveaux") pointe vers **A**. Pas
d'autre caller prévu à court terme (les 5 callers legacy
n'ont pas besoin du `conversation_key` — ils ne lisent pas
d'historique). Si sprint 18 amène un second consommateur,
on factorisera à ce moment-là.

**Arbitrage proposé : Option A** — accès direct
`str(ctx.extra.get("chat_id", "default"))` dans
`AnalystAgent.run`. Repli `"default"` pour les tests qui
n'instrumentent pas `chat_id` ; en prod, le chemin Telegram
le pose toujours.

Voir D1 §7.

─────────────────────────────────────────────────────────────────────────

## 4. Source des constantes d'identité côté caller (Section 4 du brief)

### 4.a — Définitions actuelles dans le router

`llm/llm_router.py:13-26` :

```python
from pathlib import Path

def _load_soul() -> str:
    path = Path(config.soul_path)
    if path.exists():
        return path.read_text().strip()
    return "Tu es Aria, un assistant cognitif personnel."

def _load_user() -> str:
    path = Path(config.user_path)
    if path.exists():
        return path.read_text().strip()
    return ""

_SOUL = _load_soul()
_USER = _load_user()
```

Chargement au **module-load**, une seule fois. `_SOUL`
non-vide garanti (fallback string si fichier absent). `_USER`
peut être chaîne vide si fichier absent.

Composition actuelle en forme **legacy** (`_call` lignes
320-326) :

```python
system_parts = [_SOUL]
if _USER:
    system_parts.append(f"\n\nPROFIL UTILISATEUR :\n{_USER}")
system_prompt = "\n".join(system_parts)
```

→ Le system prompt actuel est `_SOUL + "\n" + "\n\nPROFIL UTILISATEUR :\n" + _USER`
si `_USER` non vide, sinon `_SOUL` seul.

Vérification fichiers prod : `soul.md` (1466 octets, 28 lignes,
mtime 31 mars 23:54), `user.md` (326 octets, 6 lignes, mtime
1 avril 00:05). `_USER` est donc non-vide en prod, le path
"`_SOUL` seul" est inerte aujourd'hui mais existe.

### 4.b — Trois options pour la reconstitution côté caller

| Option | Description | Avantages | Inconvénients |
|---|---|---|---|
| **(i) Import direct des constantes privées** : `from llm.llm_router import _SOUL, _USER` | Le caller importe les symboles `_`-prefixed | Zéro duplication. Source de vérité unique. Trivial à écrire | Couplage à un détail d'implémentation. Renommage du symbole côté router casse le caller. Convention `_` viole l'encapsulation Python |
| **(ii) Helper public sur LLMRouter** : `LLMRouter.build_base_system_prompt() -> str` (méthode classmethod ou statique) | Le caller appelle un point d'entrée explicite | Source de vérité unique. API publique stable. Le router peut faire évoluer la composition interne (ex. ajout d'un troisième fichier) sans casser les callers | Léger ajout de surface API. Le caller doit instancier ou importer la classe |
| **(iii) Lecture indépendante depuis le caller** | Le caller relit `config.soul_path` / `config.user_path` lui-même | Découplage complet. L'agent peut sciemment diverger (ex. ne pas inclure `_USER` pour une opération META_MEMORY) | Duplication de logique (deux endroits qui lisent les mêmes fichiers, deux fallbacks à maintenir). Risque de drift silencieux si l'un évolue sans l'autre |

### 4.c — Composition finale du system prompt côté caller

L'objectif d'équivalence stricte avec le comportement legacy
exige :

```
<SOUL>
<saut de ligne>
<saut de ligne>PROFIL UTILISATEUR :
<USER>
<saut de ligne>
<CONTEXTE COGNITIF — bloc reconstruit>
```

Détail des séparateurs côté legacy :
- `system_parts = [_SOUL]`
- `system_parts.append(f"\n\nPROFIL UTILISATEUR :\n{_USER}")`
- `"\n".join(system_parts)` → produit `_SOUL + "\n\n\nPROFIL UTILISATEUR :\n" + _USER` (le `\n\n` du prepend + le `\n` du join = trois `\n`).

Subtilité : trois `\n` consécutifs entre `_SOUL` et `PROFIL UTILISATEUR`. C'est le comportement actuel — si on veut l'équivalence stricte, c'est ce qu'il faut reproduire.

Côté caller sprint 17, l'ordre des blocs proposé est :

1. **Identité** : `_SOUL` + `\n\n\nPROFIL UTILISATEUR :\n` + `_USER` (équivalent strict legacy)
2. **CONTEXTE COGNITIF** : le `context_block` injecté en suffixe (séparateur `\n\n` puis header explicite, ex. `\n\nCONTEXTE COGNITIF :\n{context_block}`)
3. **PROJET RÉCENT EN MÉMOIRE** : `\n\nPROJET RÉCENT EN MÉMOIRE :\n{intent_name}`
4. **RÈGLES** : le bloc règles existant (avec les ancres du test garde-fou — "quel que soit le sujet" notamment)

Ordre justifié : identité d'abord (SOUL + USER) car ce sont
les couches les plus stables ; CONTEXTE puis PROJET RÉCENT
ensuite (méta-information sur le tour) ; RÈGLES en queue
(les modèles tendent à suivre les dernières instructions du
system avec plus de fidélité).

**Position d'audit** : Option (ii) — helper public sur
`LLMRouter`. Raisons :

- Préserve la source de vérité unique (constat partagé avec
  l'architecte).
- Évite l'import de symboles `_`-prefixed côté agent (signal
  d'encapsulation respectée).
- L'agent ne duplique pas la logique d'init (chemin fichier,
  fallback, jointure). Si demain `config.soul_path` devient
  une URL ou un secret manager, le router gère seul.
- Surface API minime — une seule classmethod statique sans
  dépendance d'instance.

L'option (i) reste acceptable comme repli si on veut zéro
modification du router au sprint 17. Mais cf. constat C1 :
on doit déjà modifier `core/kernel.py:111`, donc l'intouchable
"pas de modification de LLMRouter" du kickoff §"Hors-scope
strict" est déjà détendu. Une classmethod ajoutée est moins
risquée qu'une lecture intra-agent.

L'option (iii) est écartée par YAGNI — la divergence de
composition par agent n'est pas un besoin documenté.

Voir D6 §7.

─────────────────────────────────────────────────────────────────────────

## 5. Sémantique de `config.max_history_turns` (Section 5 du brief)

### 5.a — Unité réellement attendue par `load_conversation_history`

`load_conversation_history(conversation_key, n)` retourne au
plus `n` **MESSAGES** (cf. §2.a, ligne `return turns[-n:]` sur
une liste où chaque doc = un message).

→ Avec `n=10`, on récupère 10 messages, soit 5 tours
user+assistant en moyenne, ou 10 messages d'un même rôle dans
des cas pathologiques (par exemple si l'écriture user a échoué
côté assistant N fois de suite).

### 5.b — Mismatch sémantique avec `config.max_history_turns`

`config.py:67` : `max_history_turns: int = 10`.

Le nom **`turns`** suggère paires (un turn = un échange
user+assistant). Le paramètre store accepte **messages**. Si
on appelle naïvement `bridge.load_conversation_history(key, n=config.max_history_turns)`,
on charge en pratique 10 messages = ~5 turns, soit la moitié
de ce que le nom évoque.

Correspondance proposée pour l'appel sprint 17 :

```python
limit = config.max_history_turns * 2
history = bridge.load_conversation_history(key, n=limit)
```

Cohérent avec le nom (10 turns = 20 messages au plus) tant
qu'on respecte le contrat "1 turn = 1 user + 1 assistant".
Sur des conversations naissantes (premier tour partiel),
`n=20` sur 1 message renvoie 1 message — OK.

### 5.c — Dette confirmée, pas de modification au sprint 17

`config.max_history_turns` est dead config jusqu'à ce sprint
(grep exhaustif §sprint15 §3, confirmé : un seul match dans
tout le repo). Le sprint 17 va l'utiliser pour la première
fois.

Renommer en `max_history_messages` serait plus honnête, mais :
1. Hors-scope strict du kickoff sprint 17.
2. Touche `config.py` (couche transverse).
3. Risque de casser un futur consommateur qui aurait pris
   `max_history_turns` comme nom durable.

→ Dette **#37 candidate** à ouvrir en clôture sprint 17 :
soit renommer en `max_history_messages`, soit conserver le
nom et documenter explicitement la convention "messages = N×2
turns" dans le docstring. Sprint 18 (cleanup) tranchera.

Voir D7 §7.

─────────────────────────────────────────────────────────────────────────

## 6. Non-redondance avec CONTEXTE COGNITIF (Section 6 du brief)

### 6.a — `session_memory` et `context_block` citent-ils du contenu conversationnel ?

**`session_memory` (le slot HISTORIQUE actuel)** : alimenté
par `retrieve_by_intent(query=message, intent_id=intent.id)`
(`execution/routers/llm_router.py:146`). Lecture vectorielle
dans `wing=aria_episodic`, scope `room=intent_id`.

Or `aria_episodic` contient les entrées de `write_interaction`,
qui écrit aujourd'hui le tour complet en concaténation
`f"USER:\n{message}\n\nARIA:\n{result}"`. **Donc `session_memory`
PEUT contenir, sous forme de bullet text, des morceaux
verbatim de messages d'échanges passés**, à condition que le
recall vectoriel les remonte (dépend de la similarité du
`query=message` courant avec les souvenirs stockés).

C'est de la **redondance partielle, par recall sémantique**.
Pas un historique chronologique exhaustif.

**`context_block`** : alimenté par `build_context_block`
(`cognition/context_builder.py`). Sa section `[Souvenirs pertinents]`
puise dans les **mêmes** `session_memories` (cf. §1.c), plus
en fallback les `global_memories`. Tronqué à 400 chars/hit
(au lieu de 800 dans `_format_memories`).

Donc :

- **`session_memory` ⊆ source `aria_episodic` filtré par
  intent_id** → contient des fragments de messages passés
  textuels via `write_interaction`.
- **`context_block.[Souvenirs pertinents]` ⊆ source `aria_episodic`
  (session_memories prioritaire + global_memories fallback)**
  → contient les mêmes fragments avec une troncature
  différente.
- **Aucun de ces deux slots ne lit `wing=aria_conversation`**.
  La wing dédiée à l'historique chronologique reste vide
  aujourd'hui (cf. C2).

### 6.b — Risque de double comptage post-sprint 17

Au sprint 17, on ajoute un **troisième** canal qui transporte
de l'historique : la liste `messages=[{role, content}, ...]`
construite depuis `load_conversation_history`.

| Canal | Source palace | Format | Granularité |
|---|---|---|---|
| (existant) `context_block.[Souvenirs pertinents]` | `aria_episodic` (recall vectoriel) | bullets texte, troncature 400 chars | hits sémantiques pertinents, max 5 |
| (à supprimer) slot HISTORIQUE via `_format_memories(session_memory)` | `aria_episodic` (recall vectoriel par intent) | bullets texte, troncature 800 chars | 5 hits scopés intent |
| (à introduire) `messages=[…]` natif | `aria_conversation` (lecture chronologique) | `{role, content}` natif provider | 10 turns = ~20 messages |

→ Si le sprint 17 supprime le slot HISTORIQUE comme prévu et
qu'on câble correctement l'écriture conversationnelle (C2),
on obtient :

- (a) `context_block` continue de citer du contenu épisodique
  recall-pertinent (souvenirs scopés à la requête, parfois
  vieux de plusieurs sessions).
- (b) `messages` natifs portent l'historique chronologique
  récent de la conversation Telegram en cours.

**Risque de double comptage** : si un échange récent (présent
dans `aria_conversation`) est aussi pertinent sémantiquement
(via `aria_episodic`), il peut apparaître **dans les deux
canaux**, formaté différemment. Le LLM le verra deux fois.

Atténuation immédiate : aucune. Le coût en tokens reste borné
(`context_block` budgeté à 2000 tokens), le risque de "drift
silencieux" est faible (la double présence renforce plutôt
qu'elle ne contredit).

Dette à ouvrir en clôture sprint 17 (dette #38 candidate) :
- Soit ne plus écrire les tours dans `aria_episodic` (assumer
  que `aria_conversation` est suffisant et que l'épisodique
  doit être réservé aux faits durables → mais ça casse
  l'intent recall qui dépend de l'épisodique scopé par
  `intent_id`).
- Soit dédupliquer côté `build_context_block` en filtrant les
  hits dont le timestamp tombe dans la fenêtre déjà couverte
  par `load_conversation_history`.
- Soit assumer la redondance et ne rien faire (sprint 17 cible
  uniquement la perte du contexte multi-tour, pas l'optimisation
  des tokens system).

Position d'audit : **assumer pour sprint 17, instruire la dette
sprint 18**.

### 6.c — `CONTEXTE COGNITIF` reste dans le system prompt

Conclusion §6.b : `context_block` n'est pas un message
conversationnel et reste légitime en system prompt
(méta-info sur le tour, profil stable, intents actifs,
souvenirs sémantiquement liés). Pas de bascule vers le user
message.

→ Position architecte du kickoff (§"Décisions à trancher au
tour 1" point 3) confirmée sans réserve.

Voir D3 §7.

─────────────────────────────────────────────────────────────────────────

## 7. Synthèse arbitrages — tableau des 8 décisions

| #  | Décision                                                                                 | Choix retenu                                                                                                                                                                                       | Alternative écartée                                                  | Raison principale                                                                                                                                          |
|----|------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D1 | Source de `conversation_key`                                                             | `str(ctx.extra.get("chat_id", "default"))` — accès direct, inline dans `AnalystAgent.run`                                                                                                          | Property/helper sur `AgentContext` ou module dédié                   | Calibrage CLAUDE.md (le moins exigeant entre deux). Aucun deuxième consommateur prévu. YAGNI                                                              |
| D2 | Où vit la construction du system prompt                                                  | Helper privé `_build_system_prompt(self, ctx)` dans `AnalystAgent` (méthode statique ou d'instance)                                                                                                | Module séparé `agents/_system_prompt.py` ; inline dans `run`         | Inline alourdit `run` qui devient illisible. Module séparé prématuré (un seul caller). Méthode privée = scope précis, testable isolément                  |
| D3 | Slot `CONTEXTE COGNITIF` : system ou user ?                                              | **System prompt** — préservé, en suffixe identité (cf. §4.c composition)                                                                                                                            | Bascule en premier user message                                      | C'est une méta-info de tour (profil + intents + souvenirs sémantiques pertinents), pas un message conversationnel. Cohérent avec sa nature actuelle        |
| D4 | Profondeur et format du chargement                                                       | `bridge.load_conversation_history(conv_key, n=config.max_history_turns * 2)`, format `[{role, content, timestamp}, ...]`. Le caller drop `timestamp` à la conversion en messages provider          | n=10 brut (= 10 messages = ~5 turns)                                 | Aligne sémantique avec le nom `turns`. Le router sprint 16 ignore `timestamp` de toute façon (cf. `_validate_messages` exige `role` + `content`)          |
| D5 | Écriture du tour courant — **schéma**                                                   | **Câbler `write_conversation_turn` au sprint 17** dans `LLMExecutionRouter`, schéma "deux appels groupés post-LLM" : user et assistant écrits ensemble juste après résolution `ctx.result`        | Laisser inerte (contredit C2) ; ou append user en pré-LLM, assistant en post-LLM | C2 documente l'inertie actuelle. Le post-LLM groupé évite l'orphelin sans atomicité ChromaDB. Le tour T est dans `messages` du tour T (user courant), pas dans le palace |
| D6 | Source des constantes `_SOUL` / `_USER`                                                  | Option (ii) — **helper public `LLMRouter.build_base_system_prompt()` (classmethod)**                                                                                                                 | (i) import direct des `_`-prefixed ; (iii) relecture indépendante     | Source de vérité unique. Pas de couplage à un symbole privé. Pas de duplication de logique de chargement                                                  |
| D7 | Sémantique `config.max_history_turns`                                                    | **Convention "messages = turns × 2"**, documentée dans le caller. **Pas de renommage** au sprint 17                                                                                                | Renommer en `max_history_messages` immédiatement                     | Renommage hors-scope kickoff. Couche transverse touchée. Dette #37 candidate à instruire sprint 18                                                        |
| D8 | Composition exacte du system prompt                                                      | `<SOUL>\n\n\nPROFIL UTILISATEUR :\n<USER>\n\nCONTEXTE COGNITIF :\n<context_block>\n\nPROJET RÉCENT EN MÉMOIRE :\n<intent_name>\n\n<RÈGLES préservées avec ancres garde-fou>` (cf. §4.c)                | Toute autre permutation, ou suppression de `PROFIL UTILISATEUR :`     | Équivalence stricte avec composition legacy `_call` + ajout du contexte cognitif sans casser le test garde-fou `tests/agents/test_analyst_prompt_guard.py` |

**Constats critiques C1 et C2 — implication directe sur D5 et hors-scope du kickoff**

Le tour 2 doit donc toucher (au-delà de `agents/analyst_agent.py`) :

- `core/kernel.py:108-112` — injecter `get_by_metadata` dans la
  construction du `MempalaceBridge` (1 ligne)
- `llm/llm_router.py` — ajouter `LLMRouter.build_base_system_prompt()`
  classmethod (~6 lignes, sans toucher `_SOUL` ni `_USER`)
- `execution/routers/llm_router.py:198-227` — ajouter deux
  appels `write_conversation_turn` (user + assistant)
  juste après l'écriture épisodique existante. Ne supprime
  PAS `write_interaction` (l'épisodique scopé par `intent_id`
  reste utile pour l'intent recall — cf. C4 et §6.b)

Volume diff estimé tour 2 :

| Fichier | Lignes touchées approx |
|---|---|
| `agents/analyst_agent.py` | ~50 (refactor `run` + `_build_system_prompt`, mais PROMPT constant reformaté) |
| `llm/llm_router.py` | +6 (classmethod) |
| `core/kernel.py` | +1 (injection `get_by_metadata`) |
| `execution/routers/llm_router.py` | +10 (deux `write_conversation_turn` + try/except) |
| Tests : `tests/agents/test_analyst_messages_form.py` (nouveau) | ~80 |
| Tests : fixture extension `conftest.py` éventuelle | ~10 |

Total ~150 lignes diff, à l'intérieur du calibrage sprint
exigence faible.

─────────────────────────────────────────────────────────────────────────

## 8. Dettes adjacentes notées (NON traitées dans le sprint)

Conformément à CLAUDE.md §"Résiste au scope creep" :

### 8.1 — Dette #36 candidate (déjà identifiée sprint 16)

`LLMRouter.route()` (`llm/llm_router.py:423-442`) inerte, non
appelée nulle part en prod. À ouvrir formellement en clôture
sprint 17 ou sprint 18.

### 8.2 — Dette #37 candidate (issue de §5.c)

`config.max_history_turns` nom trompeur (turns vs messages).
À renommer en `max_history_messages` ou documenter la
convention "limit = turns × 2" en commentaire `config.py`.
Sprint 18 cleanup.

### 8.3 — Dette #38 candidate (issue de §6.b)

Double comptage potentiel entre `messages` natif (depuis
`aria_conversation`) et `context_block.[Souvenirs pertinents]`
(depuis `aria_episodic` recall). Soit dédup, soit assumer.
Décision sprint 18 selon observation prod.

### 8.4 — Sprint 16 audit incomplet (constat C3)

`docs/sprint16/audit_llm_router.md` §3.a liste 4 callers prod
de `complete`, il en manque 2 (`executor_agent.py:49`,
`critic_agent.py:47`). Pas de conséquence opérationnelle sur
sprint 17 (les deux restent en forme legacy comme les 3 autres
callers non migrés), mais à corriger dans la doc d'audit
sprint 16 pour traçabilité. Édition rétroactive d'un audit
clos = à arbitrer (édition mineure d'un §" 3.a" pour ajouter
deux lignes au tableau, sans toucher aux verdicts).

### 8.5 — `Event.conversation_id` toujours dead

Sprint 15 audit §2 et sprint 14 plan ont déjà documenté la
dette. Reportée. Sprint 17 confirme : pas de promotion. À
supprimer sprint 18 si on assume `chat_id` brut indéfiniment.

### 8.6 — Filtrage rôle côté load (issue de §2.c)

`load_conversation_history` ne filtre pas par `role` à la
lecture. Si un jour le palace contient des entrées avec
`meta.role ∉ {"user", "assistant"}` (migration, contamination),
elles remonteraient au caller et seraient passées au router,
qui rejetterait avec `ValueError` via `_validate_messages`.
Aujourd'hui non-sujet (wing vide). Dette à instruire sprint 18+.

### 8.7 — Fixtures de test sans `chat_id`

Aucun test ne consomme aujourd'hui `ctx.extra["chat_id"]`.
Les tests qui construisent un `AgentContext` directement
(par exemple `tests/execution/test_pipeline_memory_isolation.py:69-71`)
n'ont pas besoin de le poser. **Mais le test fixture mock du
sprint 17 devra le faire** pour valider le passage
`conversation_key → bridge.load_conversation_history`. Petit
ajout sans dette, mentionné pour traçabilité.

─────────────────────────────────────────────────────────────────────────

## 9. Cohérence avec règles inviolables CLAUDE.md

Vérification §"Règles d'architecture INVIOLABLES" :

1. ✅ **Un seul point d'écriture mémoire (writer.py)** —
   l'écriture conversationnelle ajoutée (D5) passe par
   `write_conversation_turn` existant dans `memory/writer.py`.
   Pas de nouvelle voie.
2. ✅ **Une lecture mémoire passe par bridge** —
   `load_conversation_history` est sur `MempalaceBridge`. Pas
   d'import `mempalace_store` côté agent.
3. ✅ **Agents reçoivent AgentContext pré-assemblé, ne font
   AUCUNE requête mémoire** — l'audit propose que c'est le
   **kernel** (en l'occurrence `LLMExecutionRouter`) qui
   appellera `bridge.load_conversation_history` et passera la
   liste dans `ctx.extra` (ou similaire). L'agent ne fera PAS
   l'appel bridge lui-même. **Point à confirmer en arbitrage
   D2** : où exactement vit l'appel `load_conversation_history` ?
   Position audit : dans `LLMExecutionRouter._run_pipeline`
   entre la résolution intent et la construction de
   `AgentContext`, posé en `ctx.extra["conversation_history"]`.
   L'agent y accède en lecture pure.
4. ✅ **Routers retournent `{"text"}` / `{"path", "caption"}`** —
   non touché.
5. ✅ **Kernel séquence, ne décide pas** — non touché.
6. ✅ **CognitiveEngine ne fait pas de retrieval direct** —
   non touché.

Précision sur le point 3 : la sémantique stricte CLAUDE.md
est que **les agents ne requêtent pas la mémoire** —
`LLMExecutionRouter` est techniquement un router d'exécution
(pas un agent au sens `BaseAgent`), il a déjà accès direct au
`mempalace_bridge` (constructeur ligne 62-66). L'appel
`load_conversation_history` côté router est donc conforme. Si
on plaçait l'appel dans `AnalystAgent.run`, on violerait la
règle 3. **D2 implique donc nécessairement que l'appel
bridge vit côté `LLMExecutionRouter`**, pas côté agent.

─────────────────────────────────────────────────────────────────────────

## 10. Critères de fin tour 1

- [x] Section 1 : caller actuel cartographié intégralement (§1).
- [x] Section 2 : contrats `load_conversation_history` et
  `write_conversation_turn` cités intégralement (§2).
- [x] Section 3 : flux `chat_id` tracé bout-en-bout (§3).
- [x] Section 4 : trois options _SOUL/_USER analysées,
  composition cible définie (§4).
- [x] Section 5 : mismatch `max_history_turns` confirmé (§5).
- [x] Section 6 : redondance `context_block` analysée (§6).
- [x] Section 7 : 8 décisions arbitrées en tableau (§7).
- [x] Constats critiques C1, C2, C3, C4 remontés (§0).
- [x] Dettes adjacentes notées hors-scope (§8).
- [x] Cohérence règles inviolables vérifiée (§9).

**Critères tour 1 atteints.** Validation architecte requise
sur :

- les huit décisions D1–D8 (§7),
- la prise en compte des constats critiques C1 (modification
  ponctuelle `core/kernel.py`) et C2 (élargissement du périmètre
  à `execution/routers/llm_router.py` pour câbler l'écriture
  conversationnelle).

Si ces deux élargissements de périmètre sont rejetés
explicitement par l'architecte, deux scénarios alternatifs
existent :

- **Scénario dégradé A** : on câble la lecture seule, en sachant
  que `load_conversation_history` lèvera RuntimeError en prod
  (C1) → le sprint 17 livrerait une régression évidente. Non
  recommandé.
- **Scénario dégradé B** : on câble la lecture en injectant
  `get_by_metadata` mais sans écriture conversationnelle (C2
  laissé en l'état) → `load` renverra toujours `[]`, ARIA
  appelera le router avec `messages=[system, user_courant]`
  sans historique, comportement strictement identique à
  aujourd'hui sauf qu'on a perdu le slot HISTORIQUE (qui même
  s'il portait un misnomer, contenait du recall épisodique
  utile). **Régression nette du contexte**. Non recommandé.

L'audit recommande explicitement le scénario nominal
(D1–D8 + C1 + C2 traités ensemble dans le tour 2).

─────────────────────────────────────────────────────────────────────────
