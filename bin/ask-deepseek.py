#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
ask-deepseek — Délègue la lecture de fichiers volumineux à DeepSeek V4 Flash.
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
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "https://api.deepseek.com"
MODEL_FAST = "deepseek-v4-flash"   # non-thinking : lecture, résumé, extraction

# Tarifs affichés par DeepSeek ($/M tokens). Servent à l'estimation de coût :
# la clé est plafonnée, on veut voir ce que chaque appel consomme.
PRIX_IN_MISS = 0.14
PRIX_IN_HIT = 0.014
PRIX_OUT = 0.28

# Plafond de sécurité sur le corpus. Au-delà, on refuse : soit la sélection de
# fichiers est trop large (mieux vaut filtrer en amont), soit c'est une erreur.
MAX_CHARS = 800_000

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
parser.add_argument("--allow-missing", action="store_true",
                    help="Tolère les fichiers introuvables (défaut : erreur fatale)")
parser.add_argument("--yes", action="store_true",
                    help=f"Passe outre le plafond de {MAX_CHARS} caractères de corpus")
args = parser.parse_args()

# ── Validation ────────────────────────────────────────────────────────────────
api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key:
    print("[ask-deepseek] ERREUR: variable DEEPSEEK_API_KEY non définie", file=sys.stderr)
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
# Les fichiers d'abord → prefix caching (appels successifs = 90% moins cher)
messages = [
    {
        "role": "system",
        "content": (
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
except Exception as e:
    print(f"[ask-deepseek] ERREUR API: {e}", file=sys.stderr)
    sys.exit(1)

choix = response.choices[0]
print(choix.message.content)

# ── Troncature ────────────────────────────────────────────────────────────────
# Le bandeau va sur STDOUT : un avertissement stderr se noie dans un `| tail`,
# et une réponse coupée en plein inventaire ressemble à une réponse finie.
tronquee = getattr(choix, "finish_reason", None) == "length"
if tronquee:
    print(f"\n{'=' * 60}\n"
          f"⚠️  RÉPONSE TRONQUÉE — la limite de {max_tokens} tokens de sortie a été\n"
          f"    atteinte. Ce qui précède est INCOMPLET. Relance avec une question\n"
          f"    plus étroite, ou découpe le corpus.\n"
          f"{'=' * 60}")

# ── Consommation réelle ───────────────────────────────────────────────────────
usage = getattr(response, "usage", None)
if usage:
    tok_in = getattr(usage, "prompt_tokens", 0) or 0
    tok_out = getattr(usage, "completion_tokens", 0) or 0
    hits = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
    miss = getattr(usage, "prompt_cache_miss_tokens", None)
    if miss is None:
        miss = max(tok_in - hits, 0)
    cout = (miss * PRIX_IN_MISS + hits * PRIX_IN_HIT + tok_out * PRIX_OUT) / 1e6
    print(f"[ask-deepseek] usage : {tok_in} in ({hits} en cache) + {tok_out} out "
          f"→ ~${cout:.4f}", file=sys.stderr)

sys.exit(2 if tronquee else 0)
