#!/home/nico/Nextcloud/projects/aria/venv/bin/python3
"""
write-deepseek — Génère du code boilerplate ou de la prose via DeepSeek V4 Flash.
Usage:
  write-deepseek --spec "pytest pour le parser MAVLink" \
                 --context src/mavlink_parser.py \
                 --target tests/test_mavlink_parser.py

  write-deepseek --lang markdown --spec "note de synthèse" \
                 --context notes/a.md notes/b.md \
                 --target /tmp/synthese.md

Fiabilité (durci le 2026-07-22, après une génération entièrement fabriquée) :
- un --context introuvable est FATAL : sans référence, le modèle invente une
  sortie plausible et rien ne le signale ;
- la cible n'est jamais écrasée sans --force, et aucun répertoire parent n'est
  créé sans --mkdir (un --target mal expansé créait une arborescence parasite) ;
- une génération tronquée n'est PAS écrite (règle « zéro perte ») ;
- le prompt système s'adapte au --lang : code brut vs prose.
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

# Tarifs DeepSeek ($/M tokens) — la clé est plafonnée, on affiche le coût réel.
PRIX_IN_MISS = 0.14
PRIX_IN_HIT = 0.014
PRIX_OUT = 0.28

# Langages qui produisent de la PROSE et non du code : le prompt système change
# du tout au tout (« pas de markdown », « directement importable » n'ont aucun
# sens pour une note de synthèse).
LANGS_PROSE = {"markdown", "md", "text", "txt", "rst", "prose"}

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url=BASE_URL,
)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Génération via DeepSeek V4 Flash")
parser.add_argument("--spec", required=True,
                    help="Description de ce qu'il faut générer")
parser.add_argument("--context", nargs="+", default=[],
                    help="Fichiers de référence (style, API, signatures, sources)")
parser.add_argument("--target", required=True,
                    help="Fichier de sortie à écrire")
parser.add_argument("--lang", default="python",
                    help="Langage cible (défaut: python ; markdown/text = prose)")
parser.add_argument("--think", action="store_true",
                    help="Active le mode thinking pour les générations complexes")
parser.add_argument("--allow-missing", action="store_true",
                    help="Tolère un fichier de contexte introuvable (défaut : fatal)")
parser.add_argument("--force", action="store_true",
                    help="Autorise l'écrasement d'une cible existante")
parser.add_argument("--mkdir", action="store_true",
                    help="Autorise la création des répertoires parents de la cible")
args = parser.parse_args()

# ── Validation ────────────────────────────────────────────────────────────────
api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not api_key:
    print("[write-deepseek] ERREUR: variable DEEPSEEK_API_KEY non définie", file=sys.stderr)
    sys.exit(1)

# ── Vérification de la cible AVANT de payer un appel API ─────────────────────
target_path = pathlib.Path(args.target)

if target_path.exists() and not args.force:
    print(f"[write-deepseek] ERREUR: la cible existe déjà — {args.target}\n"
          f"                 Écrire ici écraserait le fichier sans filet. Passe --force\n"
          f"                 si c'est bien l'intention (relis le diff après coup).",
          file=sys.stderr)
    sys.exit(1)

if not target_path.parent.exists():
    if not args.mkdir:
        print(f"[write-deepseek] ERREUR: le répertoire parent n'existe pas — "
              f"{target_path.parent}\n"
              f"                 Souvent le signe d'un --target mal formé (variable de\n"
              f"                 shell non expansée). Passe --mkdir si la création est\n"
              f"                 bien voulue.", file=sys.stderr)
        sys.exit(1)

# ── Lecture des fichiers de contexte ──────────────────────────────────────────
# Un contexte manquant est FATAL : privé de ses références, le modèle produit
# une sortie d'apparence sérieuse et entièrement fabriquée (constaté le
# 2026-07-22 — cycle de dépendances inventé de toutes pièces).
context_blocks = []
lus = []
manquants = []
illisibles = []
for p in args.context:
    path = pathlib.Path(p)
    if not path.exists():
        manquants.append(p)
        continue
    try:
        content = path.read_text(encoding="utf-8")
        context_blocks.append(f"<reference path='{p}'>\n{content}\n</reference>")
        lus.append((p, len(content)))
    except Exception as e:
        illisibles.append(f"{p} — {e}")

if manquants or illisibles:
    for p in manquants:
        print(f"[write-deepseek] contexte introuvable — {p}", file=sys.stderr)
    for msg in illisibles:
        print(f"[write-deepseek] contexte illisible — {msg}", file=sys.stderr)
    if not args.allow_missing:
        print(f"[write-deepseek] ERREUR: {len(manquants) + len(illisibles)} fichier(s) de "
              f"contexte sur {len(args.context)} inaccessible(s) — génération ANNULÉE.\n"
              f"                 Sans ses références le modèle INVENTE. Corrige les\n"
              f"                 chemins, ou passe --allow-missing en connaissance de cause.",
              file=sys.stderr)
        sys.exit(1)
    print(f"[write-deepseek] ⚠️  --allow-missing : contexte PARTIEL "
          f"({len(lus)}/{len(args.context)} fichiers)", file=sys.stderr)

if args.context and not context_blocks:
    print("[write-deepseek] ERREUR: aucun fichier de contexte lisible alors que "
          "--context était fourni — génération ANNULÉE.", file=sys.stderr)
    sys.exit(1)

context_section = "\n\n".join(context_blocks) if context_blocks else "(aucun fichier de référence fourni)"

if lus:
    total = sum(n for _, n in lus)
    print(f"[write-deepseek] contexte : {len(lus)} fichier(s), {total} caractères",
          file=sys.stderr)
    for p, n in sorted(lus, key=lambda x: -x[1]):
        print(f"                 {n:>8} car.  {p}", file=sys.stderr)

# ── Prompt ────────────────────────────────────────────────────────────────────
prose = args.lang.lower() in LANGS_PROSE

if prose:
    system_prompt = f"""Tu rédiges un document {args.lang} destiné à être lu par un humain.
