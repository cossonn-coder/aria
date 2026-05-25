─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 16 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-05-24 (prévisionnel)
**Branche de travail prévue**     : `feat/sprint16-router-multi-messages`
**Tag de référence sortie**       : `sprint-15`
**État sprint 15**                : CLOS. Store conversationnel
  livré standalone (audit
  `docs/sprint15/audit_conversation_store.md`, commit
  `9d81738`), merge sur main via `a19e9aa`, tag `sprint-15`
  pushé. Branche `feat/sprint15-conversation-store` conservée
  localement et sur origin. Une nouvelle dette ouverte (#35).

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 15 (rappel synthétique)

- **Audit cartographique mémoire complet** : 4 writers
  recensés dans `memory/writer.py`, invariant W4 systématique.
  Wings = metadata ChromaDB, pas collections séparées —
  pas de "registration" à faire pour ajouter une wing,
  juste écrire avec le bon `wing` en metadata.
  `MempalaceBridge` strictement lecture jusqu'au sprint 15.
- **Cinq décisions structurantes arbitrées** (audit §11) :
  pas de module `conversation_store.py` séparé ; `chat_id`
  brut sous nom générique `conversation_key: str` ;
  `role/content` séparé ; extension de
  `memory/mempalace_store.py` avec `get_by_metadata` ;
  `room=conversation_key` sans duplication metadata.
- **Code livré inerte** : `write_conversation_turn` ajouté à
  `memory/writer.py` (5e writer), `load_conversation_history`
  ajouté à `MempalaceBridge` avec injection optionnelle de
  `get_by_metadata`, `get_by_metadata` ajouté à
  `memory/mempalace_store.py`. **Aucun caller existant ne
  consomme ces nouvelles fonctions** — le branchement est
  sprint 17.
- **18 tests verts** ajoutés (12 dans `test_writer.py` dont
  un paramétré 6×, 6 dans
  `test_mempalace_bridge_conversation.py`). Suite complète
  236 verts, 0 régression.
- **Discipline préservée** : 4 tours atomiques (audit, fix,
  revue, clôture), aucun fix en dehors du scope, refus
  d'embarquer l'option `--import-mode=importlib` qui
  cassait 3 fichiers de test (dette #35 ouverte à la place).

─────────────────────────────────────────────────────────────────────────

## Cible sprint 16 : A2 — LLMRouter multi-messages

### Objectif

Faire en sorte que `LLMRouter._call` accepte une liste
`messages: list[dict[str, str]]` au format natif provider
(`{"role": "user"|"assistant"|"system", "content": str}`)
et la transmette telle quelle aux providers, au lieu de
construire systématiquement `[{"role": "system", "content":
system_prompt}, {"role": "user", "content": user_prompt}]`.

**Aucun branchement dans le pipeline cognitif** — le
sprint 16 fait de `LLMRouter` une couche capable de porter
l'historique, mais les agents continuent à passer leur
prompt sous l'ancienne forme pendant ce sprint. Le sprint
17 connectera le store conversationnel du sprint 15 au
nouveau format du sprint 16, dans le kernel ou dans une
couche dédiée.

### Livrable principal

`LLMRouter._call` (ou son équivalent dans l'arborescence
`llm/`) accepte une nouvelle signature compatible :

- **Forme courte (legacy, à conserver)** :
  `_call(system_prompt: str, user_prompt: str, ...)` →
  comportement actuel inchangé.
- **Forme longue (nouvelle)** :
  `_call(messages: list[dict], ...)` → transmise
  directement au provider.

Un seul de ces deux formats peut être passé à un appel
donné — `ValueError` si les deux ou aucun.

Plus :
- Vérification provider par provider que le format multi-
  messages est supporté nativement (Mistral, Cerebras,
  Groq, Gemini, SambaNova, OpenRouter, Anthropic — cf.
  `config.py` pour la liste).
- Tests unitaires : forme legacy inchangée, forme messages
  transmise telle quelle (mock provider), erreur si les
  deux signatures sont passées, erreur si aucune.
- Pas de modification d'un seul agent. Pas de modification
  du kernel. Pas de modification du store conversationnel.

### Hors-scope strict

- Aucun appel à `bridge.load_conversation_history` depuis
  un caller existant (sprint 17).
- Aucun retrait du slot `HISTORIQUE DE CETTE SESSION` dans
  `AnalystAgent` (sprint 17).
- Aucune modification de `MEMORY_TOP_K[CONFIRMATION]` ni de
  `MIN_MESSAGE_LENGTH` (sprint 18 optionnel).
- Aucune modification de `core/event.py` (la décision §7.2
  audit sprint 15 maintient `chat_id` brut, pas de
  promotion de `Event.conversation_id`).
- Aucun nettoyage de `config.max_history_turns` ni de
  `Event.conversation_id` (dette à clore sprint 18 si on
  confirme).
- Pas de gestion de fallback inter-providers liée au
  format multi-messages. Si un provider ne supportait pas
  le format (cas non attendu mais à vérifier), traiter en
  dette séparée plutôt qu'en patch dans le sprint.

### Décisions à trancher au tour 1 (audit)

1. **Signature du `_call`** : `_call(*, system_prompt=None,
   user_prompt=None, messages=None, ...)` (params keyword
   exclusifs) versus deux fonctions séparées
   `_call_legacy` + `_call_messages` versus dispatch
   interne `_call(payload)` où `payload` est l'un ou
   l'autre. Recommandation architecte ouverte — arbitrer
   en tour 1 après lecture du code réel et des callers.

2. **Validation côté router ou côté caller** : le router
   refuse-t-il un format `messages` invalide (rôles
   inconnus, content vide, ordre user/assistant
   incohérent) ou laisse-t-il le provider gérer ? Position
   recommandée architecte : validation minimale côté
   router (rôles ∈ {user, assistant, system}, content
   non-None), tout le reste passe au provider. À
   confirmer.

3. **Compatibilité provider** : tous les providers de
   `config.py` (Mistral, Cerebras, Groq, Gemini,
   SambaNova, OpenRouter, Anthropic) acceptent-ils le
   format `messages=[...]` standard ? L'audit doit
   produire une matrice provider × format avec preuve
   adossée au code des wrappers (ou au minimum lien doc
   pinned). Si un provider impose un format propriétaire,
   décider de l'inclure dans le sprint 16 ou de le
   décaler.

### Découpage interne du sprint 16 (prévisionnel)

- **Tour 1 — audit** : cartographie de `LLMRouter`
  actuel (signature, callers, gestion des providers,
  fallback inter-providers en cas de 429 / erreur),
  matrice de compatibilité multi-messages provider par
  provider, arbitrage des trois décisions ci-dessus.
  Audit pur, aucun code écrit.
- **Tour 2 — fix** : modification de `LLMRouter._call`
  pour supporter les deux signatures, validation côté
  router, tests unitaires. Vert sur tests = critère
  intermédiaire.
- **Tour 3 — run live** : ce sprint touche au cœur du
  pipeline LLM, run live obligatoire avant clôture.
  Nico fournit captures Telegram + extraits journalctl
  d'un échange normal (pas de régression sur le
  comportement actuel — la forme legacy est encore
  utilisée par tous les agents). Si bug détecté en
  live, ré-ouverture sur tour 2bis avant clôture.
- **Tour 4 — clôture** : commit, merge, tag sprint-16,
  push. Convention deux commits si nouveau cadrage
  inter-sprints à intégrer ; sinon un seul commit.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-23 (post sprint 15)

| #  | Sujet                                                  | Statut                          |
|----|--------------------------------------------------------|---------------------------------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6)                  | ouverts, non touchés            |
| 17 | Semantic wings non câblées                             | ouvert, architectural           |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 |
| 29 | Path venv `/home/nico/projects/aria/` vs Nextcloud     | DÉCLASSÉE sprint 13             |
| 31 | Drift HNSW mécanique récurrent sur `mempalace_drawers` | ouvert                          |
| 32 | Digression aria Normandie → Belgique                   | REQUALIFIÉE sprint 14, sera résolue par clôture #34 |
| 33 | Garde runbook `"mempalace-fork" in __file__` path-based | ouvert, polish trivial         |
| 34 | **Perte systématique du contexte conversationnel multi-tour** | **OUVERT, EN COURS sprints 15-17** ; sprint 15 (A1) clos |
| 35 | **Structure tests dépendante auto-sys.path classique pytest, empêche `--import-mode=importlib`** | **OUVERT sprint 15**, à traiter sprint refactor tests dédié, hors fil rouge #34 |

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence

