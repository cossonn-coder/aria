# Sprint 17 — tronçon 02 : brancher l'historique conversationnel (A3, #34)

## Objectif

ARIA garde le fil d'une conversation Telegram. Chaque échange
user/assistant est écrit dans le wing `aria_conversation` ; au message
suivant, les derniers échanges sont relus et envoyés au LLM en
`messages=[...]` natifs (forme livrée au sprint 16).

Prérequis : tronçon 01 fait (les tests n'écrivent plus en prod).

Référence complète : `docs/sprint17/audit_branchement_caller.md`
(§0 constats C1–C4, §4.c composition du system prompt, §7 décisions
D1–D8, §9 règles inviolables). Ce kickoff en est la version arrêtée.

## Les 4 changements de prod (points vérifiés au code le 2026-10-15)

### 1. `core/kernel.py` — injecter la lecture (constat C1)

Ligne 111 : `MempalaceBridge(store=mempalace_search)` → ajouter
`get_by_metadata=` avec `memory.mempalace_store.get_by_metadata`
(signature `get_by_metadata(palace_path, where, include=None)`, attendue
par le bridge). Sans ça, `load_conversation_history` lève `RuntimeError`.
Respecter le style d'import existant de `mempalace_search` dans ce fichier.

### 2. `llm/llm_router.py` — exposer le system prompt de base (D6)

Ajouter une classmethod publique `LLMRouter.build_base_system_prompt()`
qui renvoie **exactement** la chaîne que la branche legacy de `_call`
construit aujourd'hui (lignes ~321-326) :
`_SOUL`, puis si `_USER` : `"\n\nPROFIL UTILISATEUR :\n" + _USER`,
joints par `"\n"`. Faire utiliser ce helper par la branche legacy de
`_call` (source de vérité unique). Ne rien changer d'autre dans le router
(la forme messages n'injecte toujours ni `_SOUL` ni `_USER`).

### 3. `execution/routers/llm_router.py` — lire et écrire (D1, D4, D5, constat C2)

Dans `LLMExecutionRouter._run_pipeline` :

- **Lecture**, avant la construction de `AgentContext` (étape 5) :
  `conversation_key = str(metadata.get("chat_id", "default"))` (D1 ;
  `chat_id` vient de `interfaces/telegram_interface.py`, passé en
  `metadata`). Charger
  `self.mempalace_bridge.load_conversation_history(conversation_key, n=config.max_history_turns * 2)`
  (D4/D7 : `max_history_turns`=10 tours = 20 messages ; documenter cette
  convention en commentaire). Poser la liste dans
  `ctx.extra["conversation_history"]`.
  Règle inviolable 3 : c'est le router qui lit, **jamais l'agent**.
- **Écriture**, à l'étape 10 : après l'écriture épisodique existante,
  deux appels `write_conversation_turn(conversation_key, "user", message)`
  puis `(conversation_key, "assistant", result)`.
  **Amendement Nico (2026-10-15)** : ces deux écritures se font **même
  si aucun intent n'est résolu** (aujourd'hui l'étape 10 saute tout si
  `intent is None`). Ne pas modifier le comportement de
  `write_interaction` (épisodique) : il garde sa condition sur l'intent.
  Même politique non bloquante que l'existant (`log.exception` si erreur,
  la réponse part quand même). `write_interaction` n'est pas supprimé.
- **Logs pour le run live** (une ligne `log.info` chacun, style des logs
  existants) : `conversation_history loaded key=%s messages=%d` après la
  lecture, `conversation_write OK key=%s` après les deux écritures.

### 4. `agents/analyst_agent.py` — appeler en forme messages (D2, D3, D8)

- Méthode privée `_build_system_prompt(self, ctx)` (D2) qui compose (D8,
  audit §4.c) :
  `LLMRouter.build_base_system_prompt()` + `"\n\nCONTEXTE COGNITIF :\n"` +
  `context_block` + `"\n\nPROJET RÉCENT EN MÉMOIRE :\n"` + `intent.name`
  + `"\n\n"` + bloc RÈGLES actuel.
- `run` construit
  `[{"role": "system", "content": system}] + [{"role": h["role"], "content": h["content"]} for h in history] + [{"role": "user", "content": ctx.message}]`
  avec `history = ctx.extra.get("conversation_history", [])`
  (le `timestamp` est retiré), puis
  `llm_router.complete(messages=..., role=role, temperature=0.3, max_tokens=800)`.
- Le slot `HISTORIQUE DE CETTE SESSION` et `_format_memories` disparaissent
  (constat C4 : c'était du recall épisodique, toujours présent via
  `context_block`). Supprimer `_format_memories` s'il n'a plus de caller.
- `ctx.intent` peut-il être `None` dans Analyst ? Vérifier au code ; si
  oui, se comporter comme aujourd'hui (le `PROMPT.format` actuel accède à
  `ctx.intent.name` sans garde → même comportement accepté).

**Garde-fou** : la constante de module `PROMPT` reste (le test
`tests/agents/test_analyst_prompt_guard.py` la lit). Elle doit garder ses
4 ancres (pas de `"domaine actuel"` ni `"uniquement dans le domaine"`,
présence de `"quel que soit le sujet"` et `"projet récent en mémoire"`,
longueur > 200). Le plus simple : `PROMPT` devient le gabarit de la partie
propre à l'agent (PROJET RÉCENT + RÈGLES). Le test garde-fou ne doit pas
être modifié.

## Tests (cas nominaux, pas plus)

Nouveau fichier `tests/agents/test_analyst_messages_form.py`, et/ou
ajouts côté router :
1. Historique vide → `messages` = `[system, user]`.
2. Historique de 2 tours → `messages` = `[system, user1, assistant1, user2(courant)]`
   dans l'ordre, sans `timestamp`.
3. Le system prompt contient le profil (`PROFIL UTILISATEUR`), le
   `context_block` et le nom d'intent.
4. Router : après un `_run_pipeline` avec `metadata={"chat_id": 42}`,
   `load_conversation_history("42", n=20)` a été appelé et deux
   `write_conversation_turn` ont eu lieu (user puis assistant), y compris
   quand aucun intent n'est résolu.

Adapter les tests existants qui supposaient `complete(prompt)` côté
Analyst, sans élargir leur portée.

## Ne PAS faire

- Pas de modification de `planner_agent.py`, `executor_agent.py`,
  `critic_agent.py`, `cognitive_classifier.py`, `intent_namer.py`.
- Pas de modification de `load_conversation_history`,
  `write_conversation_turn`, `core/event.py`, `config.max_history_turns`.
- Pas de limite de temps sur l'historique (décision Q2 : les 10 derniers
  tours quel que soit leur âge).
- Pas de déduplication épisodique/conversation (dette #38 candidate).
- Pas de `soul.md` / `user.md` modifiés.

## Critère de fin

pytest vert (dont le garde-fou), les 4 cas ci-dessus couverts. Rapport :
lister ce que seul le run live validera (continuité réelle, latence).
