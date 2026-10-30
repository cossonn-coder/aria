# Sprint 42 — tronçon 01 : réception des fichiers Telegram et lecture du texte

À lire avant : `CLAUDE.md`, `docs/sprint42/00_etat.md`, `docs/sprint42/audit_fichiers_telegram.md`.
Branche : `feat/sprint42-fichiers-telegram`.

## Objectif

Un document envoyé à ARIA sur Telegram n'est plus ignoré. Selon son type :

| Cas | Comportement |
|---|---|
| taille > 20 Mo (`document.file_size`) | réponse directe « Fichier trop gros : je ne peux lire que les fichiers de 20 Mo au plus. », sans téléchargement ni kernel |
| image (`mime_type` commençant par `image/`) | même chemin qu'une photo : `Event IMAGE` {file_path, caption} |
| `.pgn` (extension, insensible à la casse) | contenu lu en texte (UTF-8, repli latin-1), précédé de la légende si présente (`légende + "\n\n" + pgn`), traité comme un message texte (`_process_text`) → `detect_pgn` → `CHESS_ANALYSIS` |
| tout autre fichier | `Event FILE` {file_path, file_name, caption} → nouvelle opération `FILE_READ` → lecture comme une URL |

`FILE_READ` = même pipeline que `URL_READ` (`execution/routers/web_router.py`) : texte → tranche
de 100 000 car. (`_cut_slice`) → synthèse `LLMRole.DIGEST` orientée par la légende (sans légende :
résumé général, comme une URL seule) → `LLMExecutionRouter` en `REASONING` + `skip_intent`.
Au-delà de 100 000 car. : marqueur `URL_PARTIAL_MARKER` posé avec le **chemin local** du
fichier à la place de l'URL ; « lis la suite » relit le fichier depuis le disque.

## Fichiers à toucher (vérifiés au code le 2026-10-30)

- `interfaces/telegram_interface.py` : `_add_handlers` (l. ~101) ajoute
  `MessageHandler(only_nico & filters.Document.ALL, self._handle_document)`. `_handle_document`
  sur le modèle de `_handle_photo` (log `telegram_update … type=document`, verrou utilisateur,
  téléchargement, `_handle_with_waiting`, `send`). Pas de logique métier : seulement
  l'aiguillage du tableau ci-dessus.
- `config.py` : `self.file_receive_dir = str(BASE_DIR / "received_files")` à côté de
  `image_receive_dir` (l. ~111). `.gitignore` : ajouter `received_files/`.
- `cognition/cognitive_context.py` : `FILE_READ = "file_read"` dans `CognitiveOperation`.
- `cognition/cognitive_engine.py` `classify` : `EventType.FILE` → `FILE_READ` (sans LLM,
  comme l'image).
- `core/kernel.py` `_ROUTING_TABLE` (l. ~54) : `FILE_READ` → `"web_router"`.
- Nouveau module `files/__init__.py` + `files/extract.py` : `extract_text(path) -> str`.
  - `.pdf` : `pypdf` (présent dans le venv), texte des pages joint par `"\n\n"` ;
  - `.html` / `.htm` : texte via `bs4` (présent) ;
  - sinon : décodage UTF-8, repli latin-1 ; un fichier binaire (octet nul dans les
    premiers 8 Ko) lève `ValueError`.
- `execution/routers/web_router.py` :
  - `execute` : branche `FILE_READ` → `_read_slice(file_path, 0, caption ou "", metadata)`
    (le contenu du payload est le dict de l'event) ;
  - `_read_slice` obtient le texte et le titre selon la source : URL `http(s)` → `extract(url)`
    (Tavily, inchangé) ; chemin local → `extract_text(path)`, titre = nom du fichier
    (`Path(path).name`, le nom d'origine est dans le nom téléchargé, voir plus bas) ;
  - libellés pour un fichier : « Voici le texte d'un fichier… », « [Synthèse du fichier « nom »
    (caractères a-b sur n) : … ] », consigne de fin sans « cite l'URL ». Échec d'extraction →
    `[Fichier illisible : dis-le à Nico en une phrase.]`.
  - La reprise (`_handle_url_read` sans URL, `_PARTIAL_RE`) marche telle quelle si le chemin
    ne contient pas d'espace : le nom téléchargé doit donc être sans espace.
- Nom de téléchargement : `received_files/<file_unique_id>_<nom d'origine, espaces → _>`.

## Tests à ajouter (cas nominal)

- `tests/execution/test_web_router.py` : `FILE_READ` sur un .txt temporaire → le message
  délégué contient « Synthèse du fichier » et le nom ; fichier > 100 000 car. → marqueur de
  lecture partielle avec le chemin, puis reprise qui relit depuis le disque (fakes LLM existants
  du fichier).
- `tests/` (nouveau `tests/files/test_extract.py`) : .txt UTF-8, .txt latin-1, binaire →
  `ValueError` ; un PDF d'une page avec texte (le générer dans le test, p. ex. via `pypdf`
  ou un PDF minimal écrit à la main).
- `tests/cognition` : `classify` d'un `Event FILE` → `FILE_READ`.
- `tests/interfaces/test_telegram_interface.py` : aiguillage de `_handle_document` (trop gros
  → réponse directe sans kernel ; image → `Event IMAGE` ; `.pgn` → texte au kernel ; autre →
  `Event FILE`), sur le modèle des tests existants du fichier.

## Hors scope

- OCR (PDF scanné, texte des images) : tronçon 02. Ici, un PDF sans texte donne une
  synthèse vide ou « illisible », sans traitement spécial.
- Office (.docx, .xlsx, .odt), vocal.
- Plusieurs parties dans un `.pgn` : tronçon 02 (ici le `.pgn` part tel quel au kernel ;
  l'analyse ne lit encore que la première partie).
- Relire le fichier sur une question de suivi (seule la synthèse est dans l'historique).
- Aucune écriture mémoire nouvelle : `LLMExecutionRouter` écrit l'historique comme pour une URL.

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests verts ; `grep -n "FILE_READ" core/kernel.py
cognition/cognitive_engine.py execution/routers/web_router.py` montre le câblage.