Standard ARIA pour ce sprint, avec **une exception** : le
run live tour 3 est obligatoire et non négociable. Le
`LLMRouter` est le cœur du pipeline LLM ; un changement de
signature qui passe les tests unitaires mais casse en prod
fait perdre plusieurs tours de diagnostic. Run live = un
échange Telegram normal après déploiement, captures + log,
validation explicite que le comportement legacy est
intact.

Hors run live : fix qui marche + tests cas nominaux (forme
legacy / forme messages / erreur dual / erreur empty). Pas
de tests sur tous les rôles imaginables, pas de tests
provider-spécifiques (la matrice de compatibilité audit
tour 1 suffit).

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Sept leçons préservées des sprints 10-15, plus une
nouvelle issue du sprint 15 :

8. **Séparation des commits par scope sémantique** —
   sprint 15 a livré deux commits distincts (`docs:
   cadrage inter-sprints 14-15` et `sprint 15: store
   conversationnel`) sur la même branche feature, pour
   préserver la lisibilité du diff au tag. Quand de la
   matière hors-sprint traîne dans l'index au moment de
   clôturer, ne pas la fondre dans le commit sprint —
   commit séparé, scope clair.

Micro-amélioration workflow à acter au prochain push de
branche feature : utiliser `git push -u origin <branch>`
au premier push pour poser le tracking upstream. Coût
négligeable, lisibilité légère de `git branch -vv`. Pas
une dette, juste une convention à adopter.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-15` (commit de merge
  `a19e9aa`, tag `sprint-15` sur ce commit, pushé sur
  origin).
- `feat/sprint15-conversation-store` conservée localement
  et sur origin.
- Branche de travail sprint 16 à créer :
  `feat/sprint16-router-multi-messages` depuis
  `sprint-15`. Premier push avec `-u`.
- Fichiers de référence à lire pour cadrer (Claude Code
  via sa VM, pas re-cités ici) :
  - `docs/sprint14/audit_contexte_conversationnel.md`
    §"LLMRouter" (cause racine côté provider).
  - `docs/sprint14/plan_fix_contexte_conversationnel.md`
    §"Sprint 16" (cadrage A2).
  - `docs/sprint15/audit_conversation_store.md`
    §"Format role/content séparé" (motivation de la
    structure côté store, alignée sur le format
    natif provider sprint 16).
  - `llm/llm_router.py` (et l'arborescence `llm/` plus
    largement) pour tour 1 audit.
  - `config.py` pour la liste des providers à valider.

─────────────────────────────────────────────────────────────────────────