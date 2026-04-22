# ARIA — Cognitive Kernel Assistant

ARIA est un système d’agent cognitif personnel basé sur :

- un kernel central d’orchestration
- un système d’intentions persistantes
- une mémoire vectorielle (MemPalace)
- un pipeline d’agents spécialisés
- une interface Telegram

---

## ⚙️ Philosophie

ARIA n’est pas un chatbot.

ARIA est un **runtime cognitif** :

- le Kernel est le seul point d’accès aux données
- les agents sont des fonctions sans état
- la mémoire est centralisée et persistante
- toute action est rattachée à une intention

---

## 🧠 Architecture
Telegram Interface
↓
Kernel
↓
Intent Engine
↓
Memory Layer (MemPalace)
↓
Agent Pipeline
↓
Response


---

## 📦 Stack

- Python 3.13
- sentence-transformers
- ChromaDB (MemPalace)
- Telegram Bot API
- systemd (Linux service)

---

## 🚀 Installation

```bash
cd ~/projects/aria
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

---

## 🔐 Configuration

Créer un fichier .env local :

TELEGRAM_BOT_TOKEN=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
OPENROUTER_API_KEY=...
CEREBRAS_API_KEY=...

⚠️ Le fichier .env ne doit jamais être versionné.

---

## ▶️ Lancement

source venv/bin/activate
python bot.py

---

##🧩 Comportement du système
chaque message est transformé en Intent ou rattaché à un intent existant
la mémoire est consultée uniquement par le Kernel
les agents reçoivent uniquement un AgentContext
aucun agent ne peut accéder directement à la mémoire ou au stockage