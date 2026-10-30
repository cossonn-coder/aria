# Audit sprint 42 — lecture de fichiers envoyés sur Telegram

Date : 2026-10-30. Code lu à `main` (après `sprint-41` + correctifs échiquier).

## 1. Ce qui se passe aujourd'hui quand Nico envoie un fichier

Rien. `interfaces/telegram_interface.py:101-121` (`_add_handlers`) ne branche que trois
handlers, tous filtrés sur Nico :

| Handler | Filtre | Ce qu'il fait |
|---|---|---|
| `_handle_message` | `filters.TEXT & ~filters.COMMAND` | `Event TEXT` → kernel |
| `_handle_photo` | `filters.PHOTO` | télécharge `photo[-1]` dans `received_images/`, `Event IMAGE` {file_path, caption} → kernel |
| `_cmd_<nom>` | commandes de `meta_commands.COMMANDS` | métacommandes hors kernel |

Un document (PDF, .txt, .pgn, .docx, image envoyée « en fichier », audio…) n'est capté par
aucun handler : PTB l'ignore, **aucune réponse et aucune ligne au journal**. Un message vocal
aussi (`EventType.VOICE` déclaré dans `core/event.py`, jamais émis).

`core/event.py` déclare déjà `EventType.FILE`, jamais émis. `CognitiveEngine.classify`
(`cognition/cognitive_engine.py:83-120`) ne traite que `IMAGE` et `TEXT` ; tout autre type
tombe sur `UNKNOWN` → `llm_router` (le contenu dict serait passé tel quel au pipeline texte).

## 2. Ce qui est réutilisable : la lecture d'URL (sprint 23)

`execution/routers/web_router.py` `_handle_url_read` / `_read_slice` / `_cut_slice` :

- texte extrait (Tavily `extract`) → tranche de 100 000 car. coupée en fin de paragraphe ;
- synthèse fidèle par `LLMRole.DIGEST` (max 1 000 tokens), orientée par la consigne du message ;
- message enrichi `[Synthèse … :\n…]` + consigne → `LLMExecutionRouter` en `REASONING`,
  `skip_intent` ; c'est **la synthèse, pas le document**, qui entre dans l'historique
  (`aria_conversation`, écrit par `LLMExecutionRouter` → `memory/writer.py`, règle 1 respectée) ;
- lecture partielle : marqueur `URL_PARTIAL_MARKER … caractères a-b sur n]` relu au tour suivant
  (« lis la suite », `detect_url_resume`).

Pour un fichier, seule l'étape « obtenir le texte » change : extraction locale au lieu de
Tavily. Le reste (tranche, synthèse, délégation, suite) se reprend tel quel.

Le chemin échecs se reprend aussi : `detect_pgn` (`cognitive_classifier.py:128`) envoie un PGN
collé vers `CHESS_ANALYSIS` ; un fichier `.pgn` lu en texte prendrait ce chemin sans code neuf
côté échecs.

Le chemin image se reprend : une image envoyée « en fichier » (non compressée) peut suivre
`IMAGE_INPUT` comme une photo.

## 3. Formats lisibles et coût

Bibliothèques présentes dans le venv : `pypdf 6.10`, `pandas 3.0`, `beautifulsoup4`, `pillow`,
`groq 1.1`. Absentes : `openpyxl`, `python-docx`, `odfpy`.

| Format | Extraction | Dépendance | Remarque |
|---|---|---|---|
| Texte : .txt .md .csv .json .log .py .html… | décodage UTF-8 (repli latin-1) | aucune | .html : texte via `bs4` déjà présent |
| .pgn | texte → chemin `CHESS_ANALYSIS` existant | aucune | partie(s) analysée(s) comme un PGN collé |
| PDF avec texte | `pypdf` | présente | la majorité des PDF (factures, articles, docs) |
| PDF scanné (image) | pas de texte → OCR nécessaire | lourde (tesseract ou vision page par page) | hors scope recommandé : dire « PDF scanné, illisible » |
| .docx / .odt / .epub | zip + XML (stdlib) ou `python-docx` | aucune en stdlib | texte brut, mise en forme perdue |
| .xlsx / .ods | `pandas` + `openpyxl` | `openpyxl` à installer | tableau → texte CSV par feuille |
| Image en fichier (.jpg .png .webp) | chemin vision existant | aucune | comme une photo |
| Vocal / audio | transcription Whisper (Groq, clé déjà là) | aucune nouvelle lib | sujet distinct (`EventType.VOICE`), pas un « fichier » au sens strict |

Limite Telegram : un bot ne télécharge pas un fichier de plus de **20 Mo** (Bot API
`getFile`). Au-delà : répondre « fichier trop gros ».

## 4. Forme d'intégration conforme aux règles d'architecture

- Interface : handler `filters.Document.ALL` (filtré Nico) → téléchargement dans un dossier
  `received_files/` → `Event FILE` {file_path, file_name, mime_type, caption}. Pas de logique
  métier dans l'interface.
- Cognition : `classify` traite `EventType.FILE` → nouvelle opération `FILE_READ` (ou
  `IMAGE_INPUT` pour une image en fichier, `CHESS_ANALYSIS` pour un .pgn).
- Exécution : branche `FILE_READ` (dans `web_router` ou un petit router dédié) : extraction
  locale → mêmes tranche / synthèse / délégation que `URL_READ`. Le router n'écrit rien
  (règle 1) ; l'historique reçoit la synthèse via `LLMExecutionRouter`.
- Mémoire : le fichier brut reste sur disque, rien de neuf dans le palace. Palace prod non touché.

## 5. Questions de conception

1. Périmètre des formats (texte + PDF + .pgn + image-fichier seulement, ou aussi Office, ou
   aussi le vocal).
2. Sans légende : résumé automatique, ou simple accusé « reçu, que veux-tu en faire ? ».
3. Suite de lecture au-delà de 100 000 car. (« lis la suite ») : reprise du marqueur URL, ou
   pas de suite (premiers 100 000 car. seulement).
4. Questions de suivi (« et page 3, il dit quoi ? ») : l'historique ne contient que la
   synthèse ; relire le fichier sur une question de suivi = mécanisme en plus (dernier fichier
   reçu relu sur demande).
