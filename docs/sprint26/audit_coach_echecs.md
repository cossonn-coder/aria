# Sprint 26 — Audit : coach d'échecs (PGN → moteur → positions illustrées)

**Date** : 2026-10-19 — **Base** : `main` @ `87dffa6` (tag `sprint-25`).

## 1. Besoin (Nico, 2026-10-19)

Nico colle une partie (PGN Chess.com) ou une image. ARIA doit :
1. reconnaître sa couleur (pseudo `staroflexeur`) ;
2. trouver les positions critiques avec un vrai moteur (Stockfish ou équivalent) ;
3. expliquer les idées de la position ;
4. illustrer chaque position critique par une **image d'échiquier**.

Constat de départ, d'après la conversation collée [n=1 conversation, 8 échanges] :
le LLM seul invente des coups et des évaluations. Exemples : « 1.d4 Df6 »
présenté comme du Gambit Dame, « 18...Rd6 sacrifie la dame », le conseil
6.Ce1 qui perd la dame. Il se trompe aussi de couleur sur la partie 1 :
il a fallu que Nico précise « je joue les noirs ». Sans moteur, le coaching
est faux. Le moteur doit fournir les faits, et le LLM se limiter à les
expliquer.

## 2. Pipeline actuel (vérifié au code)

```
Telegram (_handle_message / _handle_photo)        interfaces/telegram_interface.py
  → Event TEXT | IMAGE
  → AriaKernel.handle_event                        core/kernel.py:139
      classify → CognitiveEngine.classify          cognition/cognitive_engine.py:89
                 → classify_operation (TEXT)       cognition/cognitive_classifier.py:239
      dispatch → ExecutionDispatcher.dispatch      execution/execution_dispatcher.py
                 → _ROUTING_TABLE[op] → router.execute(payload)   (SYNCHRONE)
      normalize → AriaKernel._normalize            core/kernel.py:182
  → TelegramInterface.send(chat_id, result)        interfaces/telegram_interface.py:185
```

### 2.1 Classification (`classify_operation`)

Ordre actuel : image metadata → **URL** → reprise URL → web search →
génération image → message court → cache → LLM → UNKNOWN.

**Piège** : un PGN Chess.com peut contenir `[Link "https://www.chess.com/game/…"]`.
Les deux PGN collés par Nico n'en ont pas, mais l'export standard en
contient un. La règle 2 (`detect_url`) le classerait en `URL_READ`. Une
détection PGN doit donc passer **avant** la règle URL.

Aucune trace d'échecs dans le code (`grep -ri chess` : 0 hit en prod).

### 2.2 Contrat de sortie des routers → rupture nécessaire

- Règle inviolable 4 : un router retourne `{"text": str}` **ou**
  `{"path": str, "caption": str}`, jamais les deux.
- `_normalize` (kernel.py:182) : un `data["path"]` d'extension image produit
  `{"type": "image", …}`, sinon `data["text"]`.
- `TelegramInterface.send` : soit **une** `send_photo` (caption tronquée à
  1024 car.), soit du texte découpé à 4096.

Le coaching produit **du texte plus N images**, ce que le contrat actuel
ne permet pas. Une extension minimale touche trois endroits : le contrat
(texte de la règle 4 dans `CLAUDE.md`), `_normalize` et `send`.

### 2.3 Modèle de router « faits externes → LLM »

`WebExecutionRouter` (execution/routers/web_router.py) sert de patron
direct : il calcule des faits (résultats web), construit un message enrichi
`[… faits …]\n[Consigne : …]\n\n<message>` et délègue à
`LLMExecutionRouter.execute({"op_type": REASONING, "metadata": {..., "skip_intent": True}})`.
Il n'écrit rien en mémoire lui-même : c'est `LLMExecutionRouter` qui écrit
le tour de conversation (le message enrichi est le tour `user`), ce qui
respecte la règle 1. Les relances (« et si 18...Dxb5 ? ») voient donc les
faits moteur dans l'historique.

### 2.4 Environnement (VM)

