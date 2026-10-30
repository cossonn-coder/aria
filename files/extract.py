# aria/files/extract.py
#
# Extraction locale du texte d'un fichier reçu sur Telegram (sprint 42).
#
# Appelé par WebExecutionRouter pour FILE_READ, et par l'interface
# Telegram pour lire un .pgn. Aucune écriture mémoire. Seul réseau :
# l'OCR des pages PDF scannées, par la chaîne vision (ImageRouter).
#
#   .pdf          → texte des pages (pypdf), joint par "\n\n" ; une page
#                   sans texte est transcrite depuis ses images (20 max)
#   .html / .htm  → texte visible (bs4)
#   autre         → décodage UTF-8, repli latin-1 ; binaire → ValueError

import base64
import mimetypes
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from llm.image_router import ImageRouter

# Fenêtre de détection d'un fichier binaire : un octet nul dans les
# premiers 8 Ko suffit à le refuser.
_BINARY_PROBE_BYTES = 8192

# Plafond de pages scannées transcrites par fichier (arbitrage Nico).
_MAX_OCR_PAGES = 20


def extract_text(path: str) -> str:
    """Texte brut du fichier `path`, selon son extension."""
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        return _pdf_text(PdfReader(path))

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


def _pdf_text(reader: PdfReader) -> str:
    """
    Texte des pages d'un PDF. Une page sans texte (scannée) est transcrite
    par la vision à partir de ses images, dans la limite de _MAX_OCR_PAGES ;
    au-delà, une mention finale indique l'arrêt.
    """
    router = ImageRouter()
    texts = []
    scanned = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        if not text.strip():
            scanned += 1
            if scanned <= _MAX_OCR_PAGES:
                text = "\n".join(router.transcribe(_data_url(img)) for img in page.images)
        texts.append(text)

    result = "\n\n".join(texts)
    if scanned > _MAX_OCR_PAGES:
        result += (
            f"\n\n[Transcription arrêtée à {_MAX_OCR_PAGES} pages scannées "
            f"sur {scanned}.]"
        )
    return result


def _data_url(img) -> str:
    """Data URL d'une image extraite par pypdf, transmissible au client vision."""
    mime = mimetypes.guess_type(img.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(img.data).decode()}"
