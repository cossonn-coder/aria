─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 15 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-23
**Branche de travail prévue** : `feat/sprint15-conversation-store`
**Tag de référence sortie sprint 14** : `sprint-14`
**État sprint 14** : CLOS. Audit cartographique livré
  (`docs/sprint14/audit_contexte_conversationnel.md`, 1271
  lignes, commit `9c949bd`) + plan de fix multi-sprints
  (`docs/sprint14/plan_fix_contexte_conversationnel.md`, 308
  lignes, commit `0603715`), mergés sur main via commit
  `666b18c`, tag `sprint-14` posé et pushé. Branche
  `feat/sprint14-context-continuity` conservée localement et
  sur origin (convention respectée). Dette #34 (perte
  systématique du contexte conversationnel multi-tour)
  formellement ouverte, plan de fix en quatre sous-sprints
  (15, 16, 17, 18 optionnel) acté.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 14 (rappel synthétique)

- **Diagnostic structurel établi sans incertitude** (audit
  §6) : la perte de contexte conversationnel n'est pas un bug
  d'une fonction défectueuse, c'est l'absence complète d'un
  mécanisme. `Event.conversation_id` est déclaré mais jamais
  assigné, `config.max_history_turns=10` est dead config sans
  caller, `LLMRouter._call` envoie strictement `[system, user]`
  au provider. Aucun chargement d'historique chronologique
  n'existe dans le repo. Le slot `HISTORIQUE DE CETTE SESSION`
  du `AnalystAgent` est trompeur — il reçoit un retrieval
  vectoriel filtré par `intent_id`, pas un dialogue
  chronologique.
- **Amplificateurs identifiés** sur messages courts :
  `MEMORY_TOP_K[CONFIRMATION]=0` coupe tout retrieval global,
  `MIN_MESSAGE_LENGTH=10` shortcut toute réponse brève vers
  CONFIRMATION avant cache et LLM, `intent_id` ré-résolu par
  cosine pur à chaque tour rend le regroupement épisodique
  fragile sur les continuations courtes.
- **Décision architecturale actée** (plan §1) : approche A
  (multi-messages format natif provider) avec store wing
  MemPalace dédiée `aria_conversation`. Approches B
  (sérialisation prompt unique) et C (hybride par opération)
  écartées avec raison documentée. Stores RAM (perte au
  restart), dérivation `aria_episodic` (pollue sémantique
  vectorielle), fichier JSON (incohérent avec architecture
  mémoire) écartés.
- **Découpage en quatre sous-sprints acté** (plan §2) :
  sprint 15 = store conversationnel, sprint 16 = LLMRouter
  multi-messages, sprint 17 = branchement bout-en-bout +
  validation live, sprint 18 = nettoyage périmétrique
  optionnel.
- **Discipline préservée** : aucun fix dans le sprint 14,
  scope strictement diagnostic + planification, malgré la
  tentation de toucher au code (le bug est visible à chaque
  interaction Telegram). Calibrage no-pivot tenu.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 15 : A1 — Store conversationnel

### Objectif

Créer le module qui stocke et restitue chronologiquement les
tours d'une conversation, prêt à être consommé par les sprints
16 (router multi-messages) et 17 (branchement pipeline).
**Aucun branchement dans le pipeline existant** — le store
est livré standalone, testé unitairement, mais inerte côté
runtime jusqu'au sprint 17.

### Livrable principal

Module `memory/conversation_store.py` avec API minimale :
- `append(conversation_key, role, content)` — ajoute un tour à
  une conversation.
- `load(conversation_key, n)` — retourne les `n` derniers tours
  par ordre chronologique croissant (oldest → newest), prêt à
  être passé en `messages` au provider.

Plus :
- Création de la wing `aria_conversation` dans MemPalace
  (registration équivalente aux wings existantes
  `aria_episodic`, `aria_semantic`, `aria_classifier`).
- Méthodes correspondantes sur `MempalaceBridge` :
  `write_conversation_turn` et `load_conversation_history`,
  qui délèguent au `conversation_store`.
