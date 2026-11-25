#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
ask-deepseek — Délègue la lecture de fichiers volumineux à Claude Haiku 5.5
(Anthropic depuis le 2026-11-25 ; le nom de l'outil est resté).
Usage:
  ask-deepseek --paths file1.py file2.py --question "Quels ports sont utilisés ?"
  ask-deepseek --paths file1.py --question "Résume ce module" --think

Fiabilité (durci le 2026-07-22, après le 1er test grandeur nature) :
- un fichier introuvable est FATAL (--allow-missing pour tolérer) : une réponse
  bâtie sur un corpus amputé est indiscernable d'une réponse complète ;
- la troncature de la réponse est détectée et annoncée sur stdout ;
- le volume envoyé et le coût réel sont affichés sur stderr (clé plafonnée).
"""
import argparse
import os
import pathlib
import sys
import anthropic
from dotenv import load_dotenv

# Clé Anthropic : celle d'ARIA (même venv, même compte, même crédit).
load_dotenv("/home/nico/Nextcloud/projects/aria/.env")

# ── Config ──────────────────────────────────────────────────────────────────
MODEL = "claude-haiku-5-5"

# Tarifs Claude Haiku 5.5 ($/M tokens), carte « prompt ≤ 100K tokens » ; au-delà, entrée
# 0,50 et sortie 2,50. Cache : lecture 0,1x l'entrée, écriture 1,25x.
PRIX_IN = 0.10
PRIX_OUT = 0.50
PRIX_IN_LONG = 0.50
PRIX_OUT_LONG = 2.50

# Plafond de sécurité sur le corpus. Au-delà, on refuse : soit la sélection de
# fichiers est trop large (mieux vaut filtrer en amont), soit c'est une erreur.
MAX_CHARS = 800_000

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

def cout_usd(usage) -> tuple[int, int, int, float]:
    """(tokens entrée, dont lus en cache, sortie, coût estimé $) d'une réponse Anthropic."""
    plain = usage.input_tokens or 0
    hits = usage.cache_read_input_tokens or 0
    writes = usage.cache_creation_input_tokens or 0
    tok_in = plain + hits + writes
    prix_in, prix_out = (PRIX_IN, PRIX_OUT) if tok_in <= 100_000 else (PRIX_IN_LONG, PRIX_OUT_LONG)
    cout = (plain * prix_in + hits * prix_in * 0.1 + writes * prix_in * 1.25
            + usage.output_tokens * prix_out) / 1e6
    return tok_in, hits, usage.output_tokens, cout


# ── Args ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Lecture de fichiers via Claude Haiku 5.5")
parser.add_argument("--paths", nargs="+", required=True, help="Fichiers à analyser")
parser.add_argument("--question", required=True, help="Question à poser sur le corpus")
parser.add_argument("--think", action="store_true",
                    help="Active la réflexion adaptative, effort high (plus lent, meilleure analyse)")
parser.add_argument("--allow-missing", action="store_true",
                    help="Tolère les fichiers introuvables (défaut : erreur fatale)")
parser.add_argument("--yes", action="store_true",
                    help=f"Passe outre le plafond de {MAX_CHARS} caractères de corpus")
args = parser.parse_args()

# ── Validation ────────────────────────────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    print("[ask-deepseek] ERREUR: ANTHROPIC_API_KEY absente (ni environnement, ni .env d'ARIA)", file=sys.stderr)
    sys.exit(1)

# ── Lecture des fichiers ──────────────────────────────────────────────────────
# Un chemin qui manque doit ARRÊTER l'appel : le modèle répondrait sur le corpus
# amputé sans que rien ne le signale dans sa réponse, et l'appelant croirait
# avoir interrogé l'ensemble.
docs = []
lus = []
manquants = []
illisibles = []
for p in args.paths:
    path = pathlib.Path(p)
    if not path.exists():
        manquants.append(p)
        continue
    try:
        content = path.read_text(encoding="utf-8")
        docs.append(f"<file path='{p}'>\n{content}\n</file>")
        lus.append((p, len(content)))
    except Exception as e:
        illisibles.append(f"{p} — {e}")

if manquants or illisibles:
    for p in manquants:
        print(f"[ask-deepseek] fichier introuvable — {p}", file=sys.stderr)
    for msg in illisibles:
        print(f"[ask-deepseek] fichier illisible — {msg}", file=sys.stderr)
    if not args.allow_missing:
        print(f"[ask-deepseek] ERREUR: {len(manquants) + len(illisibles)} fichier(s) sur "
              f"{len(args.paths)} inaccessible(s) — appel ANNULÉ.\n"
              f"                Corrige les chemins, ou passe --allow-missing pour "
              f"interroger le corpus partiel en le sachant.", file=sys.stderr)
        sys.exit(1)
    print(f"[ask-deepseek] ⚠️  --allow-missing : corpus PARTIEL "
          f"({len(lus)}/{len(args.paths)} fichiers)", file=sys.stderr)

if not docs:
    print("[ask-deepseek] ERREUR: aucun fichier lisible fourni", file=sys.stderr)
    sys.exit(1)

corpus = "\n\n".join(docs)

# ── Récapitulatif de ce qui part réellement ──────────────────────────────────
total_chars = len(corpus)
print(f"[ask-deepseek] corpus : {len(lus)} fichier(s), {total_chars} caractères "
      f"(~{total_chars // 4} tokens estimés)", file=sys.stderr)
for p, n in sorted(lus, key=lambda x: -x[1])[:5]:
    print(f"                {n:>8} car.  {p}", file=sys.stderr)
if len(lus) > 5:
    print(f"                … et {len(lus) - 5} autre(s)", file=sys.stderr)

if total_chars > MAX_CHARS and not args.yes:
    print(f"[ask-deepseek] ERREUR: corpus de {total_chars} caractères > plafond "
          f"{MAX_CHARS} — appel ANNULÉ.\n"
          f"                Restreins la sélection (grep -l en amont) ou passe --yes.",
          file=sys.stderr)
    sys.exit(1)

# ── Appel API ─────────────────────────────────────────────────────────────────
# Corpus d'abord, marqué pour le cache de prompt : des questions successives sur
# le même corpus le relisent à 0,1x le prix d'entrée (sous ~5 min).
system = (
    "Tu es un analyste de code et de documentation, précis et concis. "
    "Réponds uniquement à ce qui est demandé, sans preamble inutile. "
    "Cite toujours les noms exacts (fichiers, fonctions, variables, identifiants) "
    "et le chemin du fichier d'où vient chaque information. "
    "EXHAUSTIVITÉ : quand une liste est demandée, parcours TOUT le corpus. "
    "Si tu ne peux pas garantir d'avoir tout couvert, dis-le explicitement — "
    "n'écris jamais « aucun autre » ou « rien de plus » comme conclusion par "
    "défaut. Mieux vaut signaler un doute qu'affirmer une liste complète. "
    "Ne déduis rien qui ne soit pas écrit dans le corpus. "
    "Langue de réponse : celle de la question posée ; si la question est en "
    "français, réponds en français avec les accents et diacritiques corrects."
)
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": f"<corpus>\n{corpus}\n</corpus>", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": args.question},
    ],
}]