Règles absolues :
- N'utilise QUE ce qui figure dans les fichiers de référence. N'invente aucun fait,
  aucun chemin de fichier, aucun identifiant, aucune dépendance entre éléments.
- Si la référence ne dit rien sur un point demandé, écris-le explicitement plutôt
  que de combler par du plausible.
- Ne recopie pas les références : synthétise, en gardant les termes exacts.
- Respecte la langue de la spécification ; si elle est en français, rédige en
  français avec les accents et diacritiques corrects (jamais d'ASCII à la place).
- Produis le document brut, sans clôture par des backticks."""
else:
    system_prompt = f"""Tu es un générateur de code expert. Tu produis UNIQUEMENT du code {args.lang} brut.
Règles absolues :
- Pas de markdown (pas de ```), pas d'explications, pas de commentaires introductifs.
- Le fichier généré doit être directement exécutable / importable.
- Respecte scrupuleusement le style du code de référence fourni (nommage, logging, structure).
- N'invente pas d'API : n'utilise que les signatures présentes dans les références.
- Commentaires en français si le code de référence utilise du français.
- Ne jamais utiliser print() — utiliser le logger si le code de référence le fait."""

user_prompt = f"""Fichiers de référence :
{context_section}

Tâche : {args.spec}

Fichier cible : {args.target}

Génère le contenu complet du fichier cible. Contenu brut uniquement."""

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
    choix = response.choices[0]
    generated = choix.message.content.strip()
except Exception as e:
    print(f"[write-deepseek] ERREUR API: {e}", file=sys.stderr)
    sys.exit(1)

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
    print(f"[write-deepseek] usage : {tok_in} in ({hits} en cache) + {tok_out} out "
          f"→ ~${cout:.4f}", file=sys.stderr)

# ── Troncature : on n'écrit PAS un fichier amputé ────────────────────────────
# Règle « zéro perte » : un fichier coupé en plein milieu, annoncé « ✓ écrit »,
# est pire que pas de fichier du tout — surtout sur une cible versionnée.
if getattr(choix, "finish_reason", None) == "length":
    print(f"[write-deepseek] ERREUR: génération TRONQUÉE (limite {max_tokens} tokens "
          f"atteinte) — fichier NON écrit.\n"
          f"                 Découpe la tâche, ou relance avec --think.", file=sys.stderr)
    print("─" * 60, file=sys.stderr)
    print(generated, file=sys.stderr)   # sur stderr : à inspecter, pas à réutiliser
    sys.exit(1)

# ── Nettoyage éventuel des balises markdown résiduelles ──────────────────────
# En mode prose, les ``` peuvent être légitimes (bloc de code dans le document) :
# on ne retire que la clôture entière du fichier.
if generated.startswith("```"):
    lines = generated.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    generated = "\n".join(lines)

if not generated.strip():
    print("[write-deepseek] ERREUR: génération vide — fichier NON écrit.", file=sys.stderr)
    sys.exit(1)

# ── Écriture du fichier cible ─────────────────────────────────────────────────
if args.mkdir:
    target_path.parent.mkdir(parents=True, exist_ok=True)

try:
    target_path.write_text(generated, encoding="utf-8")
except Exception as e:
    print(f"[write-deepseek] ERREUR écriture: {e}", file=sys.stderr)
    print(generated)   # fallback : ne pas perdre la génération
    sys.exit(1)

nb_lignes = generated.count("\n") + 1
etat = "écrasé" if args.force and target_path.exists() else "écrit"
print(f"[write-deepseek] ✓ Fichier {etat} : {args.target} "
      f"({len(generated)} caractères, {nb_lignes} lignes)")
print("─" * 60)
# Aperçu seulement : le fichier DOIT être relu en entier par l'appelant
# (une génération non relue peut avoir perdu une section — règle « zéro perte »).
apercu = generated.splitlines()[:30]
print("\n".join(apercu))
if nb_lignes > 30:
    print(f"…\n[write-deepseek] ({nb_lignes - 30} lignes de plus — RELIS le fichier "
          f"entier avant de t'en servir)")
