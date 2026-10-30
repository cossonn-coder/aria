# aria/files/extract.py
#
# Extraction locale du texte d'un fichier reçu sur Telegram (sprint 42).
#
# Appelé par WebExecutionRouter pour FILE_READ, et par l'interface
# Telegram pour lire un .pgn. Aucune écriture mémoire, aucun réseau.
#
#   .pdf          → texte des pages (pypdf), joint par "\n\n"
#   .html / .htm  → texte visible (bs4)
#   autre         → décodage UTF-8, repli latin-1 ; binaire → ValueError

from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

# Fenêtre de détection d'un fichier binaire : un octet nul dans les
# premiers 8 Ko suffit à le refuser.
_BINARY_PROBE_BYTES = 8192


def extract_text(path: str) -> str:
    """Texte brut du fichier `path`, selon son extension."""
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    raw = Path(path).read_bytes()
    if b"\x00" in raw[:_BINARY_PROBE_BYTES]:
        raise ValueError(f"fichier binaire non lisible : {Path(path).name}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # latin-1 décode n'importe quel octet : repli sans échec.
        text = raw.decode("latin-1")

    if suffix in (".html", ".htm"):
        return BeautifulSoup(text, "html.parser").get_text("\n", strip=True)
    return text
