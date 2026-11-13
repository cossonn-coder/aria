# Sprint 59 — audit : résoudre une position d'échecs envoyée en image

Date : 2026-11-13. Déclencheur : screenshot chess.com (vu côté noirs, « trait aux noirs »)
envoyé à 10:11 ; Aria lit une position illégale (deux rois en e1) et ne résout rien.
Image : `received_images/AgACAgQAAxkBAAIRC2r21CrIlMG_Gu1Vvov9rCC-zA-mAAINEGsbqI6xU9OaFhYZAeciAQADAgADbQADPQQ.jpg`
(250×250 px, sans coordonnées).
Position réelle : `r1bqkb1r/pp3ppp/2n2n2/2pp4/2B5/2NP1N2/PPP2PPP/R1BQK2R b KQkq - 0 1`.

## 1. Chemin actuel d'une photo

1. `interfaces/telegram_interface.py:273` `_handle_photo` (et `:358` pour un document
   image/*) : télécharge dans `received_images/`, crée `Event IMAGE`
   `content={"file_path", "caption"}`.
2. `cognition/cognitive_engine.py:86` : tout event IMAGE devient `IMAGE_INPUT`, sans
   appel LLM ; `interrogative=is_interrogative_caption(caption)`.
3. `core/kernel.py:56` : `IMAGE_INPUT` est routé vers `image_router`
   (`execution/routers/image_router.py`, `ImageExecutionRouter`).
4. `ImageExecutionRouter._handle_input` (l. 93) :
   - `internal_router.handle_input` = `llm/image_router.py` `ImageRouter.handle_input`,
     qui envoie une consigne de description générique à `VISION_ROUTING_TABLE`
     (deepseek-flash, puis groq qwen3.8 ×3) ;
   - `write_image_artifact` (épisodique) ;
   - légende interrogative → `_handle_input_enriched` : la description est injectée dans
     `LLMExecutionRouter` (REASONING), qui « résout » **sans moteur** ;
   - sinon : description brute + deux tours dans `aria_conversation`.

Ce chemin ne contient ni lecture de plateau, ni FEN, ni Stockfish. L'échec du 13.11
vient des deux bouts : une description vision fausse, puis un LLM qui raisonne à vue.

## 2. Ce qui existe déjà côté échecs (réutilisable)

- Stockfish : `config.stockfish_path` = `/usr/games/stockfish` ; `python-chess` 1.11.2.
- `chess_coach/render.py:115` `render_position(fen, orientation, best_uci, out_path)` :
  diagramme PNG avec flèche, orientation gérée.
- `execution/routers/chess_router.py` : analyse PGN (CHESS_ANALYSIS), `_format_line`
  (l. 153) pour numéroter une ligne SAN. Aucune entrée FEN seule.
- Contrat router (règle 4) : `{"text", "images": [...]}` déjà livré par Telegram
  (`_deliver`, type `images_text`).

## 3. Mesures : qui sait lire une grille ?

Consigne identique pour tous : « 8 rangées telles qu'affichées, lettres FEN ou '.' ».
Script : `scratchpad/vision_fen*.py`, `gem2.py` (hors repo).

| Modèle | Résultat |
|---|---|
| deepseek-flash (vision prod n°1) | faux ×2 [n=2] : rangées de 6 à 13 cases, différentes d'un appel à l'autre |
| groq qwen3.8-27b (secours prod) | faux ×2 [n=2] |
| claude-sonnet-4-5 | faux ×1 [n=1] : deux rois blancs |
| gemini-3.8-flash | juste ×1 [n=1] ; 3 appels sur 4 en échec (503 forte demande, timeout 90 s) |
| gemini-3.5-flash | juste ×3 [n=3, une seule image], ~10 s par appel |
| gemini-3.1-pro-preview | 429 (quota gratuit épuisé) |
| gemini-2.5-flash / 2.5-pro | 404 (retirés) |

Clé Gemini présente (`config.gemini_api_key`), non utilisée en prod aujourd'hui (seule
mention : `gemini_model = "gemini-2.0-flash"`, obsolète). Appel natif
`v1beta/models/<m>:generateContent` ; l'URL OpenAI-compatible renvoie 404 avec le client
`GroqVisionClient` actuel.

Photo d'échiquier **physique** : aucune mesure (pas d'image disponible). Risque non chiffré.

## 4. Stockfish sur la position (trait aux noirs, 3 s, multipv 3)

| Coup | Éval (noirs) | Ligne |
|---|---|---|
| 1…dxc4 | +4,71 | 2. O-O Be7 3. Re1 O-O 4. Bg5 h6 5. Bh4 cxd3 |
| 1…Qe7+ | +3,71 | 2. Be3 dxc4 3. dxc4 Be6 … |
| 1…Qa5 | +1,80 | 2. Bb5 d4 … |

Solution : 1…dxc4, qui gagne la pièce c4.

## 5. Constats pour la conception

- Une consigne de description ne peut pas devenir fiable sur deepseek ou qwen :
  la lecture de grille demande un modèle à part (Gemini 3.x flash mesuré) ou un lecteur local.
- Le seul point de décision possible est `ImageExecutionRouter._handle_input`, après
  la description vision : le classifier ne voit pas l'image (règle 5 : le kernel ne décide
  pas ; l'arbitrage local au router existe déjà pour le mode enrichi).
- Orientation : sans coordonnées, il faut la déduire des pièces (les pions blancs du côté
  du bas → blancs en bas). Règle de Nico : le camp au trait est en bas, sauf « blancs » ou
  « noirs » dans la légende.
- Une lecture illégale (`chess.Board.is_valid()` faux) doit être dite telle quelle, avec le
  diagramme lu, au lieu d'être « résolue ».
