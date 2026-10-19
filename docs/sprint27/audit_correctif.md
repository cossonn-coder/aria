# Sprint 27 — audit correctif post-run live 03 (A1-A5)

Date : 2026-10-19. Code audité : `ed7d4de` (tronçon 01), `e2d267c` (tronçon 02).
Fichiers lus en entier : `chess_coach/explosive.py`, `chess_coach/analysis.py`,
`execution/routers/chess_router.py`. Rejeux hors ligne : script scratchpad
(`analyze_game` + `find_explosive` + `select_critical`, Stockfish réel, mêmes options).

## 1. Run live 03 — constats bruts (journalctl 2026-10-19 11:56-12:01)

| Msg | critical | durée | verdict |
|---|---|---|---|
| M1 Morra | `d:6.Bc4` (6.b4), `d:8.e5` (8.Cd5) | 21,4 s | cible trouvée, bruit 6.b4 |
| M2 Dh5 | `d:2.Qh5` (2.d4), nico=white source=default | 6,3 s | ✗ mauvaise couleur |
| M3 letton | `a:2...f5`, `d:3...e4`, `d:4...Nf6` | 36,0 s | ✗ tout en ouverture |

Plainte de Nico (M3) : « il ne comprend pas le letton (gagner du développement
en gagnant des tempos, sortir l'adversaire de sa ligne) ; l'analyse reste sur
l'ouverture et pas sur le milieu de jeu ; à l'ouverture, sauf faute grave, je sais
ce que je fais ».

## 2. Constats au code

### C1 — M2 : en-têtes PGN indentés ignorés (bug, cause certaine)

`parse_pgn` (analysis.py) cherche la 1re ligne `lstrip().startswith("[")` mais
passe les lignes **non dépouillées** à `chess.pgn.read_game`. Reproduit :

```
'[White "Test"]\n  [Black "staroflexeur"]\n  ...'  →  headers Black = '?'
```

→ `detect_color` tombe en `default` (blancs). Le collage Telegram de Nico indentait
les lignes 2+ ; M1 marchait parce que `[White "staroflexeur"]` était la 1re ligne.
Correctif : `line.strip()` sur chaque ligne avant `read_game` (une ligne).

### C2 — Ordre de sélection : la sorte d évince le milieu de partie (A1)

`select_critical` : `selected = (errors + explosives + uniques)[:3]`. Rejeu M3 :
**12...Dxh5** (punition de la gaffe 12.O-O?? −50 pts, meilleur coup, écart au 2e
47,8 pts, non décidé à 88,7 %, pas une reprise) est une sorte **c** valide de score
47,8 — la plus instructive de la partie — et elle est évincée par les d.
`find_explosive` est en outre bornée aux coups ≤ 20 : par construction les d sont
toutes en ouverture/début de milieu.

### C3 — Pas de notion « ouverture assumée » (A2)

Toutes les sortes s'appliquent dès le coup 1. 2...f5 (letton, choix délibéré) sort
en `a` quand sa perte franchit 10 pts. Rejeu M3 hors ligne : perte 9,1 → `correct` ;
en live ≥ 10 → `a`. Le seuil se joue au bruit moteur près (C5).

### C4 — d se déclenche quand Nico a joué le meilleur coup (A3)

`_search_position` exclut le coup joué des candidats, mais ne demande pas que le
coup joué soit « calme » / non-meilleur. Rejeux : `d:5.Nf3` (played_best=True),
`d:8.e5` (played_best=True dans un rejeu sur deux), live `d:4...Nf6` (4...d5 coût 0).
Le kickoff M1 attendait pourtant `d:8.e5` avec 8.e5 = meilleur : ambiguïté de Q1,
pas un bug d'implémentation.

### C5 — Non-déterminisme fort (nouveau)

Threads=8 + limites en temps (0,15 s / 0,5 s / 0,3 s) ⇒ deux rejeux du même PGN
donnent des sélections différentes :

| PGN | rejeu 1 | rejeu 2 | live |
|---|---|---|---|
| M1 | d:2.d4, d:5.Nf3, d:8.e5 | d:6.Bc4, d:8.e5 | d:6.Bc4, d:8.e5 |
| M3 | — | d:1...e5, a:9...Kf8, d:10...Fd7 | a:2...f5, d:3...e4, d:4...Nf6 |

8.Cd5 : perte 10,5 / 9,9 / ≈12, piège 11,5 / 12,7 / 14 [n=3] — toujours au bord
des seuils 10 (perte des a, piège des d).

### C6 — Sacrifice mesuré à une coupure arbitraire de la ligne (bug)

`_deepen` : sacrifice = bilan matériel après `_LINE_PLIES = 6` demi-coups de la PV,
même au milieu d'un échange. Rejeu M3 : 1...d6 → ligne `d6 d4 e5 dxe5 dxe5 Dxd8+`
→ **sacrifice 9** (la dame prise, pas encore reprise par Rxd8). Faux positif massif
(score 5,2, en tête des d).

Inverse : 8.Cd5 → PV `Cd5 Cxe4 Te1` → sacrifice **1 pion** (e4), le cavalier offert
n'apparaît que via le piège. Le bloc enrichi dit « sacrifice : 1 pion(s) » → le LLM
écrit « sacrifier un pion » : l'erreur de texte vient **de nos faits**, pas du LLM.

### C7 — Qualité du texte LLM (A5)

Deux sources : (i) faits trompeurs (C6) ; (ii) le LLM ne voit pas l'échiquier et
invente des positions de pièces (« fou en e6 », « 3...Cc6 sacrifie trois pions »,
« 4...Cf6 attaque le pion e4 » alors que e4 est un pion noir). Le bloc enrichi ne
donne ni FEN, ni matériel, ni pièces attaquées. La consigne ne parle pas du choix
d'ouverture ni du « style » de Nico (gambits, tempo).

### C8 — Adjacents (hors scope, dettes)

- Groq 413 (ITPM 7000) sur chaque analyse d'échecs : historique 20 messages + bloc
  enrichi → repli DeepSeek systématique (+5-10 s). Préexistant.
- Légende « joué 8.e5 … (meilleur 8.e5) » : conséquence de C4.

## 3. Pistes (à arbitrer, cf. 00_etat.md)

- C1 : strip des lignes — trivial, pas d'arbitrage.
- C6 : mesurer le sacrifice sur une ligne **stabilisée** (prolonger tant que le
  dernier coup est une prise / échec, borne 10) et compter le matériel **offert**
  (valeur de la pièce posée en prise sur la case d'arrivée) même si refusé.
- C5 : limites en profondeur/nœuds plutôt qu'en temps réduit le bruit sans le
  supprimer (Threads > 1 reste non déterministe) ; marges d'hystérésis sur seuils.
- A1/A2/A3 : règles de sélection (choix de Nico).
- A5 : enrichir les faits (matériel offert réel, pièces/cases clés, FEN) + consigne.