| Élément | État |
|---|---|
| `stockfish` (apt Debian) | **non installé**, candidat `17-1` |
| `python-chess` (PyPI `chess`) | **non installé**, 1.11.2 dispo |
| `pillow` | installé (12.2.0) |
| `libcairo2` (requis par cairosvg) | **absent** |
| Police DejaVu Sans (glyphes ♔…♟ U+2654-265F) | présente |
| CPU / RAM | 16 cœurs / 4,6 Gio (1,3 Gio dispo) |

Conséquence : `chess.svg` + cairosvg ajouterait une dépendance système.
Un rendu **Pillow** (cases + glyphes DejaVu + flèches) n'en demande aucune.

### 2.5 Vision et lecture de position

Dette #60 (ouverte, acceptée) : le modèle vision **invente** la lecture fine
d'une position d'échecs. Une capture d'écran → FEN fiable demande un
reconnaisseur spécialisé (modèle dédié ou API tierce). Ce n'est pas le
pipeline vision actuel (`llm/vision/groq_vision.py`, `openrouter_vision.py`).

### 2.6 Synchronicité

`ExecutionDispatcher.dispatch` est synchrone et appelé depuis
`handle_event` (async). Une analyse moteur bloque donc la boucle pendant sa
durée, comme le font déjà les appels LLM. Le lock par utilisateur
sérialise les messages : c'est acceptable en mono-utilisateur, mais le
temps d'analyse doit rester borné. Ordre de grandeur : 40 coups ≈ 80
positions × 0,1–0,2 s ≈ 8–16 s [estimation, non mesurée].

## 3. Proposition d'architecture

```
PGN collé
 → classify_operation : detect_pgn() AVANT la règle URL → CHESS_ANALYSIS
 → _ROUTING_TABLE : CHESS_ANALYSIS → "chess_router"
 → ChessExecutionRouter.execute
     1. parse PGN (python-chess) ; couleur de Nico = en-tête White/Black == pseudo
     2. Stockfish local (UCI, temps borné/position) : éval avant/après chaque
        coup de Nico → chute d'éval → K positions critiques (K ≤ 3)
        pour chacune : FEN, coup joué, meilleur coup + ligne courte (PV), évals
     3. rendu PNG de chaque position (Pillow), orienté côté Nico,
        flèche coup joué / flèche meilleur coup
     4. message enrichi [Analyse moteur : …][Consigne : n'invente aucun coup…]
        → LLMExecutionRouter REASONING + skip_intent → texte
     5. retour {"text": texte, "images": [{"path", "caption"}, …]}
 → _normalize laisse passer images + text
 → send : photos (caption courte « Position 1 — 17...Cg4+ ») puis texte
```

Règles inviolables :
- **1 (écriture unique)** : le router n'écrit rien. Le tour de conversation
  est écrit par `LLMExecutionRouter`. Les diagrammes ne vont pas en
  mémoire épisodique : ce sont des artefacts dérivés.
- **2 (lecture unique)** : aucune lecture mémoire dans le router.
- **3** : rien côté agents.
- **4** : à **amender** (contrat `{"text", "images"}`), sur arbitrage de Nico.
- **5** : le kernel ne fait qu'ajouter une ligne de table, plus `_normalize`
  qui reste de la traduction pure.

Modules nouveaux (proposés) : `chess_coach/` (parse + moteur + rendu, sans
mémoire ni LLM) et `execution/routers/chess_router.py`.

## 4. Hors périmètre proposé (→ dettes)

- Capture d'écran ou photo d'échiquier → FEN (cf. §2.5, #60).
- Relances moteur sur une position citée en texte libre (« et après 18...Dxb5 ? »).
  En v1, la relance passe par le LLM avec les faits moteur présents dans
  l'historique, sans nouveau calcul.
- Questions d'ouverture sans PGN (« plan de la hollandaise contre 2.e3 ») :
  elles restent sur le LLM seul.
- Lien de partie Chess.com (récupération du PGN via l'API publique).

## 5. Risques

- Message enrichi lourd (PGN + lignes moteur) dans l'historique : il pèse
  sur les tours suivants et sur Groq (#73). DeepSeek prend alors le relais,
  ce qui est accepté depuis le sprint 25.
- Notation : python-chess produit du SAN anglais (N, B, R, Q, K) alors que
  le LLM répond en français (C, F, T, D, R). Il faut une consigne explicite,
  sinon la réponse mélangera les deux.
- Installation `apt install stockfish` : **sudo, par Nico**.
