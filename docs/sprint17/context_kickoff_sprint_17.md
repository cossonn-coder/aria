─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 17 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-05-26 (prévisionnel)
**Branche de travail prévue**     : `feat/sprint17-conversation-wiring`
**Tag de référence sortie**       : `sprint-16`
**État sprint 16**                : CLOS. LLMRouter signature
  multi-messages livrée standalone (audit
  `docs/sprint16/audit_llm_router.md`, commit `846a028`),
  merge sur main via `1fc6a39`, tag `sprint-16` pushé.
  Branche `feat/sprint16-router-multi-messages` conservée
  localement et sur origin. Aucune nouvelle dette ouverte.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 16 (rappel synthétique)

- **Audit cartographique LLMRouter complet** :
  signature publique `complete(prompt, role, temperature,
  max_tokens)`, dispatch HTTP inliné dans `_call` avec
  unique branche conditionnelle `if provider == "anthropic"`.
  Pas de wrappers par provider. System prompt construit
  une fois au module-load depuis `_SOUL` + `_USER`, aucun
  caller ne le surcharge.
- **Recadrage factuel** du brief initial qui parlait d'une
  signature `_call(system_prompt, user_prompt, ...)` qui
  n'existe pas. L'évolution a porté sur `complete()`, pas
  sur `_call()`.
- **Providers concernés** : Mistral, Groq×3, Cerebras,
  OpenRouter, Anthropic. Gemini et SambaNova absents de
  `ROUTING_TABLE` malgré leur config présente — hors-scope,
  pas de dette à ouvrir.
- **Signature livrée** : `complete(prompt=None, *,
  messages=None, role, temperature, max_tokens)`. Xor
  strict, ValueError si les deux ou aucun. Validation
  minimale via `_validate_messages` (rôle ∈ {user, assistant,
  system}, content `str` non vide).
- **Conversion Anthropic** : extraction des `{role:system}`
  → param `system` top-level concaténé `\n\n`. Clé `system`
  omise du payload si zéro system message (pas de chaîne
  vide).
- **Décision design critique** : en forme messages, le
  router **n'injecte ni `_SOUL` ni `_USER`**. Le caller
  assume la responsabilité du system prompt complet. C'est
  le cœur du travail sprint 17.
- **10 tests** ajoutés (`tests/llm/test_llm_router_messages.py`),
  suite complète 246 verts, 0 régression.
- **Run live validé** : 3 échanges Telegram normaux (CHAT
  court, PLANNING, REASONING), identité ARIA préservée
  (tutoiement, ton direct, contextualisation Grenoble issue
  de `_USER`), zéro ValueError dans journalctl.
- **Discipline préservée** : 4 tours atomiques (audit, fix,
  run live, clôture), aucune dérive de scope, aucun caller
  prod modifié — le sprint 16 a livré une couche inerte
  parfaitement, prête pour le branchement sprint 17.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 17 : A3 — Branchement caller (fil rouge #34 clos)

### Objectif

Faire en sorte qu'`AnalystAgent` charge l'historique
conversationnel via `MempalaceBridge.load_conversation_history`
(livré sprint 15, inerte), construise un `messages=[...]`
au format natif provider, et appelle `LLMRouter.complete`
en forme messages (livrée sprint 16) au lieu de la forme
prompt unique actuelle.

À l'issue du sprint 17, le fil rouge #34 (perte
systématique du contexte conversationnel multi-tour) est
**clos** : ARIA garde naturellement le fil d'une
conversation Telegram, via le store conversationnel
existant et le canal messages natif des providers.

### Livrable principal

`AnalystAgent.process` (ou son équivalent dans l'arborescence
`agents/`) modifié pour :

1. **Charger l'historique** : appel à
   `bridge.load_conversation_history(conversation_key=..., limit=N)`
   où `conversation_key` provient du context cognitif
   (`ctx.event.chat_id` ou équivalent, à arbitrer en tour 1).
   `N` = `config.max_history_turns` par défaut (déjà à 10,
   cf. `config.py`).

2. **Construire le system prompt explicite** : assembler
   `_SOUL` + `_USER` + le slot `CONTEXTE COGNITIF` (intent,
   session_memory, context_block) **côté caller**, puisque
   le router n'injecte plus rien en forme messages. Le slot
   `HISTORIQUE DE CETTE SESSION` du prompt actuel **disparaît**
   — il est remplacé par les messages natifs eux-mêmes.

3. **Construire la liste messages** :
   `[{role:system, content:<system_prompt>}, ...<history>, {role:user, content:<message courant>}]`
   où `<history>` est la liste retournée par
   `load_conversation_history` (format `[{role, content}, ...]`,
   ordre chronologique).

4. **Appeler `complete(messages=...)`** au lieu de
   `complete(prompt=...)`. Les autres params (role,
   temperature, max_tokens) inchangés.

