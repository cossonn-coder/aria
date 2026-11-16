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

---

## Audit 2 — suites du run live (2026-11-13)

### A. Déclenchement (cas 4 non déclenché)

`cognition/cognitive_classifier.py:126-143` : `is_chess_image` est vrai si la description
vision contient `échiquier|échecs|chess`, ou si la légende matche
`_CHESS_CAPTION_RE = \b(échecs|échiquier|mat|trait|résous|résoudre|meilleur coup|position)\b`.
La légende « les blancs jouent, que faire ? » ne contient aucun de ces mots, et la
description vision n'a pas parlé d'échiquier. Correctif : ajouter `blancs?|noirs?` à la
regex (décision de Nico : ni « jouent », ni « plateau », ni « pièces »).

### B. Lecteur local sur la capture du cas 4

Capture : `received_images/AgACAgQAAxkBAAIRfWr3K1os…eQADPQQ.jpg` (858×931, chess.com
plein écran, thème vert, vue côté noirs, coordonnées dessinées dans les cases, dernier coup
surligné en jaune sur e8 et e7). `board_local.read_board` → `None`. Trois causes,
mesurées une à une :

1. **Repérage décalé d'une case** (`_find_lines`). Profils : x → (18, 103, 824), y → (52, 103, 824).
   La 1re « ligne intérieure » trouvée (x=18, y=52) est le **bord extérieur** du plateau :
   contre le fond sombre, il fait un bord net sur toute la longueur. Sur 9 lignes (2 bords
   + 7 intérieures), deux fenêtres de 7 ont le même score ; `argmax` prend la première.
   Le test « plein écran simulé » du tronçon 02 passait, mais sa capture de référence a
   peu de contraste avec son fond. Bonnes bornes : xs = 19…843, ys = 53…877.
2. **Alternance refusée** (`_alternates`), même avec les bonnes bornes : les cases
   surlignées (jaune) et les chiffres de coordonnées (coin haut-gauche des cases de la
   colonne de gauche, là où l'échantillon est pris à 1/8 de la case) font sauter le critère
   `spread < contrast / 2`, qui prend le maximum sur les 64 cases.
3. **Reconnaissance** : avec les bonnes bornes et sans le test d'alternance, la lecture fait
   **63 cases justes sur 64**. Seule erreur : le roi noir sur la case e7 surlignée, lu `b`.
   Le fond jaune n'existe dans aucune case de référence, et la distance euclidienne sur les
   pixels bruts y est sensible.

Grille réelle de la capture (rangée du haut d'abord, telle qu'affichée) :
```
.......R
.....PPP
...qNKQ.
...b....
..p.ppB.
.p.p..p.
...k....
......nr
```

### C. Relance « et si X ? »

- Aujourd'hui, « et si 1...Qe7+ ? » passe dans `classify_operation`
  (`cognitive_classifier.py:348`). Aucune règle déterministe ne s'applique, donc le message
  part au cache puis au classifieur LLM, et la réponse vient du LLM. Celui-ci voit
  l'historique (FEN + réponse, écrit par `image_router.py:299-309`), mais ne joue pas le
  coup et n'appelle pas Stockfish.
- Précédent pour une règle qui lit l'historique : `detect_url_resume` / `detect_doc_reread`
  (`cognitive_classifier.py:198-241`), via `bridge.load_conversation_history(key, n=2)`,
  avec un marqueur posé dans le tour `user`. Ici, le marqueur existe déjà :
  `[Position d'échecs lue sur image : <FEN>]`.
- Les routers lisent l'historique par le bridge (précédent : `web_router.py:189`).
  `ImageExecutionRouter` reçoit déjà `mempalace_bridge`, qui n'est plus utilisé depuis le
  sprint 24 (`image_router.py:73-88`).
- La résolution complète (Stockfish 3 s, texte, diagramme avec flèches, écriture de
  l'historique) est dans `image_router._handle_chess_board` (`image_router.py:258-311`),
  à partir de la FEN. Elle est réutilisable telle quelle à partir d'une FEN.
- Table opération → router : `core/kernel.py:56-70`.
