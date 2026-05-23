# Plan de fix — perte du contexte conversationnel multi-tour

**Sprint** : 14 / clôture
**Branche** : `feat/sprint14-context-continuity`
**Date** : 2026-05-23
**Référence audit** : `docs/sprint14/audit_contexte_conversationnel.md`
**Dette tracée** : #34 (perte systématique du contexte
conversationnel multi-tour).
**Scope** : plan documentaire de fix. Aucune modification de
code dans ce sprint. Le code est livré aux sprints 15-17 (et
optionnellement 18).

---

## §1 — Décision architecturale

### Approche retenue : **A — multi-messages format natif provider**

Le `LLMRouter._call` accepte désormais une liste de messages
typés `role/content` (`user`, `assistant`, `system`),
construite à partir d'un historique chronologique de la
conversation. Chaque provider (Anthropic, OpenAI-like, Gemini)
reçoit ses messages dans son format natif, sans sérialisation
en prompt unique côté agent. La continuité conversationnelle
devient une responsabilité de la couche router, pas du prompt
template.

### Approches écartées

- **B — sérialisation en prompt unique** : injecter l'historique
  comme bloc texte dans le prompt analyst. Écartée parce qu'elle
  perpétue l'illusion d'un dialogue dans un appel one-shot, gaspille
  des tokens en formatage répétitif, et bride la qualité de
  raisonnement des modèles entraînés sur des dialogues structurés.
- **C — hybride par opération** : multi-messages pour CHAT,
  sérialisation pour PLANNING/REASONING. Écartée parce qu'elle
  double les chemins de code, multiplie les modes de bug, et
  laisse précisément les opérations longues (PLANNING) sans
  vrai contexte conversationnel — alors que c'est là que le
  bug se manifeste le plus visiblement (cas "15 août").

### Store retenu : **wing MemPalace dédiée `aria_conversation`**

Une nouvelle wing distincte des trois existantes. Stockage
chronologique des tours d'une conversation, indexé par clé de
conversation (à trancher en sprint 15 : `chat_id` Telegram brut
ou `Event.conversation_id` promu).

Raisons :

- **Persistence au restart** : un store RAM-only perdrait
  l'historique à chaque `systemctl restart aria.service`, ce
  qui est en pratique fréquent (tour 1 d'un sprint touche
  presque toujours le service).
- **Alignement vision multi-utilisateurs** : ARIA est mono-user
  aujourd'hui (Nico via Telegram), mais le kernel cognitif est
  conçu pour scaler vers d'autres interfaces (web, voice).
  L'identifiant conversationnel doit être indépendant du
  protocole transport.
- **Sémantique propre vis-à-vis des wings existantes** :
  - `aria_episodic` = retrieval vectoriel par similarité, room
    = `intent_id`, granularité = interaction résolue.
  - `aria_semantic` = faits stables sur l'utilisateur.
  - `aria_classifier` = cache des décisions du classifier.
  - `aria_conversation` (nouveau) = dialogue chronologique brut,
    indexé par identifiant de conversation, granularité = tour.
  La séparation évite que la nouvelle dimension chronologique
  pollue le retrieval vectoriel existant.

### Stores écartés

- **RAM (dict en mémoire dans le kernel)** : perte à chaque
  redémarrage du service.
- **Dérivation depuis `aria_episodic`** : la wing épisodique est
  optimisée pour le retrieval vectoriel filtré par `intent_id`.
  La requérir en mode "derniers N tours par timestamp"
  obligerait à introduire des filtres ChromaDB hétérogènes sur
  une wing déjà chargée, et l'`intent_id` change d'un tour à
  l'autre (cf. audit §6 point 4) — la conversation serait
  fragmentée à travers plusieurs rooms.
- **Fichier JSON local** : pas de cohérence avec le reste de
  l'architecture mémoire MemPalace, oblige à dupliquer la couche
  de persistence.

---

## §2 — Découpage en sous-sprints

| Sprint | Objectif | Livrable | Critère de fin |
|---|---|---|---|
| 15 (A1) | Store conversationnel | Module `conversation_store.py` avec API `append`/`load` + tests unitaires | Tests verts, module non encore branché dans le pipeline |
| 16 (A2) | LLMRouter multi-messages | `LLMRouter._call` accepte `messages: list[dict]`, compat ascendante via helper wrap, tests par provider | Tests verts sur Anthropic + un OpenAI-like + Gemini ; pipeline existant inchangé en comportement (helper wrap rétro-compatible) |
| 17 (A3) | Branchement bout-en-bout | Kernel écrit dans le store, agents lisent et passent messages au router, suppression slot `HISTORIQUE DE CETTE SESSION` trompeur, validation Telegram live | Run live sur cas "15 août" : aria répond en gardant le contexte du tour 1 |
| 18 (A4) optionnel | Nettoyage périmétrique | Reclassement `MEMORY_TOP_K[CONFIRMATION]`, revue `MIN_MESSAGE_LENGTH=10`, décision sur `Event.conversation_id` (retirer ou promouvoir), retrait `max_history_turns` dead config | Décisions documentées, code nettoyé, tests verts |

