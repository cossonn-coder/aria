# tests/files/test_extract.py
#
# Sprint 42, tronçon 01 : extraction locale du texte d'un fichier reçu.

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from files.extract import extract_text


def test_txt_utf8(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes("Échecs à Lyon".encode("utf-8"))
    assert extract_text(str(p)) == "Échecs à Lyon"


def test_txt_latin1_fallback(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes("Échecs à Lyon".encode("latin-1"))
    assert extract_text(str(p)) == "Échecs à Lyon"


def test_html_visible_text(tmp_path):
    p = tmp_path / "a.html"
    p.write_text("<html><body><h1>Titre</h1><p>Corps</p></body></html>", encoding="utf-8")
    assert extract_text(str(p)) == "Titre\nCorps"


def test_binary_raises(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc\x00def")
    with pytest.raises(ValueError):
        extract_text(str(p))


def test_pdf_with_text(tmp_path):
    # PDF d'une page généré à la main : police Helvetica + flux « Bonjour ARIA ».
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Bonjour ARIA) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    p = tmp_path / "a.pdf"
    with open(p, "wb") as f:
        writer.write(f)

    assert "Bonjour ARIA" in extract_text(str(p))


def test_scanned_pdf_page_is_transcribed(tmp_path, monkeypatch):
    # Sprint 42, tronçon 03 : page sans texte, une image → transcription vision.
    from PIL import Image
    from llm.image_router import ImageRouter

    img = tmp_path / "scan.png"
    Image.new("RGB", (50, 50), "white").save(img)
    p = tmp_path / "scan.pdf"
    Image.open(img).save(p, "PDF")

    seen = []

    def fake_transcribe(self, image):
        seen.append(image)
        return "Facture n° 42"

    monkeypatch.setattr(ImageRouter, "transcribe", fake_transcribe)

    assert "Facture n° 42" in extract_text(str(p))
    assert seen and seen[0].startswith("data:image/")