- Tests unitaires couvrant : append simple, append multiple,
  load avec `n` plafonnant, load sur conversation vide,
  séparation entre deux `conversation_key` distincts.

### Hors-scope strict

- Aucune modification de `core/event.py`, `core/kernel.py`,
  `llm/llm_router.py`, ni d'aucun agent.
- Aucune modification de `TelegramInterface`.
- Aucun appel au store depuis le pipeline cognitif existant.
- Aucune décision sur le slot `HISTORIQUE DE CETTE SESSION` —
  c'est le sprint 17 qui le retire.
- Aucune décision sur `MEMORY_TOP_K[CONFIRMATION]` ou
  `MIN_MESSAGE_LENGTH` — c'est le sprint 18 optionnel.

### Décisions à trancher au tour 1 (audit)

Deux décisions structurantes que le plan sprint 14 a flaggées
explicitement et qui doivent être tranchées avant tout code :

1. **Choix de la clé d'indexation** : `chat_id` Telegram brut
   (simple, mais couple le store au transport) versus
   `Event.conversation_id` promu en champ load-bearing (plus
   propre, demande de toucher `core/event.py` et
   `TelegramInterface` au sprint 17 mais pas avant).
   Recommandation architecte ouverte — à arbitrer en tour 1
   après lecture du code réel.

2. **Format de stockage du turn** : texte concaténé
   `USER:\n...\n\nARIA:\n...` (calqué sur l'actuel
   `write_interaction` qui écrit dans `aria_episodic`) versus
   structure `role/content` séparée (une entrée par tour avec
   `role` en métadonnée ChromaDB). **Recommandation forte
   architecte : structure séparée**, plan §3 sprint 15. Ça
   évite un re-parsing texte au sprint 16 (router
   multi-messages) et s'aligne directement sur le format natif
   provider. À confirmer en tour 1 que ChromaDB supporte
   proprement le filtrage par metadata `role` et le tri
   chronologique par metadata `timestamp`.

### Découpage interne du sprint 15 (prévisionnel)

- **Tour 1 — audit** : cartographie de l'écriture mémoire
  actuelle (`memory/writer.py`, `MempalaceBridge`,
  registration des wings existantes dans MemPalace), arbitrage
  des deux décisions ci-dessus avec preuve étayée par le code
  lu. Audit pur, aucun code écrit.
- **Tour 2 — fix** : implémentation du `conversation_store`,
  des méthodes bridge, registration de la wing, tests
  unitaires. Vert sur tests = critère de fin.
- **Tour 3 — clôture** : merge sur main, tag `sprint-15`,
  push.

Bonus de clôture envisageable si la fenêtre tient : #33 garde
runbook `"mempalace-fork" in __file__` path-based (effort
très bas, pas lié au sprint mais agrégeable). À décider en
clôture, pas en ouverture.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-23 (post sprint 14)

| #  | Sujet                                                  | Statut                          |
|----|--------------------------------------------------------|---------------------------------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6)                  | ouverts, non touchés            |
| 17 | Semantic wings non câblées                             | ouvert, architectural           |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 (backlog "à confirmer" à reprendre) |
| 29 | Path venv `/home/nico/projects/aria/` vs Nextcloud     | DÉCLASSÉE sprint 13             |
| 31 | Drift HNSW mécanique récurrent sur `mempalace_drawers` | ouvert, candidat structurel multi-sprints |
| 32 | Digression aria Normandie → Belgique                   | **REQUALIFIÉE sprint 14** comme symptôme de #34 ; sera résolue par clôture #34 |
| 33 | Garde runbook §6 `"mempalace-fork" in __file__` path-based | ouvert, polish trivial agrégeable |
| 34 | **Perte systématique du contexte conversationnel multi-tour** | **OUVERT, EN COURS sprint 15-17** (plan §2-§4 sprint 14) |

─────────────────────────────────────────────────────────────────────────

## Backlog résiduel #26 (toujours en attente d'arbitrage Nico)

