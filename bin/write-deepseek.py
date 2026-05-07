#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
write-deepseek — Génère du code boilerplate via DeepSeek V4 Flash.
Usage:
  write-deepseek --spec "pytest pour le parser MAVLink" \
                 --context src/mavlink_parser.py \
                 --target tests/test_mavlink_parser.py

  write-deepseek --spec "docstrings pour toutes les fonctions publiques" \
                 --context aria/kernel.py \
                 --target aria/kernel_documented.py
"""
import argparse
import os
import pathlib
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "https://api.deepseek.com"
MODEL_FAST = "deepseek-v4-flash"

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url=BASE_URL,
)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Génération de code boilerplate via DeepSeek V4 Flash")
parser.add_argument("--spec", required=True,
                    help="Description de ce qu'il faut générer")
parser.add_argument("--context", nargs="+", default=[],
                    help="Fichiers de référence (style, API, signatures)")
parser.add_argument("--target", required=True,
                    help="Fichier de sortie à écrire")
parser.add_argument("--lang", default="python",
                    help="Langage cible (défaut: python)")
parser.add_argument("--think", action="store_true",
                    help="Active le mode thinking pour les générations complexes")
args = parser.parse_args()

# ── Validation ────────────────────────────────────────────────────────────────
api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key:
    print("[write-deepseek] ERREUR: variable DEEPSEEK_API_KEY non définie", file=sys.stderr)
    sys.exit(1)

# ── Lecture des fichiers de contexte ──────────────────────────────────────────
context_blocks = []
for p in args.context:
    path = pathlib.Path(p)
    if not path.exists():
        print(f"[write-deepseek] AVERTISSEMENT: fichier de contexte introuvable — {p}", file=sys.stderr)
        continue
    try:
        content = path.read_text(encoding="utf-8")
        context_blocks.append(f"<reference path='{p}'>\n{content}\n</reference>")
    except Exception as e:
        print(f"[write-deepseek] AVERTISSEMENT: impossible de lire {p} — {e}", file=sys.stderr)

context_section = "\n\n".join(context_blocks) if context_blocks else "(aucun fichier de référence fourni)"

# ── Prompt ────────────────────────────────────────────────────────────────────
system_prompt = f"""Tu es un générateur de code expert. Tu produis UNIQUEMENT du code {args.lang} brut.
Règles absolues :
- Pas de markdown (pas de ```), pas d'explications, pas de commentaires introductifs.
- Le fichier généré doit être directement exécutable / importable.
- Respecte scrupuleusement le style du code de référence fourni (nommage, logging, structure).
- Commentaires en français si le code de référence utilise du français.
- Ne jamais utiliser print() — utiliser le logger si le code de référence le fait."""

user_prompt = f"""Fichiers de référence :
{context_section}

Tâche : {args.spec}

Fichier cible : {args.target}

Génère le contenu complet du fichier cible. Code brut uniquement."""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]

# ── Appel API ─────────────────────────────────────────────────────────────────
extra_params = {}
if not args.think:
    extra_params["extra_body"] = {"thinking": {"type": "disabled"}}
    max_tokens = 16384   # génération de fichiers complets
else:
    max_tokens = 32768   # thinking + génération longue

try:
    response = client.chat.completions.create(
        model=MODEL_FAST,
        messages=messages,
        max_tokens=max_tokens,
        **extra_params,
    )
    generated = response.choices[0].message.content.strip()
except Exception as e:
    print(f"[write-deepseek] ERREUR API: {e}", file=sys.stderr)
    sys.exit(1)

# ── Nettoyage éventuel des balises markdown résiduelles ──────────────────────
if generated.startswith("```"):
    lines = generated.splitlines()
    # Retire la première et dernière ligne si ce sont des backticks
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    generated = "\n".join(lines)

# ── Écriture du fichier cible ─────────────────────────────────────────────────
target_path = pathlib.Path(args.target)
target_path.parent.mkdir(parents=True, exist_ok=True)

try:
    target_path.write_text(generated, encoding="utf-8")
    print(f"[write-deepseek] ✓ Fichier écrit : {args.target} ({len(generated)} caractères)")
    # Affiche aussi le contenu sur stdout pour que Claude puisse le lire
    print("─" * 60)
    print(generated)
except Exception as e:
    print(f"[write-deepseek] ERREUR écriture: {e}", file=sys.stderr)
    # Fallback : afficher sur stdout
    print(generated)
    sys.exit(1)
