#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
extract-chat — Extrait le texte lisible d'un log de conversation au format .jsonl.
Filtre : uniquement les messages human/assistant, sans tool_calls ni blobs binaires.

⚠️  INTERDIT sur ~/.claude/ — refus dur (voir plus bas). Les transcripts de
session Claude Code peuvent contenir des secrets : une clé d'API s'y est
retrouvée en clair le 2026-07-22. L'outil est réservé aux logs produits par une
application, jamais aux transcripts de l'agent.

Usage:
  extract-chat ./logs/session.jsonl
  extract-chat ./logs/session.jsonl -o /tmp/chat.txt
  extract-chat ./logs/session.jsonl --last 20
"""
import argparse
import json
import pathlib
import sys

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Extrait le texte d'un transcript Claude Code")
parser.add_argument("jsonl", help="Fichier .jsonl du transcript")
parser.add_argument("-o", "--output", default=None, help="Fichier de sortie (défaut: stdout)")
parser.add_argument("--last", type=int, default=None,
                    help="Garder uniquement les N derniers échanges")
args = parser.parse_args()

# ── Lecture ───────────────────────────────────────────────────────────────────
path = pathlib.Path(args.jsonl)
if not path.exists():
    print(f"[extract-chat] ERREUR: fichier introuvable — {args.jsonl}", file=sys.stderr)
    sys.exit(1)

# ── Verrou : jamais les transcripts de l'agent ────────────────────────────────
# On résout le chemin réel (symlinks, ../ et ~ compris) : le refus ne doit pas
# se contourner par une écriture détournée du chemin.
reel = path.resolve()
interdit = (pathlib.Path.home() / ".claude").resolve()
if reel == interdit or interdit in reel.parents:
    print(f"[extract-chat] ERREUR: lecture REFUSÉE sous {interdit}\n"
          f"                Les transcripts de session peuvent contenir des secrets "
          f"(incident du 2026-07-22).\n"
          f"                Cet outil est réservé aux logs produits par une application.",
          file=sys.stderr)
    sys.exit(1)

lines = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue

# ── Extraction du texte ───────────────────────────────────────────────────────
def extract_text(content) -> str:
    """Extrait le texte pur d'un champ content (str ou liste de blocs)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            # Ignorer : tool_use, tool_result, image, document (trop verbeux/binaire)
        return "\n".join(parts)
    return ""


exchanges = []
for obj in lines:
    role = obj.get("role", "")
    content = obj.get("content", "")

    if role not in ("user", "assistant", "human"):
        continue

    # Ignorer les messages qui ne contiennent que des appels d'outils
    text = extract_text(content)
    if not text:
        continue

    label = "HUMAIN" if role in ("user", "human") else "ARIA"
    exchanges.append(f"[{label}]\n{text}\n")

# ── Diagnostic de schéma ──────────────────────────────────────────────────────
# Ce parseur attend `role`/`content` à la RACINE de chaque ligne. D'autres
# formats (dont les transcripts Claude Code) les encapsulent sous `message`.
# Sans ce message, une sortie vide passe pour « conversation sans texte ».
if not exchanges and lines:
    encapsule = sum(1 for o in lines if isinstance(o.get("message"), dict))
    print(f"[extract-chat] AVERTISSEMENT: {len(lines)} ligne(s) JSON lue(s), "
          f"0 échange extrait.", file=sys.stderr)
    if encapsule:
        print(f"                {encapsule} ligne(s) portent un objet `message` : ce "
              f"format encapsule\n"
              f"                role/content, que ce parseur attend à la racine. "
              f"Schéma non géré.", file=sys.stderr)
    sys.exit(1)

# ── Filtre --last ─────────────────────────────────────────────────────────────
if args.last and len(exchanges) > args.last:
    exchanges = exchanges[-args.last:]

# ── Sortie ────────────────────────────────────────────────────────────────────
output = "\n".join(exchanges)

if args.output:
    pathlib.Path(args.output).write_text(output, encoding="utf-8")
    print(f"[extract-chat] ✓ Transcript exporté : {args.output} ({len(exchanges)} échanges)")
else:
    print(output)
