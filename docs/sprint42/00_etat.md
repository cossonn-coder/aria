# Sprint 42 — lecture des fichiers envoyés sur Telegram

**Phase** : B figée (OK Nico 2026-10-30) — prêt pour `/sprint-auto sprint 42`.
**Branche** : `feat/sprint42-fichiers-telegram` (depuis `main` après `sprint-41`).
**Audit** : `audit_fichiers_telegram.md`.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_reception_fichiers.md` | handler document, `Event FILE` → `FILE_READ` → lecture comme une URL (texte, .html, PDF texte), `.pgn` → analyse, image en fichier → photo, > 20 Mo refusé | ⏳ |
| 02 | `02_pgn_plusieurs_parties.md` | PGN de plusieurs parties : toutes analysées, réponse groupée | ⏳ |
| 03 | `03_ocr.md` | OCR par la chaîne vision : pages PDF scannées (20 max), texte des photos | ⏳ |
| 04 | `04_run_live.md` | run live (Nico) | ⏳ |

## Décisions arrêtées

- Cible : lecture des fichiers envoyés sur Telegram (choix Nico).
- Formats : texte brut (UTF-8, repli latin-1, .html via bs4), PDF avec texte (`pypdf`), `.pgn`
  → chemin `CHESS_ANALYSIS`, image envoyée en fichier → chemin photo. Pas d'Office ni de vocal.
- Texte d'un PDF scanné ou d'une image : lu (OCR) et transmis à ARIA comme texte.
- OCR par la chaîne vision existante (`VISION_ROUTING_TABLE` : DeepSeek puis Groq ×3), pas de
  tesseract. Photos ordinaires : la description recopie aussi le texte lisible (un seul appel).
  `max_tokens` vision 1024 → 4096.
- PDF scanné : 20 pages transcrites au plus, au-delà ARIA le dit ; pas de suite.
- Fichier sans légende : résumé général automatique, comme une URL seule.
- Au-delà de 100 000 car. : « lis la suite » comme pour les URL (marqueur avec le chemin local) ;
  question de suivi = depuis la synthèse seule, pas de relecture du fichier.
- `FILE_READ` traité par `web_router` (même tranche / synthèse / délégation que `URL_READ`),
  extraction locale dans `files/extract.py`. Aucune écriture mémoire nouvelle.
- PGN de plusieurs parties : toutes analysées, sans plafond, réponse groupée à la fin
  (≈ 1,5-3 min par partie [n=2], ARIA bloquée pendant ce temps, #112 accepté).
- > 20 Mo (limite Bot API) : refus immédiat par l'interface.

## Dettes ouvertes par le sprint

(aucune pour l'instant)

## §REPRISE

Conception figée. Exécution : `/sprint-auto sprint 42` (tronçons 01 → 03, puis run live 04 par Nico).
