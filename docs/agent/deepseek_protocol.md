# Protocole de délégation DeepSeek – Économie de tokens

> Ces règles priment sur toute autre consigne.

---

## Outils disponibles

| Outil | Rôle |
|---|---|
| `write-deepseek` | Génération de boilerplate (tests, docstrings, scaffolding) |
| `extract-chat` | Extraction de transcript avant mise à jour doc |
| `ask-deepseek` | Lecture et analyse multi-fichiers |

**Chemins :** `/home/nico/.local/bin/<outil>`

---

## Vérification en début de session

À exécuter automatiquement, sans attendre de demande :

```bash
ls -la /home/nico/.local/bin/ask-deepseek \
        /home/nico/.local/bin/write-deepseek \
        /home/nico/.local/bin/extract-chat
```

---

## 1. `write-deepseek` – Génération de boilerplate

### Déclencheurs automatiques

Exécuter immédiatement (sans demander) dans ces situations :

- Générer un **fichier de tests pytest** pour un module existant
- Ajouter des **docstrings** à toutes les fonctions publiques d'un fichier
- Créer un **nouveau handler / routeur** en suivant un pattern existant
- Mettre à jour la **documentation** après une session (voir §4)

### Syntaxe

```bash
/home/nico/.local/bin/write-deepseek \
  --spec "<description précise>" \
  --context <fichier_reference> \
  --target <fichier_sortie>
```

### Exemple – Ajouter des tests

**Demande :** *« Ajoute des tests pour `src/mavlink_parser.py` »*

```bash
/home/nico/.local/bin/write-deepseek \
  --spec "Génère un fichier pytest complet pour src/mavlink_parser.py, testant toutes les fonctions publiques" \
  --context src/mavlink_parser.py \
  --target tests/test_mavlink_parser.py
```

---

## 2. `ask-deepseek` – Lecture multi-fichiers

Les tours d'audit pré-fix (audit avant fix) sortent du déclenchement automatique d'ask-deepseek. Claude Code lit directement les fichiers et retourne leur contenu intégral. Si le brief mentionne 'audit' ou demande explicitement le contenu brut, le protocole de délégation est suspendu pour ce tour.

### Déclencheurs automatiques

- Lire **≥ 1 fichier de plus de 300 lignes**
- Lire **≥ 3 fichiers**, quelle que soit leur taille
- Comprendre des **interactions entre modules**

### Syntaxe

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

### Exemple – Question sur plusieurs fichiers

**Demande :** *« Quel port utilise le module telemetry ? »* (avec ≥ 3 fichiers concernés)

```bash
/home/nico/.local/bin/ask-deepseek \
  --paths src/telemetry.py src/config.py src/main.py \
  --question "Quel port utilise le module telemetry ?"
```

---

## 3. `extract-chat` – Préparation pour la documentation

### Déclencheur

Avant chaque mise à jour de documentation, après une session de travail.

### Syntaxe

```bash
/home/nico/.local/bin/extract-chat \
  ~/.claude/projects/aria/<session>.jsonl \
  -o /tmp/chat.txt
```

> Ne jamais lire un fichier `.jsonl` brut – toujours passer par `extract-chat`.

---

## 4. Workflow de mise à jour de la documentation

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

### Exemple – Fin de feature

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

## 5. Répartition des responsabilités

| Tâche | Responsable |
|---|---|
| Déboguer une race condition | **Claude** |
| Décision d'architecture | **Claude** |
| Lire 5 fichiers pour trouver un port | **DeepSeek** via `ask-deepseek` |
| Générer un fichier de tests | **DeepSeek** via `write-deepseek` |
| Mettre à jour la doc après une session | **DeepSeek** via `extract-chat` + `write-deepseek` |
| Scaffolding d'un nouveau handler | **DeepSeek** via `write-deepseek` |

---

## 6. Interdictions

- Ne **jamais** générer soi-même un fichier de tests, des docstrings ou du code de structure.
- Ne **jamais** répondre à une question nécessitant la lecture de ≥ 3 fichiers sans `ask-deepseek`.
- Ne **jamais** ouvrir ou lire directement un fichier `.jsonl` : utiliser `extract-chat`.
- Ne **jamais** produire du code boilerplate dans les messages de réponse.
