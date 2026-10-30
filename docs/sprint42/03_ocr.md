# Sprint 42 — tronçon 03 : OCR des PDF scannés et du texte des images

À lire avant : `CLAUDE.md`, `docs/sprint42/00_etat.md`. Branche : `feat/sprint42-fichiers-telegram`.
Prérequis : tronçon 01 fait (`files/extract.py`, `FILE_READ`).

## Objectif

Le texte d'un PDF scanné ou d'une image est lu et transmis à ARIA comme texte, par la chaîne
vision existante (pas de tesseract, arbitrage Nico).

1. **PDF** : une page dont `pypdf` ne tire pas de texte (vide après `strip()`) est transcrite
   par la vision à partir de ses images (`page.images`, pypdf présent, Pillow présent).
   20 pages transcrites au plus par fichier ; au-delà, le texte extrait se termine par
   « [Transcription arrêtée à 20 pages scannées sur N.] » (ARIA le dit à Nico via la synthèse).
2. **Photos et images en fichier** : la consigne de description demande en plus la
   transcription intégrale du texte lisible. Un seul appel vision.

## Constat au code (vérifié le 2026-10-30)

- `llm/image_router.py` : `VISION_ROUTING_TABLE` (DeepSeek, puis groq1-3), `ImageRouter`
  `handle_input` construit deux prompts (avec / sans légende, l. ~131-153) puis
  `_run_vision(source, prompt)` → `_dispatch(table, "describe", …)` avec repli.
- `llm/vision/groq_vision.py` `describe(image, prompt)` : `max_tokens` fixé à 1024 (l. ~60),
  `image` = chemin local, URL http, ou chaîne passée telle quelle (une data URL convient).
- `execution/routers/image_router.py` : photo → `handle_input` → description renvoyée ou
  injectée au pipeline texte selon la légende ; inchangé ici.

## Fichiers à toucher

- `llm/vision/groq_vision.py` : `max_tokens` 1024 → 4096 (une page dense ou une capture d'écran
  dépasse 1024 tokens).
- `llm/image_router.py` :
  - `ImageRouter.transcribe(image) -> str` : `_run_vision` avec une consigne « Transcris
    intégralement et fidèlement tout le texte visible, dans sa langue d'origine, sans résumer
    ni commenter. S'il n'y a aucun texte, réponds exactement : AUCUN TEXTE. » ; renvoie
    `""` pour « AUCUN TEXTE » ;
  - les deux prompts de `handle_input` gagnent une phrase : s'il y a du texte lisible
    (document, capture d'écran, ticket, panneau…), le recopier intégralement à la fin, après
    « Texte : ». Rien d'autre ne change dans ces prompts.
- `files/extract.py` : OCR par page sans texte dans la branche PDF (appel à
  `ImageRouter().transcribe` sur chaque image de la page, textes joints), compteur de 20 pages
  transcrites, mention finale si arrêt.

## Tests à ajouter (cas nominal)

- `transcribe` avec un client vision factice (voir `tests/images/fakes.py`) : texte rendu tel
  quel ; « AUCUN TEXTE » → `""`.
- `extract_text` sur un PDF sans texte avec une image (généré dans le test, Pillow) et
  `ImageRouter.transcribe` simulé → le texte simulé est dans le résultat.
- Les tests existants de prompts vision (`tests/images/`) restent verts ; en adapter un seul
  s'il compare le prompt mot à mot.

## Hors scope

- Tesseract, rendu de page PDF par poppler, OCR des pages vectorielles sans image.
- Changer le chemin photo (`execution/routers/image_router.py`) ou les modèles vision.
- Suite de lecture sur les pages scannées au-delà de 20.

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests verts.
