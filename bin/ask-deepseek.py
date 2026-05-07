#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
ask-deepseek — Délègue la lecture de fichiers volumineux à DeepSeek V4 Flash.
Usage:
  ask-deepseek --paths file1.py file2.py --question "Quels ports sont utilisés ?"
  ask-deepseek --paths file1.py --question "Résume ce module" --think
"""
import argparse
import os
import pathlib
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://api.deepseek.com"
MODEL_FAST = "deepseek-v4-flash"   # non-thinking : lecture, résumé, extraction

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url=BASE_URL,
)

# ── Args ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Lecture de fichiers via DeepSeek V4 Flash")
parser.add_argument("--paths", nargs="+", required=True, help="Fichiers à analyser")
parser.add_argument("--question", required=True, help="Question à poser sur le corpus")
parser.add_argument("--think", action="store_true",
                    help="Active le mode thinking (plus lent, meilleure analyse)")
args = parser.parse_args()

# ── Validation ────────────────────────────────────────────────────────────────
api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key:
    print("[ask-deepseek] ERREUR: variable DEEPSEEK_API_KEY non définie", file=sys.stderr)
    sys.exit(1)

# ── Lecture des fichiers ──────────────────────────────────────────────────────
docs = []
for p in args.paths:
    path = pathlib.Path(p)
    if not path.exists():
        print(f"[ask-deepseek] AVERTISSEMENT: fichier introuvable — {p}", file=sys.stderr)
        continue
    try:
        content = path.read_text(encoding="utf-8")
        docs.append(f"<file path='{p}'>\n{content}\n</file>")
    except Exception as e:
        print(f"[ask-deepseek] AVERTISSEMENT: impossible de lire {p} — {e}", file=sys.stderr)

if not docs:
    print("[ask-deepseek] ERREUR: aucun fichier lisible fourni", file=sys.stderr)
    sys.exit(1)

corpus = "\n\n".join(docs)

# ── Appel API ─────────────────────────────────────────────────────────────────
# Les fichiers d'abord → prefix caching (appels successifs = 90% moins cher)
messages = [
    {
        "role": "system",
        "content": (
            "Tu es un analyste de code précis et concis. "
            "Réponds uniquement à ce qui est demandé, sans preamble inutile. "
            "Si la question porte sur du code, cite les noms exacts (fonctions, variables, fichiers). "
            "Langue de réponse : celle de la question posée."
        ),
    },
    {
        "role": "user",
        "content": f"<corpus>\n{corpus}\n</corpus>",
    },
    {
        "role": "user",
        "content": args.question,
    },
]

# Thinking mode : on/off selon le flag --think
# En non-thinking, DeepSeek V4 Flash coûte $0.14/1M input, $0.28/1M output
# En thinking, les tokens de raisonnement sont comptés dans l'output (prévoir large)
extra_params = {}
if not args.think:
    extra_params["extra_body"] = {"thinking": {"type": "disabled"}}
    max_tokens = 4096
else:
    max_tokens = 16384  # thinking tokens + réponse

try:
    response = client.chat.completions.create(
        model=MODEL_FAST,
        messages=messages,
        max_tokens=max_tokens,
        **extra_params,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"[ask-deepseek] ERREUR API: {e}", file=sys.stderr)
    sys.exit(1)
