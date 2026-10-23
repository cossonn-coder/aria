# Sprint 32 — audit « Prochaine action : … » (#74) et payload de 319 000 car. (#113)

Date : 2026-10-23. Code lu sur `main` (`9516075`). Données : `~/.aria/intents.json`
(327 645 octets, 9 intents) et `journalctl -u aria` du run live 31 (09:51-09:53).

## 1. Constat (run live 31, message 3 `salut`)

```
09:52:10 telegram_update … type=text                 ← « salut »
09:52:10 conversation_history loaded … messages=20
09:52:11 [LLM] groq (qwen…) a répondu.               ← classifier (court)
09:52:12 provider groq skipped (payload 319023 chars > 12000)  ×3
09:52:17 [LLM] deepseek (deepseek-flash) a répondu.  ← 1er appel : 319 023 car.
09:52:17 provider groq skipped (payload 161407 chars > 12000)  ×3
09:52:21 [LLM] deepseek (deepseek-flash) a répondu.  ← 2e appel : 161 407 car.
09:52:23 pipeline done → 86 chars                    ← « Prochaine action : Partie contre AaronDias16 … »
```

Aucun appel au namer : le `salut` a été **rattaché** (`attach`) à l'intent actif
`jeux echecs` (id `f2f3be70…`).

## 2. Chemin de code

### 2.1 Classification
`salut` est court → `CognitiveOperation.CONFIRMATION` (`cognition/cognitive_classifier.py:14`, règle
« message court »).

### 2.2 Choix du pipeline — `agents/controller/controller_agent.py:22-46`

```python
if operation in (FACT_RECALL, MEMORY_QUERY, PROFILE_QUERY, META_MEMORY):
    pipeline = ["analyst"]
elif operation == PLANNING:
    pipeline = ["analyst", "planner"]
elif operation == REASONING:
    pipeline = ["analyst"]
else:                                     # CONFIRMATION, UNKNOWN, …
    phase = ctx.intent.infer_phase() if ctx.intent else "creation"
    if phase == "creation":   pipeline = ["analyst"]
    elif phase == "planning": pipeline = ["analyst", "planner"]
    elif phase == "execution": pipeline = ["executor", "critic"]   ← #74
    else:                     pipeline = ["analyst"]
```

### 2.3 Phase — `intent/intent.py:110-115`

```python
def infer_phase(self):
    if not self.actions_history: return "creation"
    if self.next_action:         return "execution"
    return "planning"
```

- `IntentEngine.apply` (`intent/intent_engine.py:145-193`) appelle **toujours** `add_action`
  (CREATE, ATTACH, SPLIT) → `actions_history` n'est jamais vide après `apply` → la phase
  `creation` n'est jamais atteinte sur un intent résolu.
- `next_action` est posé par `PlannerAgent` (`agents/planner_agent.py:57-58`) ou par
  `ExecutorAgent` lui-même (`agents/executor_agent.py:59-63`).
- **Piège collant** : un message CONFIRMATION/UNKNOWN sur un intent sans `next_action` passe par
  analyst + planner ; dès que le planner pose une `next_action`, tous les messages suivants de cette
  catégorie sur cet intent partent en executor + critic. L'executor repose lui-même une
  `next_action` à chaque passage : on ne sort plus de la phase `execution`. Seule échappatoire :
  l'executor renvoie `STATUS: completed` → l'intent sort des actifs (c'est le `jeux echecs`
  `completed` à 64 actions dans `intents.json`), puis un nouvel intent du même nom est recréé par
  l'analyse suivante (`forced_intent_name`) et le cycle recommence. D'où l'apparition intermittente
  [n=4].

État prod actuel : `jeux echecs` actif, 29 actions, `next_action = "Partie contre AaronDias16
2026.10.22 Dutch Defense Normal Variation"` ; `plantation tomates balcon est` et `apprentissage
docker` ont aussi une `next_action` → mêmes symptômes possibles sur un `ok` / `merci` rattaché.

### 2.4 Réponse affichée — `agents/executor_agent.py:71`

```python
ctx.result = f"Prochaine action : {intent.next_action}"
```