# Sans --think : réflexion coupée (Haiku 5.5 réfléchit par défaut). Avec : adaptative,
# ses tokens comptent dans max_tokens (prévoir large).
if args.think:
    params = {"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}
    max_tokens = 16384
else:
    params = {"thinking": {"type": "disabled"}}
    max_tokens = 4096

try:
    with client.messages.stream(model=MODEL, max_tokens=max_tokens, system=system,
                                messages=messages, **params) as stream:
        response = stream.get_final_message()
except anthropic.APIError as e:
    print(f"[ask-deepseek] ERREUR API: {e}", file=sys.stderr)
    sys.exit(1)

print("".join(block.text for block in response.content if block.type == "text"))
if response.stop_reason == "refusal":
    print("\n⚠️  REFUS du modèle (stop_reason=refusal) : réponse vide ou partielle.")

# ── Troncature ────────────────────────────────────────────────────────────────
# Le bandeau va sur STDOUT : un avertissement stderr se noie dans un `| tail`,
# et une réponse coupée en plein inventaire ressemble à une réponse finie.
tronquee = response.stop_reason == "max_tokens"
if tronquee:
    print(f"\n{'=' * 60}\n"
          f"⚠️  RÉPONSE TRONQUÉE — la limite de {max_tokens} tokens de sortie a été\n"
          f"    atteinte. Ce qui précède est INCOMPLET. Relance avec une question\n"
          f"    plus étroite, ou découpe le corpus.\n"
          f"{'=' * 60}")

# ── Consommation réelle ───────────────────────────────────────────────────────
tok_in, hits, tok_out, cout = cout_usd(response.usage)
print(f"[ask-deepseek] usage : {tok_in} in ({hits} en cache) + {tok_out} out "
      f"→ ~${cout:.4f} ({MODEL})", file=sys.stderr)

sys.exit(2 if tronquee else 0)
