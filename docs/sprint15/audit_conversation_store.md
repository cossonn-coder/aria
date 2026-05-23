─────────────────────────────────────────────────────────────────────────
ARIA — Sprint 15, tour 1 : audit cartographique conversation store
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-23
**Branche** : `feat/sprint15-conversation-store`
**Cadre** : tour 1 du sprint 15 (A1 — store conversationnel).
  Audit pur, aucun code écrit. Tranche les deux décisions
  flaggées par le plan sprint 14 §3 et le kickoff sprint 15
  §"Décisions à trancher au tour 1".

─────────────────────────────────────────────────────────────────────────

## 0. Synthèse exécutive (à lire en premier)

1. **Cartographie écriture mémoire** : 4 fonctions dans
   `memory/writer.py` (`write_interaction`, `write_image_artifact`,
   `write_semantic_fact`, `write_classifier_cache`), toutes posent
   `wing/room/type` après spread `extra` (invariant W4 sprint 3.1).
   Le `MempalaceBridge` est strictement lecture-only — il n'expose
   aucune méthode d'écriture aujourd'hui. Écritures = `writer.py`
   appelé directement par les callers.
2. **Wings = metadata, pas collections** : il n'existe AUCUNE
   "registration de wing" dans le codebase ARIA ni dans le fork
   mempalace. `get_collection(palace_path)` retourne UNE seule
   collection (`mempalace_drawers` par défaut, configurée via
   `get_configured_collection_name()`). Le champ `wing` est posé
   en metadata par les writers, et `mempalace.searcher.search()`
   filtre via `build_where_filter(wing, room)` qui produit un
   filtre ChromaDB standard. Conséquence directe : **créer la
   wing `aria_conversation` = écrire avec `wing="aria_conversation"`,
   point**. Aucune migration palace, aucun appel d'init, aucune
   registration séparée. Le brief sprint 15 (kickoff §"Livrable
   principal") mentionne "Création de la wing aria_conversation
   dans MemPalace (registration équivalente aux wings existantes)" :
   à reformuler en "écriture sous metadata wing=aria_conversation",
   il n'y a rien d'autre à faire.
3. **`Event.conversation_id` confirmé dead** : déclaré
   `Optional[str] = None` à `core/event.py:24`, **zéro caller**
   (grep exhaustif, hors la déclaration). `Event.create()`
   n'accepte pas le paramètre, `TelegramInterface` ne le
   populerait pas s'il était accepté. Sprint 14 §6 confirmé sans
   réserve.
4. **`config.max_history_turns=10` confirmé dead** : déclaré à
   `config.py:67`, **zéro caller** ailleurs. Sprint 14 §6
   confirmé.
5. **`chat_id` Telegram déjà transporté bout en bout** : extrait
   dans `_handle_message:63` et `_handle_photo:86` via
   `update.effective_chat.id`, posé dans `Event.metadata["chat_id"]`,
   propagé par le kernel dans `ExecutionOperation.payload.metadata`
   ET `ExecutionOperation.metadata`. Disponible côté routeurs
   d'exécution sans aucune modification de signature.
6. **Arbitrage 1 (clé d'indexation)** : **recommandation
   `chat_id` brut**. Détails §7. Stocké côté store sous nom
   générique `conversation_key: str` (le store ne connaît pas
   le transport).
7. **Arbitrage 2 (format turn)** : **recommandation structure
   `role/content` séparée**, alignée sur la recommandation
   architecte. Détails §8. ChromaDB supporte proprement le
   filtrage par metadata + tri Python post-récupération sur
   `metadata.timestamp` (cf. `_expand_with_neighbors:218` qui
   utilise déjà `col.get(where=...)`).
8. **Note architecturale** : le brief demande d'ajouter
   `write_conversation_turn` et `load_conversation_history` sur
   `MempalaceBridge`. C'est une **inflexion** — le bridge devient
   lecture+écriture, alors qu'il était strictement lecture-only
   (cf. son docstring §"Architecture" et §"Responsabilités").
   Trois options listées §9, recommandation §9.4.

─────────────────────────────────────────────────────────────────────────

## 1. Cartographie de l'écriture mémoire actuelle

### 1.1 `memory/writer.py` — point d'écriture unique

Fichier intégral (208 lignes) examiné. Quatre fonctions publiques :

| Fonction                    | Wing posée         | Room posée         | Type posé           | Doc id stratégie                                |
|-----------------------------|--------------------|--------------------|---------------------|------------------------------------------------|
| `write_interaction`         | `aria_episodic`    | `intent_id`        | `interaction`       | `_idempotent_doc_id(text, intent_id)` — fenêtre 60s |
| `write_image_artifact`      | `aria_episodic`    | `intent_id` ou `general` | `image_input` ou `image_generated` | `{type}_{uuid4().hex[:8]}`                      |
| `write_semantic_fact`       | `aria_semantic`    | `subject`          | `semantic_fact`     | `semantic_{subject}_{uuid4().hex[:8]}`         |
| `write_classifier_cache`    | `aria_classifier`  | `operation`        | `classifier_cache`  | `_idempotent_doc_id(message, "classifier_cache")` |

**Invariant W4 (sprint 3.1 / dette #11)** posé dans chaque fonction
qui accepte `extra` :

```python
meta = {
    **(extra or {}),
    "wing": "aria_episodic",   # ← après le spread, écrase tout
    "room": intent_id,
    "type": "interaction",
    ...
}
```

`_validate(meta)` vérifie la présence des trois champs structurels.
Test garde-fou : `tests/memory/test_writer.py:test_write_interaction_extra_cannot_override_wing`.

### 1.2 `memory/mempalace_bridge.py` — lecture seule

Fichier intégral (199 lignes) examiné. **Aucune méthode d'écriture.**

Trois méthodes publiques, toutes en lecture :

| Méthode              | Wing                  | Usage                                                        |
|----------------------|-----------------------|--------------------------------------------------------------|
| `retrieve_memories`  | `aria_episodic` (par défaut, paramétrable) | Recall sémantique général, filtre distance + filter type    |
| `retrieve_by_intent` | `aria_episodic`       | Recall ciblé par `intent_id` (room)                          |
| `retrieve_semantic`  | `aria_semantic`       | Recall faits stables, `subject` optionnel                    |

Docstring de tête (lignes 5-9, 25-28) :

> MempalaceBridge est l'unique point d'accès **en lecture** à
> la mémoire vectorielle. […] Ce module ne décide pas — il
> récupère et filtre.

Le bridge **n'a jamais** été conçu pour écrire. Les callers actuels
qui écrivent (`memory_router`, `intent_engine`, etc. — à confirmer
caller par caller hors sprint) appellent `memory.writer.write_*`
directement.

### 1.3 `memory/mempalace_store.py` — wrapper minimal

Fichier intégral (21 lignes) examiné. Une seule fonction `search()`
qui délègue à `mempalace.searcher.search_memories`. **Aucune
écriture.** Le store est consommé en injection par le bridge :
`MempalaceBridge(store=mempalace_search)` à `core/kernel.py:111`.

### 1.4 Architecture wing : pas de registration

Pas un seul `register`/`init_wing`/`create_wing` dans `memory/`
(grep exhaustif). Côté fork `mempalace/palace.py:59-73` :

```python
def get_collection(palace_path, collection_name=None, create=True):
    if collection_name is None:
        from .config import get_configured_collection_name
        collection_name = get_configured_collection_name()
    return _DEFAULT_BACKEND.get_collection(
        palace_path,
        collection_name=collection_name,
        create=create,
    )
```

**UNE collection ChromaDB pour tout le palace.** Le filtrage par
"wing" est purement metadata :

`mempalace/searcher.py:168-176` :
```python
def build_where_filter(wing: str = None, room: str = None) -> dict:
    if wing and room:
        return {"$and": [{"wing": wing}, {"room": room}]}
    elif wing:
        return {"wing": wing}
    ...
```

→ **Créer une nouvelle wing = écrire avec une nouvelle valeur du
champ metadata `wing`.** Rien d'autre. Aucune action côté palace,
aucune migration, aucune registration. Le brief kickoff sprint 15
qui parle de "registration équivalente aux wings existantes" doit
être lu au sens "création par écriture initiale", pas au sens
technique d'une registration séparée — celle-ci n'existe pas et
n'a jamais existé.

─────────────────────────────────────────────────────────────────────────

## 2. État `Event.conversation_id` (sprint 14 §6 reconfirmé)

`core/event.py:17-34` (intégral) :

```python
@dataclass
class Event:
    id: str
    type: EventType
    user_id: str
    content: Any
    metadata: Dict[str, Any]
    conversation_id: Optional[str] = None

    @staticmethod
    def create(event_type, user_id, content, metadata):
        return Event(
            id=str(uuid.uuid4()),
            type=event_type,
            user_id=user_id,
            content=content,
            metadata=metadata or {},
        )
```

Observations :
- `conversation_id: Optional[str] = None` déclaré ligne 24.
- `Event.create()` lignes 26-34 : signature sans `conversation_id`,
  appel constructeur lignes 28-33 sans `conversation_id`. Le défaut
  `None` est toujours appliqué.
- Grep exhaustif `conversation_id` (hors `venv`) :
  ```
  core/event.py:24:    conversation_id: Optional[str] = None
  ```
  **Aucun caller.** Champ déclaré, jamais assigné, jamais lu.

Sprint 14 §6 (audit_contexte_conversationnel.md) confirmé sans
nuance : promouvoir `Event.conversation_id` exige une modification
de `core/event.py` (signature `Event.create` + assignation),
`interfaces/telegram_interface.py` (les deux handlers populent),
et toute autre interface future. Modification non triviale, à
planifier sprint 17 (branchement bout-en-bout) si décidée.

─────────────────────────────────────────────────────────────────────────

## 3. État `config.max_history_turns` (sprint 14 §6 reconfirmé)

Grep exhaustif `max_history_turns` (hors `venv`) :

```
config.py:67:    max_history_turns: int = 10
```

Une seule occurrence dans tout le code prod. **Aucun caller.**
Dead config. Sprint 14 §6 confirmé. Pas dans le scope sprint 15,
à supprimer sprint 18 (nettoyage périmétrique optionnel) ou laisser
en place comme placeholder explicite pour le futur paramètre du
`load(n)` du store.

─────────────────────────────────────────────────────────────────────────

## 4. Cartographie `chat_id` Telegram

### 4.1 Source

`interfaces/telegram_interface.py:62-71` (`_handle_message`) :

```python
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
```

`_handle_photo:86-106` : pattern identique, `chat_id = update.effective_chat.id`
posé dans `Event.metadata["chat_id"]`.

### 4.2 Propagation

`core/kernel.py:143-156` (`handle_event` étape 3) :

```python
exec_op = ExecutionOperation(
    type=cognitive_result.type,
    payload={
        "op_type": cognitive_result.type,
        "content": event.content,
        "metadata": {**event.metadata,
                     "interrogative": cognitive_result.interrogative,
        },
    },
    metadata=event.metadata,
)
```

`chat_id` est présent à deux endroits :
- `exec_op.payload["metadata"]["chat_id"]` (spread `event.metadata`).
- `exec_op.metadata["chat_id"]` (assignation directe).

Disponible bout en bout côté routeurs d'exécution sans aucune
modification de signature. Pour sprint 17 (branchement), un caller
qui veut indexer le store conversationnel par chat_id n'a qu'à
`str(event.metadata["chat_id"])` au moment de l'appel.

### 4.3 Granularité

`chat_id` = ID du chat Telegram. En mono-user 1:1 (cas Nico),
correspond exactement à une conversation. En groupe Telegram
hypothétique, idem (un chat = un groupe = une conversation
distincte). C'est la bonne granularité conversationnelle.

`user_id` (Telegram user) n'est PAS la bonne granularité — un même
utilisateur peut avoir plusieurs chats ouverts (DM bot + chat
groupe). Aujourd'hui irrélevant en mono-user mais c'est bien
`chat_id` qui borne la "conversation" au sens UX.

─────────────────────────────────────────────────────────────────────────

## 5. Cartographie capacités ChromaDB pour le store

### 5.1 Écriture

`col.upsert(documents=[...], ids=[...], metadatas=[...])` :
pattern existant utilisé par les 4 writers. Aucune contrainte
sur la valeur du champ metadata `wing` — n'importe quelle string.
**`wing="aria_conversation"` sera accepté sans changement.**

Métadonnées supportées : `str | int | float | bool | None`. Pas
de dict ni de list. Les datetime sont sérialisés en `isoformat()`
avant écriture (cf. `_now_iso()` writer.py:56).

### 5.2 Lecture par filtre metadata (sans embedding)

`col.get(where={...})` utilisable sans query vectorielle, prouvé
par usage dans le fork mempalace lui-même —
`mempalace/searcher.py:_expand_with_neighbors:218` :

```python
neighbors = drawers_col.get(
    where={
        "$and": [
            {"source_file": src},
            {"chunk_index": {"$in": target_indexes}},
        ]
    },
    include=["documents", "metadatas"],
)
```

Pour le store conversationnel, ça donne :

```python
col.get(
    where={"$and": [
        {"wing": "aria_conversation"},
        {"conversation_key": conv_key},
    ]},
    include=["documents", "metadatas"],
)
```

### 5.3 Tri chronologique

**ChromaDB `.get()` ne supporte pas le tri natif.** Il faut trier
en Python post-récupération. Pour un load de N derniers tours :

```python
result = col.get(where={...}, include=["documents", "metadatas"])
turns = list(zip(result["documents"], result["metadatas"]))
turns.sort(key=lambda t: t[1]["timestamp"])
return turns[-n:]
```

Performance : O(k log k) où k = nombre total de tours dans la
conversation. En mono-user Nico avec une conversation Telegram
typique, k est petit (dizaines à centaines max). Pas un goulot,
sprint 15 cadre confirmé. Si k explose (10k+ tours) en horizon
multi-mois, on peut filtrer par fenêtre temporelle dans le `where`
(`{"timestamp": {"$gte": <iso>}}`) — hors-scope sprint 15.

### 5.4 Suppression / TTL

Hors-scope sprint 15 explicite (kickoff §"Hors-scope strict"). Le
store écrit, ne supprime jamais. À traiter plus tard si la
volumétrie devient un sujet.

─────────────────────────────────────────────────────────────────────────

## 6. Inflexion architecturale : `MempalaceBridge` lecture+écriture

### 6.1 État actuel

`MempalaceBridge` docstring §"Architecture" (lignes 5-9) :

> MempalaceBridge est l'unique point d'accès **en lecture** à
> la mémoire vectorielle.

§"Responsabilités" (lignes 20-23) :

> - Filtrage qualité (distance, room générique)
> - Filtre optionnel par type de document
> - Isolation du reste du code de tout import ChromaDB direct

Le bridge est strictement lecture. Les écritures passent par
`memory.writer.write_*` appelé directement.

### 6.2 Demande du brief sprint 15

Kickoff §"Livrable principal" :

> Méthodes correspondantes sur `MempalaceBridge` :
> `write_conversation_turn` et `load_conversation_history`,
> qui délèguent au `conversation_store`.

→ Inflexion. Si appliquée littéralement, le bridge gagnerait une
méthode d'écriture (la première de son histoire), brisant son
invariant lecture-seule.

### 6.3 Options

**Option A — appliquer le brief littéralement.** Ajouter
`write_conversation_turn` et `load_conversation_history` sur le
bridge. Le bridge devient lecture+écriture. Cohérence interne du
codebase rompue (les autres écritures continuent à passer par
`writer.py` direct).

**Option B — bridge reste lecture, écriture via writer.py.**
Ajouter `write_conversation_turn` à `memory/writer.py` (cinquième
fonction d'écriture, parfaitement cohérente avec les 4 existantes).
Ajouter `load_conversation_history` à `MempalaceBridge` (lecture
chronologique, cohérent avec retrieve_*).

**Option C — module autonome.** Tout dans `memory/conversation_store.py`
(append + load), `writer.py` et `bridge.py` non touchés. Le module
expose ses propres `append`/`load` que les callers sprint 17
importent directement.

### 6.4 Recommandation : option B

Raisons :
1. **Préserve l'invariant W4** : `writer.py` reste l'UNIQUE point
   d'écriture mémoire, ce qui est une règle d'architecture
   inviolable (CLAUDE.md §"Règles d'architecture INVIOLABLES"
   point 1). L'option A le viole formellement, l'option C
   l'érode (deuxième chemin d'écriture caché dans
   `conversation_store.py`).
2. **Préserve l'invariant bridge lecture-only** : le bridge garde
   sa contractualisation explicite ("ne décide pas — récupère et
   filtre"). `load_conversation_history` est une lecture, légitime
   sur le bridge.
3. **Cohérence avec les wings existantes** : `write_interaction`
   pour `aria_episodic`, `write_semantic_fact` pour `aria_semantic`,
   `write_classifier_cache` pour `aria_classifier`. Une cinquième
   `write_conversation_turn` pour `aria_conversation` complète le
   pattern, lisible immédiatement par tout dev qui ouvre `writer.py`.
4. **Surgical** : un seul nouveau fichier (`conversation_store.py`
   peut être absorbé dans `writer.py` + une nouvelle méthode bridge,
   ou rester séparé comme module mince selon préférence Nico).
5. **Le brief sprint 15 est rédigé par l'architecte avant lecture
   fine du code** — il n'invariantait pas la lecture-only du bridge.
   Cette inflexion est l'exact type de point que le tour 1 audit
   doit remonter pour arbitrage. Recommander de la corriger
   maintenant plutôt que de figer dans le code la violation.

**Décision concrète proposée** : pas de fichier
`memory/conversation_store.py` séparé. Tout vit en deux endroits :

- `memory/writer.py` → ajouter `write_conversation_turn(conversation_key, role, content)`.
- `memory/mempalace_bridge.py` → ajouter `load_conversation_history(conversation_key, n)`.

C'est plus simple, plus surgical, plus cohérent. À confirmer par
Nico — si préférence pour module séparé (lisibilité, séparation
domaine), option C reste acceptable mais ré-introduit une voie
d'écriture hors-writer.

─────────────────────────────────────────────────────────────────────────

## 7. Arbitrage 1 — clé d'indexation : `chat_id` vs `Event.conversation_id`

### 7.1 Comparatif

| Critère                              | `chat_id` brut                                | `Event.conversation_id` promu                  |
|--------------------------------------|-----------------------------------------------|------------------------------------------------|
| Disponibilité sprint 17              | Immédiate (`event.metadata["chat_id"]`)       | Modifs `core/event.py` + `TelegramInterface`   |
| Couplage transport                   | Le STORE n'en sait rien (signature `conversation_key: str`), le CALLER mappe | Découplé par contrat, mais le caller doit toujours mapper depuis quelque part |
| Évolution multi-transport            | Politique d'assignation décidée par chaque interface (CLI : ?, MCP : ?) | Politique centralisée dans `Event.create()` ou interface |
| Risque de régression                 | Bas — `chat_id` est déjà transporté bout en bout | Moyen — touche `Event` (load-bearing), tests à ajuster |
| Calibrage CLAUDE.md                  | "Fix qui marche, surgical, moins exigeant"    | Soin supplémentaire pour proprement abstraire  |
| Mono-user (cadre ARIA)               | Suffisant indéfiniment                        | Sur-engineering pour un seul transport actif   |

### 7.2 Recommandation : `chat_id` brut, sous nom générique côté store

**Le store ne connaît PAS `chat_id`. Il connaît `conversation_key: str`.**

Côté caller (à brancher sprint 17) :
```python
conv_key = str(event.metadata.get("chat_id", "default"))
bridge.write_conversation_turn(conv_key, role="user", content=...)
```

Avantages :
- Zéro modification de `Event` au sprint 15 et 17.
- Le store est testable avec n'importe quelle string comme clé.
- Le jour où on promeut `Event.conversation_id` (sprint 18 ou
  plus tard), c'est UNE ligne à changer côté caller : on remplace
  `str(event.metadata["chat_id"])` par `event.conversation_id`.
  Le store n'est pas affecté.
- Politique d'assignation reportable jusqu'à ce qu'un deuxième
  transport existe vraiment. YAGNI respecté.

**Verdict** : option `chat_id` brut, paramètre store nommé
`conversation_key`. La promotion de `Event.conversation_id` reste
ouverte pour plus tard mais n'est pas nécessaire pour livrer
sprint 15-17.

─────────────────────────────────────────────────────────────────────────

## 8. Arbitrage 2 — format turn : texte concaténé vs `role/content`

### 8.1 Comparatif

| Critère                         | Texte concaténé `USER:...ARIA:...`         | `role/content` séparé (1 doc par tour)        |
|---------------------------------|---------------------------------------------|-----------------------------------------------|
| Affinité format provider sprint 16 | Re-parsing texte requis dans LLMRouter   | Mapping direct `{role, content}` natif        |
| Granularité requête             | Un doc = un échange complet (turn user+aria) | Un doc = un message (1 user OU 1 aria)       |
| Filtrage par rôle               | Impossible sans parser                     | Trivial : `where={"role": "user"}`           |
| Cohérence avec `write_interaction` existant | Identique au pattern actuel `aria_episodic` | Divergence — nouveau pattern              |
| Empreinte ChromaDB (par tour)  | 1 entrée pour 2 messages                   | 2 entrées (1 user, 1 aria) — double          |
| Risque de désync user/aria      | Inexistant (atomique par échange)          | Existant — un crash entre append user et append aria laisse un orphelin |
| Tri chronologique               | 1 timestamp par échange                    | 1 timestamp par message — ordre user→aria explicite |
| Recall ciblé "dernier message user" | Parsing requis                          | Trivial : `where={"role": "user"}`, sort, take last |

### 8.2 Risque désync user/aria — atténuation

Si on choisit `role/content` séparé, le risque qu'un crash entre
`append(role="user")` et `append(role="assistant")` laisse un
message user orphelin est réel. Trois mitigations possibles :

1. **Batch atomique** : `append_turn(conv_key, user_msg, aria_msg)`
   qui fait UN upsert ChromaDB avec deux documents. Atomique.
2. **Append sur réussite seulement** : l'appender côté caller
   (sprint 17) n'append le user qu'APRÈS avoir reçu la réponse
   aria, et fait les deux dans la foulée.
3. **Tolérance** : on accepte que sur un crash, on perde la
   symétrie du tour — c'est un cas rare et la conversation
   continue, c'est juste un message user "non répondu" visible
   dans l'historique.

Recommandation : mitigation 2 (append côté caller juste avant le
retour réponse). Simple, alignée sur le pipeline sprint 17 qui
n'est pas encore défini en détail. Mitigation 3 acceptable pour
sprint 15-17, à observer en prod.

### 8.3 Recommandation : `role/content` séparé

Alignement avec la recommandation architecte (plan sprint 14 §3,
kickoff sprint 15). Raisons :

1. **Format natif provider sprint 16** : `LLMRouter._call` passera
   `messages=[{role, content}, ...]` au provider (Mistral / autres).
   Le store renvoie déjà la structure. Zéro re-parsing.
2. **Granularité de lecture** : pouvoir filtrer "dernier message
   user" ou "n derniers messages assistant" sans parser un texte
   structuré simplifie tout traitement futur (ex : retrieval
   sémantique sur les seules questions user, log analyse, etc.).
3. **Lisibilité ChromaDB** : un dump du palace montre une ligne
   par message, lisible en debug sans avoir à parser un blob.
4. **Empreinte 2× acceptable** : à 200 octets par message,
   1000 tours = 400 Ko. Non-sujet.

Verdict : structure séparée, schéma proposé §10.2.

─────────────────────────────────────────────────────────────────────────

## 9. (Hors-scope confirmé — placeholder de cohérence)

Section vide intentionnellement — voir §6 pour la décision
architecturale (bridge lecture+écriture vs séparation). Numérotation
préservée pour ne pas re-référencer les sections suivantes.

─────────────────────────────────────────────────────────────────────────

## 10. Esquisse API pour le tour 2 (fix)

**Esquisse uniquement** — implémentation au tour 2 après validation
architecte de cet audit.

### 10.1 `memory/writer.py` — nouvelle fonction

```python
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
    métadonnée pour permettre le tri chronologique et le filtrage par
    rôle côté lecture.
    """
    col = get_collection(config.mempalace_path)
    doc_id = f"conv_{conversation_key}_{uuid4().hex[:12]}"

    meta = {
        **(extra or {}),
        "wing": "aria_conversation",
        "room": conversation_key,
        "type": "conversation_turn",
        "timestamp": _now_iso(),
        "role": role,
        "conversation_key": conversation_key,
    }
    _validate(meta)
    col.upsert(documents=[content], ids=[doc_id], metadatas=[meta])
```

Notes :
- `conversation_key` est dupliqué entre `room` et `meta["conversation_key"]`
  pour permettre soit le filtrage style `retrieve_by_intent` (par
  room) soit le filtrage direct par metadata. Cohérent avec le
  pattern existant.
- `role` est en metadata simple (string).
- Pas d'idempotence (`_idempotent_doc_id`) : un tour conversationnel
  est unique par construction temporelle. `uuid4` suffit. Si on
  voulait l'idempotence, ce serait `_idempotent_doc_id(content,
  f"{conversation_key}|{role}")`.

### 10.2 `memory/mempalace_bridge.py` — nouvelle méthode

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

    Returns:
        liste de {"role": str, "content": str, "timestamp": str}
        triée par timestamp croissant.
    """
    # Note : utilise col.get(where=...) — pas une recherche sémantique.
    # ChromaDB ne trie pas, on trie en Python sur metadata.timestamp.
    # ...
```

Esquisse incomplète intentionnelle : nécessite soit d'élargir le
contrat `store(...)` au-delà de `search()` (qui n'accepte que des
queries vectorielles), soit d'introduire un deuxième callable
injecté pour le `get()` non vectoriel. **Décision technique à
trancher au tour 2 selon préférence Nico** :

- **B1** : étendre le store wrapper `memory/mempalace_store.py`
  avec une fonction `get_by_metadata(palace_path, where)` qui
  encapsule `col.get(where=...)`. Le bridge la reçoit en second
  param d'injection. Cohérent avec l'isolation de tout import
  ChromaDB direct (responsabilité bridge ligne 23).
- **B2** : le bridge importe directement `get_collection` depuis
  `mempalace.palace` pour le `get()`. Brise l'isolation mais
  simple. **À éviter** sauf raison forte.

Recommandation : **B1**.

### 10.3 Tests unitaires (cas nominaux du brief)

Conformes au calibrage CLAUDE.md ("fix qui marche + 1 test de
non-régression sur le cas nominal, rien de plus") et au kickoff
§"Calibrage" :

- `test_write_conversation_turn_wing_is_conversation`
- `test_write_conversation_turn_room_is_conversation_key`
- `test_write_conversation_turn_extra_cannot_override_wing` (W4)
- `test_load_history_returns_chronological_order`
- `test_load_history_caps_at_n`
- `test_load_history_empty_returns_empty_list`
- `test_load_history_isolates_distinct_conversations`

Pattern FakeCollection identique à `tests/memory/test_writer.py`.
La fixture `fake_col` patch `memory.writer.get_collection`. Pour
le bridge, une seconde fixture `fake_get_by_metadata` capture les
appels. Pas de palace réel, pas de chromadb réel.

─────────────────────────────────────────────────────────────────────────

## 11. Décisions à valider par l'architecte avant tour 2

1. **§6.4 — option B retenue** (bridge garde lecture seule,
   `write_conversation_turn` rejoint `writer.py`,
   `load_conversation_history` rejoint le bridge). Ou alternative
   préférée parmi A/C.
2. **§7.2 — `chat_id` brut sous nom générique `conversation_key`** :
   confirmer pas de promotion `Event.conversation_id` au sprint
   15-17.
3. **§8.3 — format `role/content` séparé** : confirmer (recommandation
   architecte déjà posée, je la valide après lecture du code).
4. **§10.2 — option B1 retenue** (extension du store wrapper avec
   `get_by_metadata`, deuxième injection bridge). Ou B2 si simplicité
   prime.
5. **§10.1 — granularité `room`** : confirmer que `room=conversation_key`
   est acceptable malgré la duplication avec `meta["conversation_key"]`.
   Alternative : `room="conversation"` (générique) + `conversation_key`
   en metadata seule. Préférence audit : `room=conversation_key` pour
   cohérence avec `write_interaction` (`room=intent_id`) et possibilité
   future de filtrer via `retrieve_by_room`-style.

─────────────────────────────────────────────────────────────────────────

## 12. Cohérence avec règles inviolables CLAUDE.md

Vérification ligne par ligne du §"Règles d'architecture INVIOLABLES" :

1. ✅ **Un seul point d'écriture mémoire (writer.py)** : option B
   §6.4 respecte. Option A/C l'érodent.
2. ✅ **Une lecture mémoire passe par bridge** : `load_conversation_history`
   sur le bridge respecte.
3. ✅ **Agents reçoivent AgentContext pré-assemblé, ne font aucune
   requête mémoire** : sprint 15 ne touche aux agents, livraison
   inerte côté pipeline. Au sprint 17, c'est le kernel qui appellera
   `bridge.load_conversation_history` puis passera le résultat dans
   le contexte agent. Conforme.
4. ✅ **Routers retournent `{"text"}` / `{"path", "caption"}`** : non
   touché sprint 15.
5. ✅ **Kernel séquence, ne décide pas** : non touché sprint 15.
6. ✅ **CognitiveEngine tient dépendances injectées, pas de retrieval
   direct** : non touché sprint 15.

Aucune violation à signaler dans le design proposé.

─────────────────────────────────────────────────────────────────────────

## 13. Dettes adjacentes notées (NON traitées dans le sprint)

Conformément à CLAUDE.md §"Résiste au scope creep" :

- **Dead config `config.max_history_turns`** (§3) : à supprimer
  sprint 18 (nettoyage périmétrique).
- **Dead field `Event.conversation_id`** (§2) : à promouvoir ou
  supprimer sprint 18 (selon décision §7.2 reportée). Si on confirme
  `chat_id` brut indéfiniment, supprimer.
- **`MempalaceBridge` docstring** (§6.1) : mentionne "unique point
  d'accès en lecture". Si option B retenue, docstring reste valide.
  Si option A retenue, à mettre à jour.
- **Brief kickoff sprint 15 §"Livrable principal"** : formulation
  "Création de la wing aria_conversation (registration équivalente
  aux wings existantes)" est trompeuse — il n'y a pas de
  registration. À reformuler dans le doc kickoff (Nico arbitre).

─────────────────────────────────────────────────────────────────────────

## 14. Critères de fin tour 1

- [x] Cartographie écriture mémoire complète (§1).
- [x] Confirmation dead `Event.conversation_id` (§2).
- [x] Confirmation dead `max_history_turns` (§3).
- [x] Cartographie `chat_id` Telegram (§4).
- [x] Capacités ChromaDB documentées (§5).
- [x] Inflexion bridge architecturale remontée (§6).
- [x] Arbitrage 1 tranché avec preuve code (§7).
- [x] Arbitrage 2 tranché avec preuve code (§8).
- [x] Esquisse API tour 2 (§10).
- [x] Cohérence règles inviolables vérifiée (§12).
- [x] Dettes adjacentes notées hors-scope (§13).

**Critères tour 1 atteints.** Validation architecte requise sur les
5 points §11 avant ouverture tour 2 (fix).

─────────────────────────────────────────────────────────────────────────
