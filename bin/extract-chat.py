#!/usr/bin/env python3
"""
extract-chat — Extrait le texte lisible d'un transcript Claude Code (.jsonl).
Filtre : uniquement les messages human/assistant, sans tool_calls ni blobs binaires.

Usage:
  extract-chat ~/.claude/projects/aria/session.jsonl
  extract-chat ~/.claude/projects/aria/session.jsonl -o /tmp/chat.txt
  extract-chat ~/.claude/projects/aria/session.jsonl --last 20
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
