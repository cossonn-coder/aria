# ARIA — Contexte projet pour Claude Code

## Vision
Kernel cognitif personnel local. Single-user (Nico).
Pas un chatbot — un runtime cognitif avec mémoire persistante,
intents, et routing dynamique vers des effecteurs spécialisés.

## Stack
- Python 3.13, venv dans `./venv`
- ChromaDB (MemPalace) pour la mémoire vectorielle
- Telegram Bot comme interface principale
- systemd service `aria.service` sur Debian
- Pas de GPU pour l'instant

## Règles d'architecture INVIOLABLES

1. Une opération = un handler = un seul point d'écriture mémoire.
   Toute écriture passe par memory/writer.py (write_interaction,
   write_image_artifact, write_semantic_fact, write_classifier_cache).
   Wing/room/type sont structurels, posés APRÈS le spread de `extra`,
   jamais surchargeables via metadata. C'est l'anti-régression du
   bug W4 (sprint 3.1 / dette #11).
2. Toute lecture mémoire passe par memory/mempalace_bridge.py (un seul
   point d'accès en lecture). Aucun fichier prod n'importe
   mempalace_store directement.
3. Les agents reçoivent un AgentContext pré-assemblé — ils ne font
   AUCUNE requête mémoire eux-mêmes. Le kernel assemble tout.
4. Les routers retournent {"text": str} ou {"path": str, "caption": str} —
   jamais {"status": ...} (c'est le rôle du dispatcher).
5. Le kernel ne décide rien, n'exécute rien, ne stocke rien.
   Il séquence : classify → dispatch → normalize.
6. CognitiveEngine peut tenir des dépendances injectées (llm_router,
   bridge) mais ne fait pas elle-même de retrieval ni de stockage.
   Elle transmet ses dépendances aux composants stateless qui en
   ont besoin (classify_operation, etc.).

## Couches mémoire

État réel post-sprint-4 :

- `aria_episodic` : interactions, images reçues, images générées.
  Types `interaction|image_input|image_generated`. ~408 entrées.
  Indexé par `intent_id` (room).
- `aria_semantic` : faits stables sur l'utilisateur (allergies,
  localisation, préférences). 0 caller prod actuellement — couche
  d'infrastructure prête mais pas alimentée par le pipeline normal.
  Cf. dette #17 (bloc-note explicite).
- `aria_classifier` : cache du classifier d'opérations.
  ~199 entrées, fonctionnellement cassé depuis sa création
  (mismatch document indexé vs query) — résolu sprint 5
  (commit b0aaee5, dette #20 close).
- `aria_intentual` : réservé intents sérialisés. Pas implémenté.
- `aria` (legacy) : 0 entrée dans `mempalace_drawers`. 32 entrées
  résiduelles dans `mempalace_closets` non migrées (hors scope
  sprint 4, à arbitrer si un usage justifie leur migration).

Layout filesystem du palace, backend chromadb-rust et mécanismes de
quarantine (`.drift-*` / `.corrupt-*`) : voir
`docs/architecture/chromadb_palace.md`.

## Style de code
- Commentaires en français, professionnels et pédagogiques, code en anglais
- Logging via `from logger import get_logger; log = get_logger(__name__)`
- Jamais `print()` en prod — toujours `log.info/warning/error`
- Tests : `pytest tests/ -q` doit toujours passer

## Commandes utiles
- Service : `sudo systemctl restart aria.service`
- Logs : `sudo journalctl -u aria -f -o cat`
- Tests : `cd ~/Nextcloud/projects/aria && pytest tests/ -q`
- Sandbox : `python test/kernel_sandbox.py`

## Convention de tagging git

Un tag `sprint-N` est posé sur le commit de clôture documentaire du
sprint (mise à jour CLAUDE.md + création context_sprint_N+1_kickoff.md),
PAS sur le dernier commit technique. Cela garantit que le tag pointe
sur un état de repo cohérent entre code et documentation. Les commits
techniques se lisent via `git log <tag>~..<tag>` ou `git log
<tag_précédent>..<tag>`.

## Backlog en cours
Voir le doc de contexte complet pour le sprint actuel.
Priorité immédiate : Voir docs/sprint6/context_sprint_6_kickoff_v2.md pour la priorité actuelle.

## Ne JAMAIS faire
- Modifier `soul.md` sans demander explicitement à Nico
- Bypasser le kernel pour appeler un router directement
- Faire écrire la mémoire par un agent ou un client LLM
- Utiliser `print()` à la place du logger
- Lancer `git push` sans confirmation
- Modifier le prompt AnalystAgent sans faire passer le test garde-fou
  tests/agents/test_analyst_prompt_guard.py

## Protocole de délégation DeepSeek – Économie de tokens

> Ces règles priment sur toute autre consigne.

---

### Outils disponibles

| Outil | Rôle |
|---|---|
| `write-deepseek` | Génération de boilerplate (tests, docstrings, scaffolding) |
| `extract-chat` | Extraction de transcript avant mise à jour doc |
| `ask-deepseek` | Lecture et analyse multi-fichiers |

**Chemins :** `/home/nico/.local/bin/<outil>`

---

### Vérification en début de session

À exécuter automatiquement, sans attendre de demande :

```bash
ls -la /home/nico/.local/bin/ask-deepseek \
        /home/nico/.local/bin/write-deepseek \
        /home/nico/.local/bin/extract-chat
```

---

### 1. `write-deepseek` – Génération de boilerplate

#### Déclencheurs automatiques

Exécuter immédiatement (sans demander) dans ces situations :

- Générer un **fichier de tests pytest** pour un module existant
- Ajouter des **docstrings** à toutes les fonctions publiques d'un fichier
- Créer un **nouveau handler / routeur** en suivant un pattern existant
- Mettre à jour la **documentation** après une session (voir §4)

#### Syntaxe

```bash
/home/nico/.local/bin/write-deepseek \
  --spec "<description précise>" \
  --context <fichier_reference> \
  --target <fichier_sortie>
```

#### Exemple – Ajouter des tests

**Demande :** *« Ajoute des tests pour `src/mavlink_parser.py` »*

```bash
/home/nico/.local/bin/write-deepseek \
  --spec "Génère un fichier pytest complet pour src/mavlink_parser.py, testant toutes les fonctions publiques" \
  --context src/mavlink_parser.py \
  --target tests/test_mavlink_parser.py
```

---

### 2. `ask-deepseek` – Lecture multi-fichiers
Les tours d'audit pré-fix (audit avant fix) sortent du déclenchement automatique d'ask-deepseek. Claude Code lit directement les fichiers et retourne leur contenu intégral. Si le brief mentionne 'audit' ou demande explicitement le contenu brut, le protocole de délégation est suspendu pour ce tour.

#### Déclencheurs automatiques

- Lire **≥ 1 fichier de plus de 300 lignes**
- Lire **≥ 3 fichiers**, quelle que soit leur taille
- Comprendre des **interactions entre modules**

#### Syntaxe

```bash
# Sans raisonnement
/home/nico/.local/bin/ask-deepseek \
  --paths <fichier1> <fichier2> ... \
  --question "<question>"

# Avec raisonnement approfondi
/home/nico/.local/bin/ask-deepseek \
  --paths <fichier1> <fichier2> ... \
  --question "<question>" \
  --think
```

L'outil retourne un texte structuré (~300–500 tokens) à lire à la place des fichiers bruts.

#### Exemple – Question sur plusieurs fichiers

**Demande :** *« Quel port utilise le module telemetry ? »* (avec ≥ 3 fichiers concernés)

```bash
/home/nico/.local/bin/ask-deepseek \
  --paths src/telemetry.py src/config.py src/main.py \
  --question "Quel port utilise le module telemetry ?"
```

---

### 3. `extract-chat` – Préparation pour la documentation

#### Déclencheur

Avant chaque mise à jour de documentation, après une session de travail.

#### Syntaxe

```bash
/home/nico/.local/bin/extract-chat \
  ~/.claude/projects/aria/<session>.jsonl \
  -o /tmp/chat.txt
```

> Ne jamais lire un fichier `.jsonl` brut – toujours passer par `extract-chat`.

---

### 4. Workflow de mise à jour de la documentation

À exécuter **après chaque feature terminée**, automatiquement :

```bash
# 1. Extraire le transcript de la session courante
/home/nico/.local/bin/extract-chat \
  ~/.claude/projects/aria/$(ls -t ~/.claude/projects/aria/ | head -1) \
  -o /tmp/chat.txt

# 2. Mettre à jour l'architecture via DeepSeek
/home/nico/.local/bin/write-deepseek \
  --spec "Synchronise docs/architecture.md avec les changements listés dans /tmp/chat.txt" \
  --context docs/architecture.md \
  --target docs/architecture.md
```

#### Exemple – Fin de feature

**Demande :** *« On a fini la feature, mets à jour la doc »*

```bash
/home/nico/.local/bin/extract-chat \
  ~/.claude/projects/aria/$(ls -t ~/.claude/projects/aria/ | head -1) \
  -o /tmp/chat.txt

/home/nico/.local/bin/write-deepseek \
  --spec "Synchronise docs/architecture.md avec les changements listés dans /tmp/chat.txt" \
  --context docs/architecture.md \
  --target docs/architecture.md
```

---

### 5. Répartition des responsabilités

| Tâche | Responsable |
|---|---|
| Déboguer une race condition | **Claude** |
| Décision d'architecture | **Claude** |
| Lire 5 fichiers pour trouver un port | **DeepSeek** via `ask-deepseek` |
| Générer un fichier de tests | **DeepSeek** via `write-deepseek` |
| Mettre à jour la doc après une session | **DeepSeek** via `extract-chat` + `write-deepseek` |
| Scaffolding d'un nouveau handler | **DeepSeek** via `write-deepseek` |

---

### 6. Interdictions

- Ne **jamais** générer soi-même un fichier de tests, des docstrings ou du code de structure.
- Ne **jamais** répondre à une question nécessitant la lecture de ≥ 3 fichiers sans `ask-deepseek`.
- Ne **jamais** ouvrir ou lire directement un fichier `.jsonl` : utiliser `extract-chat`.
- Ne **jamais** produire du code boilerplate dans les messages de réponse.
