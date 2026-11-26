# docs/sprint68/mesure_ecritures.py
#
# Sprint 68, tronçon 02 : chronométrage des écritures d'un bilan de partie,
# sur une COPIE du palace (jamais le palace prod).
#
# Usage : ./venv/bin/python docs/sprint68/mesure_ecritures.py [--keep] [--threads N]
#   --keep      : réutilise la copie existante au lieu de la recopier.
#   --threads N : torch.set_num_threads(N) avant les mesures (piste à arbitrer, dette 68-2).
# Chaque passage ajoute son bloc à mesure_ecritures.txt.
#
# Mesuré, 3 répétitions chacun :
#   - get_collection à chaud, sans écriture entre deux appels ;
#   - get_collection juste après une écriture (mtime de chroma.sqlite3 changé) ;
#   - l'embedding seul de chaque texte écrit ;
#   - chaque fonction de memory/writer.py appelée par un bilan, de bout en bout ;
#   - un upsert sur une collection déjà ouverte (ce que coûterait une écriture sans
#     réouverture du client).

import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import config  # noqa: E402

PROD = "/home/nico/.mempalace/palace"
# /tmp (tmpfs) est presque plein sur la VM : la copie (~140 Mo) va dans ~/.cache.
COPY = Path.home() / ".cache" / "aria_s68_palace_copy"
REPS = 3

# Le chemin doit pointer sur la copie AVANT tout import qui ouvre le palace.
if "--keep" not in sys.argv or not COPY.exists():
    shutil.rmtree(COPY, ignore_errors=True)
    COPY.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", "-a", PROD, str(COPY)], check=True)
config.mempalace_path = str(COPY)
if Path(config.mempalace_path).resolve() == Path(PROD).resolve():
    sys.exit("chemin effectif = palace prod : arrêt")

from mempalace.backends.chroma import ChromaBackend  # noqa: E402
from mempalace.palace import get_collection  # noqa: E402

import torch  # noqa: E402

from memory import writer  # noqa: E402
from memory.mempalace_store import get_by_metadata  # noqa: E402

lines = []
if "--threads" in sys.argv:
    torch.set_num_threads(int(sys.argv[sys.argv.index("--threads") + 1]))


def out(text=""):
    lines.append(text)
    sys.stdout.write(text + "\n")


def timed(label, fn, reps=REPS):
    """Chronomètre fn() reps fois ; ligne : médiane, min, max."""
    durations = []
    for i in range(reps):
        start = time.monotonic()
        fn(i)
        durations.append(time.monotonic() - start)
    out(f"{label:<55} médiane {statistics.median(durations):6.2f} s  "
        f"(min {min(durations):.2f}, max {max(durations):.2f}) [n={reps}]")
    return durations


# ── Données de taille réelle ─────────────────────────────────────────────────
games = get_by_metadata(config.mempalace_path,
                        {"$and": [{"wing": "aria_episodic"}, {"type": "chess_game"}]})
model_i = max(range(len(games["ids"])), key=lambda i: games["metadatas"][i].get("timestamp", ""))
fiche_text = games["documents"][model_i]
fiche_meta = {k: v for k, v in games["metadatas"][model_i].items()
              if k not in ("wing", "room", "type", "timestamp", "source")}
minis_json = fiche_meta.pop("minis_json", None) or "[]"
room = games["metadatas"][model_i]["room"]
prompt = (fiche_text + "\n") * (9000 // (len(fiche_text) + 1) + 1)
prompt = prompt[:9000]
answer = prompt[:3000]
caption = answer[:900]

out(f"=== torch threads = {torch.get_num_threads()} ===")
out(f"Copie : {COPY} (palace prod non ouvert en écriture)")
out(f"Fiche modèle : {games['ids'][model_i]} ; document {len(fiche_text)} car., "
    f"{len(fiche_meta)} métadonnées, minis_json {len(minis_json)} car.")
out(f"Prompt factice {len(prompt)} car., réponse {len(answer)} car., légende {len(caption)} car.")
out()

# ── Embedding seul ───────────────────────────────────────────────────────────
ef = ChromaBackend()._resolve_embedding_function(palace_path=config.mempalace_path, model_name=None)
start = time.monotonic()
ef([fiche_text])
out(f"{'embedding à froid (chargement du modèle)':<55} {time.monotonic() - start:6.2f} s [n=1]")
for label, text in (("fiche", fiche_text), ("prompt 9 000 car.", prompt),
                    ("réponse 3 000 car.", answer), ("légende 900 car.", caption)):
    timed(f"embedding seul : {label}", lambda i, t=text: ef([t]))
out()

# ── Ouverture de collection ──────────────────────────────────────────────────
get_collection(config.mempalace_path)
timed("get_collection à chaud, sans écriture entre", lambda i: get_collection(config.mempalace_path))


def reopen_after_write(i):
    # Écriture hors chrono (métadonnée seule), puis ouverture chronométrée.
    get_collection(config.mempalace_path).update(
        ids=[games["ids"][model_i]], metadatas=[{"mesure_s68": i}])
    time.sleep(0.05)
    start = time.monotonic()
    get_collection(config.mempalace_path)
    reopen.append(time.monotonic() - start)


reopen = []
for i in range(REPS):
    reopen_after_write(i)
out(f"{'get_collection juste après une écriture':<55} médiane {statistics.median(reopen):6.2f} s  "
    f"(min {min(reopen):.2f}, max {max(reopen):.2f}) [n={REPS}]")
out()

# ── Écritures du bilan, de bout en bout ──────────────────────────────────────
timed("write_chess_game", lambda i: writer.write_chess_game(
    fiche_text, f"mesure_s68_{i}", extra=fiche_meta, room=room))
timed("update_chess_game_minis", lambda i: writer.update_chess_game_minis(
    f"chess_game_mesure_s68_{i}", minis_json))
timed("write_interaction (prompt 9 000 + réponse 3 000)", lambda i: writer.write_interaction(
    text=f"USER:\n{prompt}{i}\n\nARIA:\n{answer}", intent_id="mesure_s68",
    intent_name="mesure", source="llm_execution_router"))
timed("write_conversation_turn user (9 000)", lambda i: writer.write_conversation_turn(
    "mesure_s68", "user", prompt + str(i)))
timed("write_conversation_turn assistant (3 000)", lambda i: writer.write_conversation_turn(
    "mesure_s68", "assistant", answer + str(i)))
timed("write_sent_message (légende 900)", lambda i: writer.write_sent_message(
    0, 900000 + i, caption + str(i), "photo", "mesure"))
held = get_collection(config.mempalace_path)
timed("upsert seul sur collection déjà ouverte (conversation 9 000)", lambda i: held.upsert(
    documents=[prompt + "held" + str(i)], ids=[f"mesure_s68_held_{i}"],
    metadatas=[{"wing": "aria_conversation", "room": "mesure_s68", "type": "conversation_turn"}]))

out()
out(f"Machine : {subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()}")

with Path(__file__).with_suffix(".txt").open("a", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n\n")