Inchangé depuis sprints 12-14. À reprendre en bordure d'un
sprint qui touche au palace. Le sprint 15 touche au palace
(création wing `aria_conversation`) mais reste cadré
strictement sur cette création — pas le moment d'arbitrer #26
sauf si l'audit tour 1 révèle un blocage croisé. Liste
détaillée dans kickoff sprint 13 §"Backlog résiduel #26",
non re-citée.

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Inchangé depuis sprint 8 : **fix qui marche + 1 test de
non-régression sur le cas nominal, rien de plus**. Pour le
sprint 15, ça veut dire : tests unitaires couvrant les cas
nominaux du store (append, load, séparation des conversations),
pas de tests exhaustifs sur tous les edge cases imaginables
(concurrence multi-process, palette de roles exotiques,
volumétrie extrême — tout ça relève du sprint 17 ou plus tard
selon nécessité observée).

**Exception réactivée** : le sprint 15 crée une nouvelle wing
dans le palace prod. Si l'audit tour 1 révèle que la création
de wing nécessite des manipulations sur le palace prod existant
(migration de schéma, re-registration), basculer en mode
prudent. Sinon, calibrage normal.

Validation supplémentaire sprint 14 : la discipline a permis
de **refuser le fix immédiat** sous pression d'un bug visible
à chaque interaction Telegram, en restant sur le diagnostic
puis la planification. À reproduire — le sprint 15 doit livrer
le store standalone, pas commencer à brancher quoi que ce soit.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Six leçons préservées des sprints 10-14 :

1. **Test discriminant before/after avec preuve causale** —
   sprint 10 tour 2b.
2. **Refus du mélange de scope malgré découverte adjacente** —
   sprint 11 tour 2, sprint 13 tour micro-audit, sprint 14
   refus du fix immédiat malgré bug visible.
3. **Reconnaître l'outil structurellement inadéquat** — `lsof`
   sur chromadb-rust, cf. `docs/architecture/chromadb_palace.md`.
4. **Brief atomique = un objectif, un livrable.** Sprint 14
   trois tours atomiques séparés (audit / plan / merge),
   chaque livrable validé avant le suivant.
5. **Diagnostic structurel avant fix** — sprint 13 #28 (SHA
   fork vs PyPI), sprint 14 #34 (cartographie complète avant
   plan multi-sprints). Sans audit, on aurait probablement
   tenté un fix ponctuel sur la digression Belgique qui aurait
   raté la cause racine.
6. **Reconnaître un symptôme comme tel** — sprint 14 a
   correctement requalifié #32 (digression) comme symptôme de
   #34 (perte contexte). Le bug observé n'est pas toujours le
   bug à fixer ; la cible peut être plus profonde.

Une leçon nouvelle sprint 14 :

7. **Découpage multi-sprints quand le fix touche plusieurs
   couches** — quand un fix unique nécessiterait des
   modifications simultanées de plusieurs couches (router LLM,
   format prompt agents, store mémoire, kernel), découper en
   sous-sprints atomiques où chaque livrable est testable et
   mergeable indépendamment. Évite les sprints fleuves
   ingérables et permet diagnostic en cas de régression.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-14` (commit de merge `666b18c`,
  tag `sprint-14` sur ce commit, pushé sur origin).
- `feat/sprint14-context-continuity` conservée localement et
  sur origin.
- Branche de travail sprint 15 à créer : `feat/sprint15-
  conversation-store` depuis `sprint-14`.
- Fichiers de référence à lire pour cadrer (Claude Code via sa
  VM, pas re-cités ici) :
  - `docs/sprint14/audit_contexte_conversationnel.md` (diagnostic
    complet de la cause racine).
  - `docs/sprint14/plan_fix_contexte_conversationnel.md` (plan
    multi-sprints, §3 sprint 15 spécifiquement pour cadrer A1).
  - `memory/writer.py`, `memory/mempalace_bridge.py`,
    `core/event.py` pour le tour 1 audit.

─────────────────────────────────────────────────────────────────────────