---

## §3 — Points d'attention par sous-sprint

### Sprint 15 (A1) — Store conversationnel

**Fichiers principalement touchés**

- Nouveau : `memory/conversation_store.py`.
- Modifié : `memory/mempalace_bridge.py` — ajout des méthodes
  `write_conversation_turn` et `load_conversation_history`.
- Configuration palace : création de la wing
  `aria_conversation` dans MemPalace (suit le même schéma de
  registration que `aria_episodic`, `aria_semantic`,
  `aria_classifier`).

**Risques identifiés**

- **Choix de la clé d'indexation** : `chat_id` Telegram brut
  (simple, transport-couplé) vs `Event.conversation_id` promu
  en champ structurel (plus propre, demande de toucher
  `core/event.py` et `TelegramInterface`). À trancher dès
  l'audit tour 1 du sprint 15.
- **Format de stockage du turn** : texte concaténé
  `USER:\n... \n\nARIA:\n...` (comme l'actuel
  `write_interaction`) vs structure `role/content` séparée
  (deux entrées par tour, ou une entrée avec champ `role` en
  métadonnée). La deuxième option facilite directement le
  sprint 16 (multi-messages provider) — recommandation
  forte de choisir la structure séparée dès le sprint 15.
- **Choix du critère de pagination** : `n` derniers tours par
  timestamp décroissant. Limite par défaut à formaliser
  (probablement 10, héritage de `config.max_history_turns`,
  mais cf. dead config — la valeur doit être justifiée
  fonctionnellement, pas reprise par inertie).

**Pré-requis** : aucun, point de départ.

---

### Sprint 16 (A2) — LLMRouter multi-messages

**Fichiers principalement touchés**

- `llm/llm_router.py` :
  - `_call` : signature étendue pour accepter
    `messages: list[dict]`.
  - `complete` : conserve l'API actuelle `(prompt, role, ...)`
    en interne, devient un wrapper qui empaquette le prompt en
    `[{user: prompt}]` avant délégation.
  - Adaptateurs par provider : format Anthropic
    (`system` à part, alternance stricte user/assistant),
    format OpenAI-like (`messages` complet avec `system` dans
    le tableau), format Gemini (à confirmer — historiquement
    pas dans la routing table actuelle, à vérifier au tour 1).

**Risques identifiés**

- **Hétérogénéité des formats provider** : chaque API a ses
  contraintes :
  - Anthropic exige alternance stricte `user/assistant/user/...`,
    pas deux messages `user` consécutifs ; `system` est un
    champ séparé du tableau `messages`.
  - OpenAI-like (Groq, Mistral, OpenRouter, Cerebras, SambaNova)
    accepte `system` en première position de `messages`, et est
    plus tolérant sur l'alternance.
  - Gemini a son propre format `contents` avec `role: "model"`
    (au lieu de `assistant`).
  Trois adaptateurs à tester individuellement.
- **Compat ascendante critique** : le sprint 16 est livré seul,
  sprint 17 n'arrive qu'au sprint suivant. Pendant cet
  intervalle, tous les appels existants `llm_router.complete(prompt, role=...)`
  doivent continuer à fonctionner identiquement. Le helper wrap
  doit empaqueter le prompt unique en `[{user: prompt}]` de
  façon transparente — aucune régression observable côté
  pipeline existant.
- **Cache négatif 429** : la logique existante
  (`_is_rate_limited`, `_mark_rate_limited`) doit rester
  intacte. À vérifier que les nouveaux chemins multi-messages
  passent par les mêmes branches de gestion d'erreur.

**Pré-requis** : sprint 15 livré (le store existe mais peut
ne pas être branché ; le router peut être testé avec des
messages mockés indépendamment du store).

---

### Sprint 17 (A3) — Branchement bout-en-bout

**Fichiers principalement touchés**