### Hors-scope strict

- Pas de modification de `planner_agent.py`,
  `cognitive_classifier.py`, `intent_namer.py`. Ces 3
  callers traitent du transactionnel sans historique
  conversationnel — pas de valeur ajoutée à les migrer.
  Restent en forme legacy.
- Pas de modification de `LLMRouter` (livré sprint 16,
  validé en prod).
- Pas de modification de `core/event.py` (la décision
  audit sprint 15 §7.2 maintient `chat_id` brut sous
  `conversation_key`, pas de promotion de
  `Event.conversation_id`).
- Pas de cleanup de `config.max_history_turns` ni de
  `Event.conversation_id` (dette à clore sprint 18 si on
  confirme).
- Pas de modification de `MempalaceBridge.load_conversation_history`
  (livré sprint 15, validé par tests unitaires).
- Pas de modification de `write_conversation_turn` (le
  writer du sprint 15) — il continue d'être appelé à
  l'endroit actuel.
- Pas de gestion de cas "première conversation, historique
  vide" autre que : `load_conversation_history` retourne
  `[]`, `messages` ne contient alors que system + user
  courant. Comportement nominal, pas de cas spécial.

### Décisions à trancher au tour 1 (audit)

1. **Source de `conversation_key`** : `ctx.event.chat_id` ?
   Quelque chose dans `ctx.metadata` ? Présent sur tous les
   events qui atteignent `AnalystAgent` ? L'audit doit
   confirmer la disponibilité et le format exact, et
   décider si on passe via une property/helper ou en
   accédant directement à l'attribut.

2. **Construction du system prompt côté caller** : assemblage
   inline dans `AnalystAgent.process`, ou helper dédié
   (probablement `agents/_system_prompt.py` ou méthode privée
   `_build_system_prompt`) ? L'audit doit identifier si
   d'autres agents pourraient bénéficier du même helper à
   l'avenir (sprint 18+) ou si c'est `AnalystAgent`-spécifique.

3. **Slot `CONTEXTE COGNITIF`** : reste-t-il dans le system
   prompt (cohérent avec son rôle "contexte permanent du
   tour") ou bascule-t-il dans le premier user message
   (séparation system=identité / user=contexte+question) ?
   Position architecte par défaut : **dans le system prompt**,
   parce que la session_memory et le context_block sont des
   méta-informations sur le tour, pas des messages
   conversationnels. À confirmer après lecture du code
   actuel.

4. **Quoi charger comme historique** :
   `load_conversation_history` retourne quoi exactement,
   dans quel ordre, avec quelle profondeur par défaut ?
   L'audit doit citer le code intégral de la fonction
   sprint 15 et vérifier que son contrat correspond au
   besoin caller (rôles, content `str`, ordre chronologique).

5. **Écriture du tour courant** : à quel moment exact
   `write_conversation_turn` est-il appelé aujourd'hui ?
   Avant ou après la réponse LLM ? L'historique chargé
   au tour T+1 doit-il inclure le tour T (réponse comprise)
   ou s'arrêter au tour T-1 ? Position architecte : inclure
   T-1 et antérieurs, le tour T courant est le `{role:user}`
   final qu'on ajoute manuellement à la liste. La réponse
   Aria du tour T sera persistée APRÈS l'appel `complete`,
   exactement comme aujourd'hui. À confirmer.

### Découpage interne du sprint 17 (prévisionnel)

- **Tour 1 — audit** : cartographie d'`AnalystAgent.process`
  actuel (code intégral), du flux `Event` → `ctx` (où vit
  `chat_id`), du contrat exact de
  `load_conversation_history` et `write_conversation_turn`
  livrés sprint 15. Arbitrage des cinq décisions ci-dessus.
  Audit pur, aucun code écrit.

- **Tour 2 — fix** : modification de `AnalystAgent.process`,
  helper `_build_system_prompt` si arbitré, tests unitaires.
  La fixture `mock_network` de `conftest.py` continue de
  fonctionner mais devra peut-être être étendue pour mocker
  `load_conversation_history` côté tests `AnalystAgent`.

- **Tour 3 — run live OBLIGATOIRE** : critique. Ce sprint
  change le comportement observable d'ARIA. Run live =
  conversation Telegram multi-tour qui démontre que le
  contexte est conservé. Nico fournit captures + journalctl.
  Test naturel : poser une question dans le tour 1, poser
  une question de suivi dans le tour 2 ("et pour le tour
  précédent ?", "tu me disais quoi déjà ?") — Aria doit
  répondre avec mémoire du contexte. Si elle "redémarre"
  comme actuellement → bug.

- **Tour 4 — clôture** : commit, merge, tag sprint-17, push.
  Convention deux commits si nouveau cadrage à intégrer ;
  sinon un seul.

### Critère de clôture du fil rouge #34

Le run live tour 3 doit démontrer **un échange à au moins
3 tours** où Aria fait clairement référence à un échange
antérieur sans que Nico ait dû le re-citer dans son message
courant. Si ce critère est validé, dette #34 fermée
explicitement dans le tableau de dettes sprint 18.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-25 (post sprint 16)

| #  | Sujet                                                  | Statut                          |
|----|--------------------------------------------------------|---------------------------------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6)                  | ouverts, non touchés            |
| 17 | Semantic wings non câblées                             | ouvert, architectural           |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 |
| 29 | Path venv `/home/nico/projects/aria/` vs Nextcloud     | DÉCLASSÉE sprint 13             |
| 31 | Drift HNSW mécanique récurrent sur `mempalace_drawers` | ouvert, observé encore sprint 16 run live |
| 32 | Digression aria Normandie → Belgique                   | REQUALIFIÉE sprint 14, sera résolue par clôture #34 sprint 17 |
| 33 | Garde runbook `"mempalace-fork" in __file__` path-based | ouvert, polish trivial         |
| 34 | **Perte systématique du contexte conversationnel multi-tour** | **OUVERT, EN COURS sprints 15-17** ; A1 (15) clos, A2 (16) clos, A3 (17) cible de ce sprint |
| 35 | Structure tests dépendante auto-sys.path classique pytest, empêche `--import-mode=importlib` | ouvert, hors fil rouge #34 |

Note dette #36 candidate : `LLMRouter.route()` (lignes
330-349 de `llm/llm_router.py`) inerte, non appelée nulle
part en prod, vestige non documenté. À ouvrir formellement
en clôture sprint 17 si on confirme — pas dans le périmètre
sprint 17 lui-même.

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence

Standard ARIA pour ce sprint, avec **deux exceptions** :

1. **Run live tour 3 obligatoire et discriminant**. C'est le
   sprint qui valide ou invalide tout le fil rouge #34.
   Validation = échange Telegram multi-tour où Aria conserve
   le contexte. Pas de "vert sur tests = OK", les tests ne
   peuvent pas démontrer une conversation continue.

2. **Audit tour 1 plus exigeant que d'habitude** sur deux
   points : (a) le contrat exact de
   `load_conversation_history` et `write_conversation_turn`
   (re-lecture intégrale, pas confiance au commit message
   sprint 15), et (b) la construction du system prompt côté
   caller, qui est le seul vrai design new de ce sprint.

Hors run live et audit : fix qui marche + tests cas nominaux
(historique vide / historique présent / multi-tour avec
contexte). Pas de tests provider-spécifiques (la matrice
sprint 16 suffit). Pas de fixtures synthétiques exhaustives.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Huit leçons préservées des sprints 10-16, plus une nouvelle
issue du sprint 16 :

9. **Le brief architecte peut se tromper sur la réalité du
   code** — sprint 16 a vu deux postulats faux du brief tour
   1 (signature `_call(system_prompt, user_prompt)`
   inexistante, dossier `wrappers/` inexistant). L'audit
   Claude Code a correctement réfuté et proposé la voie
   conforme au code réel. À maintenir : exiger systématiquement
   en tour 1 le code intégral des fonctions concernées,
   ne pas accepter de paraphrase, et adopter la proposition
   contre-architecte quand elle est factuellement argumentée.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-16` (commit de merge
  `1fc6a39`, tag `sprint-16` sur ce commit, pushé sur
  origin).
- `feat/sprint16-router-multi-messages` conservée localement
  et sur origin.
- Branche de travail sprint 17 à créer :
  `feat/sprint17-conversation-wiring` depuis `sprint-16`.
  Premier push avec `-u`.
- Fichiers de référence à lire pour cadrer (Claude Code via
  sa VM, pas re-cités ici) :
  - `docs/sprint14/audit_contexte_conversationnel.md`
    §"Symptôme observable" (cause racine côté caller).
  - `docs/sprint14/plan_fix_contexte_conversationnel.md`
    §"Sprint 17" (cadrage A3).
  - `docs/sprint15/audit_conversation_store.md` §11
    (les cinq décisions sprint 15 dont la structure
    `role/content` séparé qui s'aligne sur le format natif
    sprint 16 et qu'on consomme ici).
  - `docs/sprint16/audit_llm_router.md` §3.a (le slot
    `HISTORIQUE DE CETTE SESSION` dans `AnalystAgent`
    candidat naturel à migrer) et §9.a.
  - `agents/analyst_agent.py` (cible principale tour 2).
  - `memory/writer.py` (`write_conversation_turn` sprint 15).
  - `memory/mempalace_bridge.py` (`load_conversation_history`
    sprint 15).
  - `core/event.py` et `cognition/cognitive_context.py`
    pour le flux `chat_id` → ctx.

─────────────────────────────────────────────────────────────────────────