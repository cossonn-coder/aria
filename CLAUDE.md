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

1. **Une opération = un handler = un seul point d'écriture mémoire**
2. **Les agents reçoivent un AgentContext pré-assemblé** — ils ne font
   AUCUNE requête mémoire eux-mêmes. Le kernel assemble tout.
3. **Les routers retournent `{"text": str}` ou `{"path": str, "caption": str}`** —
   jamais `{"status": ...}` (c'est le rôle du dispatcher).
4. **Le kernel ne décide rien, n'exécute rien, ne stocke rien.**
   Il séquence : classify → dispatch → normalize.
5. **CognitiveEngine ne touche pas MemPalace, ni les agents, ni les routers.**
   Il classifie, c'est tout.

## Couches mémoire
- `aria_episodic` : interactions, images, types `interaction|image_input|image_generated`
- `aria_semantic` : faits stables (allergies, localisation, préférences)
- `aria_intentual` : réservé intents sérialisés (pas implémenté)

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

## Backlog en cours
Voir le doc de contexte complet pour le sprint actuel.
Priorité immédiate : 1.3 Context builder token budget
(injecter `retrieve_semantic` dans `LLMExecutionRouter`).

## Ne JAMAIS faire
- Modifier `soul.md` sans demander explicitement à Nico
- Bypasser le kernel pour appeler un router directement
- Faire écrire la mémoire par un agent ou un client LLM
- Utiliser `print()` à la place du logger
- Lancer `git push` sans confirmation