- `core/kernel.py` : appel à `conversation_store.append(...)`
  après production du résultat (côté écriture). Décision à
  prendre au tour 1 du sprint 17 : écriture dans le kernel
  (vue conversation) vs dans `LLMExecutionRouter` (vue intent,
  cohérence avec l'écriture épisodique existante). Le kernel
  est probablement plus juste — la conversation est transverse
  aux opérations cognitives.
- `execution/routers/llm_router.py` (pipeline cognitif, à ne
  pas confondre avec `llm/llm_router.py`) : assemblage des
  messages multi-tours à partir du store, transmission aux
  agents.
- `agents/analyst_agent.py` : retrait du slot
  `HISTORIQUE DE CETTE SESSION` (trompeur), prompt simplifié,
  consommation de l'historique via le nouveau chemin
  multi-messages.
- `agents/planner_agent.py` : à revoir — actuellement reçoit
  uniquement `ctx.result` du précédent agent ; à décider s'il
  doit aussi recevoir l'historique multi-messages ou rester
  sur le résultat synthétisé de l'analyst.
- Potentiellement `agents/executor_agent.py` et
  `agents/critic_agent.py` : à inventorier au tour 1 du sprint
  17 (audit usage actuel et nécessité de l'historique).

**Risques identifiés**

- **Risque de régression maximal du sprint complet** : tout
  se branche en même temps (écriture store + lecture pipeline
  + transmission router + suppression slot). Une régression
  silencieuse — par exemple, l'analyst qui perd l'accès aux
  hits `retrieve_by_intent` sans que cela soit visible en
  tests unitaires — peut casser des opérations qui marchaient
  (PLANNING avec contexte projet, FACT_RECALL avec souvenirs
  vectoriels).
- **Le slot `HISTORIQUE DE CETTE SESSION` étant retiré**,
  vérifier que les opérations qui s'en servaient ne perdent pas
  d'utilité. En pratique l'audit a montré que ce slot était
  trompeur (retrieval vectoriel filtré par intent, pas
  chronologique), donc le retrait devrait être neutre — mais
  il faut s'assurer que l'apport vectoriel équivalent reste
  disponible via `context_block` (ou via une section dédiée si
  utile).
- **Run live obligatoire** : tests unitaires verts ≠ fix
  validé (cf. CLAUDE.md "Tests verts ≠ objectif atteint"). La
  validation finale est un run Telegram live par Nico, sur les
  trois conversations décrites en §4.
- **Compaction prompt** : avec l'historique injecté en
  multi-messages, la taille du payload croît avec le nombre de
  tours. Vérifier que la limite par défaut (cf. sprint 15)
  empêche un débordement de contexte sur les longues
  conversations.

**Pré-requis** : sprints 15 et 16 livrés et tagués (`sprint-15`,
`sprint-16`).

---

### Sprint 18 (A4, optionnel) — Nettoyage périmétrique

**Fichiers principalement touchés**

- `cognition/cognitive_context.py` : revue de
  `MEMORY_TOP_K[CONFIRMATION] = 0`. Maintenant que l'historique
  conversationnel est porté par `aria_conversation`, cette
  valeur peut probablement passer à `2` ou `3` (récupérer
  quelques hits vectoriels pertinents ne sera plus essentiel
  pour la continuité, mais peut ajouter du contexte). Ou
  rester à `0` si la couche conversation suffit — décision à
  prendre.
- `cognition/cognitive_classifier.py` : revue de
  `MIN_MESSAGE_LENGTH = 10`. Cette heuristique servait à éviter
  des intents parasites sur les réponses courtes ; avec le
  contexte conversationnel restauré, certaines réponses
  courtes ("15 août", "Les deux") devraient peut-être
  basculer vers l'opération du tour précédent plutôt que
  vers CONFIRMATION systématique. À trancher.
- `core/event.py` : décision sur `Event.conversation_id` —
  retirer le champ mort (si le sprint 15 a choisi `chat_id`
  brut comme clé) ou le promouvoir (si choix `conversation_id`,
  alors `TelegramInterface` doit l'assigner et le champ devient
  load-bearing).
- `config.py` : retrait de `max_history_turns: int = 10` (dead
  config, identifié dans l'audit) si la limite est désormais
  gérée dans `conversation_store` ; ou réutilisation si la
  valeur fait sens.

**Risques identifiés**

- **Faibles** : c'est du nettoyage post-fix, sur du code mort
  ou des heuristiques devenues secondaires.
- **Seul piège** : ne pas reclasser `MEMORY_TOP_K[CONFIRMATION]`
  ou `MIN_MESSAGE_LENGTH` sans observation prod. Les valeurs
  actuelles, même si conceptuellement liées au bug, ont aussi
  une fonction de garde-fou (éviter intents parasites). Le
  reclassement doit être empirique, pas dogmatique.

**Pré-requis** : sprint 17 livré et validé live ; idéalement
après une période d'observation prod (quelques jours d'usage
réel pour confirmer absence de régression sur l'usage normal).

---

## §4 — Critère global de fin du chantier

La dette **#34** (perte systématique du contexte conversationnel
multi-tour) est considérée résolue quand :

1. Le **sprint 17 est livré** (branche mergée, tag `sprint-17`
   posé).
2. **Validation live** par Nico sur **au moins trois
   conversations multi-tour** distinctes de profils variés :
   - Une conversation avec **réponse courte** type "15 août"
     (le cas canonique du brief sprint 14).
   - Une conversation avec **réponse longue** (plusieurs phrases
     en continuation).
   - Une conversation avec **changement de sujet en milieu de
     conversation** (pour vérifier que le contexte ne sur-influence
     pas et qu'aria sait switcher quand l'utilisateur le fait).

Le **sprint 18 est un polish post-fix**, pas un pré-requis de
clôture du chantier #34. Il peut être livré plus tard (sprint
19 ou ultérieur), ou intégré dans un sprint de maintenance
plus large.
