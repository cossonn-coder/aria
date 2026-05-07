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

## Délégation DeepSeek V4 Flash — Économie de tokens

Ces outils sont dans `~/.local/bin/` (sur le PATH). Les utiliser **sans
demander** dès que les critères ci-dessous sont remplis.

### `ask-deepseek` — Lecture de fichiers volumineux

```bash
ask-deepseek --paths <fichier1> <fichier2> ... --question "<question>"
# Avec raisonnement (fichiers complexes, interactions de threads, etc.) :
ask-deepseek --paths <fichier1> --question "<question>" --think
```

**Quand l'utiliser :**
- Lire ≥ 1 fichier de plus de 300 lignes pour répondre à une question
- Lire ≥ 3 fichiers quelle que soit leur taille
- Comprendre des interactions entre modules (ex : quel port, quelle clé de config, quel handler)
- Résumés de modules avant refactoring

**Ce que ça retourne :** texte structuré. Lire ce texte (~300-500 tokens) au lieu des fichiers.

---

### `write-deepseek` — Génération de boilerplate

```bash
write-deepseek --spec "<description précise>" \
               --context <fichier_reference.py> \
               --target <fichier_sortie.py>
```

**Quand l'utiliser :**
- Générer un fichier de tests pytest pour un module existant
- Générer des docstrings pour des fonctions publiques
- Scaffolding de nouveaux handlers/routers en suivant le pattern existant
- Mise à jour de documentation après une session de travail

**Workflow doc (OBLIGATOIRE après chaque session feature) :**
```bash
# 1. Extraire le transcript
extract-chat ~/.claude/projects/aria/<session>.jsonl -o /tmp/chat.txt

# 2. Demander les mises à jour à DeepSeek
ask-deepseek --paths /tmp/chat.txt docs/architecture.md \
             --question "Quelles mises à jour de doc sont nécessaires ? Donne les éditions exactes."

# 3. Appliquer les suggestions (coût Claude minimal)
```

---

### Frontière stricte : Claude = raisonnement, DeepSeek = I/O

| Tâche | Qui fait quoi |
|---|---|
| Déboguer une race condition | **Claude** |
| Décision d'architecture | **Claude** |
| Vérifier la stabilité numérique | **Claude** |
| Lire 5 fichiers pour trouver un port | **DeepSeek** |
| Générer un fichier de tests | **DeepSeek** |
| Mettre à jour la doc après une session | **DeepSeek** |
| Scaffolding d'un nouveau handler | **DeepSeek** |

### Ne PAS déléguer si
- La tâche fait < 1500 tokens au total (overhead non justifié)
- Il faut des numéros de ligne exacts pour un `str_replace`
- C'est du code safety-critical (guidance, MAVLink critique)
- Le raisonnement sur l'intent est nécessaire