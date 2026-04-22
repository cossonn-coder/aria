# Aria — Assistant IA personnel

Bot Telegram multi-agents avec mémoire persistante, fallback automatique sur 6 providers LLM, et pipeline agentique pour explorer des idées.

---

## Installation

```bash
cd ~/projects/aria
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

Ajoute ces variables dans `~/groq/.env` :

```env
TELEGRAM_BOT_TOKEN=...
ALLOWED_USER_ID=...         # ton user ID Telegram (optionnel mais recommandé)
GEMINI_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
CEREBRAS_API_KEY=...
SAMBANOVA_API_KEY=...
OPENROUTER_API_KEY=...
```

Place `soul.md` et `user.md` à la racine du projet (déjà fournis).
Crée un `memory.md` vide : `touch memory.md`

---

## Lancement manuel

```bash
source venv/bin/activate
python bot.py
```

## Service systemd

```bash
sudo cp aria.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aria
sudo systemctl start aria
sudo journalctl -u aria -f   # logs en temps réel
```

---

## Commandes Telegram

| Commande | Description |
|---|---|
| `/idea <texte>` | Lance le pipeline multi-agents |
| `/skip` | Passe la question en cours |
| `/cancel` | Annule le dialogue, lance quand même le plan |
| `/confirm` | Voir les mémoires en attente |
| `/confirm all` | Valider toutes les mémoires en attente |
| `/confirm 1 3` | Valider les mémoires 1 et 3 |
| `/reject` | Rejeter toutes les mémoires en attente |
| `/memories` | Voir les mémoires stockées |
| `/remember` | Forcer une extraction maintenant |
| `/models` | Voir les modèles configurés |
| `/stats` | Statistiques |
| `/reset` | Effacer toutes les mémoires |

---

## Architecture LLM

| Rôle | Usage | Ordre de fallback |
|---|---|---|
| FAST | Dialogue, synthèse | Groq → Cerebras → OpenRouter → Gemini |
| DEEP | Analyse, planning | Gemini → SambaNova → OpenRouter → Groq |
| CREATIVE | Critique, nuance | Mistral → OpenRouter → Gemini → Cerebras |

OpenRouter sélectionne dynamiquement les modèles gratuits disponibles (refresh toutes les 24h).

---

## Fichiers d'identité

| Fichier | Rôle | Modification |
|---|---|---|
| `soul.md` | Constitution du bot, règles non négociables | Rare, manuelle |
| `user.md` | Profil de Nico, préférences | Occasionnelle, manuelle |
| `memory.md` | Faits durables validés manuellement | Via éditeur texte |

Les mémoires conversationnelles sont dans ChromaDB (`chroma_db/`) et ne sont jamais écrites sans validation via `/confirm`.