Le critic (`agents/critic_agent.py`) écrit dans `ctx.extra["critique"]`, jamais lu (dette #55).

## 3. #113 : les 319 000 car. ne sont PAS l'historique de conversation

Diagnostic du sprint 31 (« historique de 20 messages = 319 023 car. ») **faux**. Les deux appels
lourds sont les prompts de l'executor et du critic :

1. `EXECUTOR_PROMPT.format(intent=intent.subject, …, history="\n".join(history))`
   (`agents/executor_agent.py:43-47`) : `subject` est une **méthode** passée sans appel →
   le prompt contient `<bound method Intent.subject of Intent(id=…, actions_history=[…], …)>`,
   c'est-à-dire le `repr` complet du dataclass, `actions_history` compris. Puis `history`
   recopie `actions_history` une seconde fois.
2. `CRITIC_PROMPT.format(intent=ctx.intent.subject, …)` (`agents/critic_agent.py:40-44`) :
   même `repr`, une fois.
3. `actions_history` contient les messages **entiers** : `apply` → `add_action(message)`, et pour
   une analyse de partie le message est le bloc enrichi (≈ 9 000 car. chacun, 8 entrées entre
   8 940 et 9 621 car.). Total `jeux echecs` actif : 157 923 car. sur 29 entrées.

Reconstitution sur l'état `intents.json` (avant l'ajout de la dernière action) :

| Prompt | Reconstitué | Journal 09:52 |
|---|---|---|
| executor | 319 067 car. | 319 023 car. |
| critic | 161 325 car. | 161 407 car. |

Écart < 0,1 % [n=1 reconstitution] (dernière entrée d'historique différente). Par comparaison, l'appel
analyst du message 4 (historique de 20 messages compris) pesait 38 486 car.

→ #113 et #74 ont **la même racine** : la branche `execution` du contrôleur.

## 4. Callers

- `AgentController` : seul instancié dans `execution/routers/llm_router.py:72-73`, appelé à
  `llm_router.py:248` (`self.controller.run(ctx, self.llm_router)`).
- `ExecutorAgent`, `CriticAgent` : instanciés seulement dans `agents/registry_agent.py:21-22`,
  atteints seulement par la branche `execution` du contrôleur.
- `infer_phase` : `controller_agent.py:37`, `executor_agent.py:45`, `critic_agent.py:43`.
- Aucun test sur `AgentController`, `ExecutorAgent` ni `CriticAgent` (`grep` dans `tests/`).

## 5. Pistes

- **A** — branche `else` du contrôleur → `["analyst"]` toujours (la phase ne choisit plus le
  pipeline). CONFIRMATION/UNKNOWN répondent comme REASONING. Executor/critic n'ont plus de chemin
  (restent dans le registre, code mort à mentionner). Planner reste sur PLANNING.
  Corrige #74 et #113 ; supprime aussi l'appel planner parasite en phase `planning`
  (2 appels LLM sur un `ok` rattaché à un intent sans `next_action`).
- **B** — ne retirer que la branche `execution` (→ analyst), garder analyst + planner en phase
  `planning`. Corrige #74/#113 mais laisse le planner reformuler les messages courts tant que
  l'intent n'a pas de `next_action`, comportement incohérent d'un intent à l'autre.
- **C** — réparer l'executor (`subject()` appelé, historique tronqué) : le `salut` répondrait
  toujours « Prochaine action : … ». Écartée.

Aucune piste ne touche le palace ni `intents.json` : `next_action` reste stockée, simplement plus
lue pour router.

## 6. Dettes adjacentes (hors sprint)

- `actions_history` stocke les messages entiers (blocs enrichis de 9 000 car.) : `intents.json`
  à 327 Ko, croissance à chaque analyse. Plus envoyé au LLM après A, seulement du disque.
- `intent.subject` sans appel aussi dans le critic ; sans objet si plus de chemin.
- #39 (executor/critic sans historique), #41 (absents de l'inventaire), #55 (critique jamais lue)
  deviennent sans objet sous A : code sans caller → à ranger avec #72.
