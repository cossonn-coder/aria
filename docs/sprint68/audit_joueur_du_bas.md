# Sprint 68 — audit : échiquier centré sur le joueur du bas + réponses adverses (61-4 + 62-9)

Audit du 2026-11-25 sur `main` (`65122cc`). Code lu en entier : `interfaces/board_interface.py`,
`interfaces/board/index.html`, `chess_coach/live.py` ; extraits de `chess_coach/difficulty.py`
(`reply_distribution`) et `chess_coach/explosive.py` (`_human_replies`).

## 1. La demande, mot pour mot

Nico, 2026-11-19 (61-4) :

> dans l'échiquier aria je préfère que l'analyse se concentre sur les coups du joueur en bas, et
> quand c'est le tour de l'autre joueur utiliser l'analyse pour anticiper les coups les plus
> probables et leur réponse (pièce surlignée et flèche semi transparente pour montrer le coup
> adverse anticipé et la réponse avec une flèche numérotée comme pour les miniatures)

Nico, 2026-11-20 (62-9) :

> l'échiquier aria doit pouvoir anticiper les différents coups logiques de l'adversaire et
> proposer des variations pour ces coups.

Les deux dettes décrivent la même fonction : 62-9 ajoute la variante de chaque coup anticipé.

## 2. Ce que fait le code aujourd'hui

### 2.1 L'analyse live sert toujours le camp au trait

- Page : `newPosition()` (`index.html:293`) envoie `POST /position {fen, elo_white, elo_black}`,
  sans rien sur l'orientation.
- Serveur : `BoardWorker.submit` (`board_interface.py:66`) prend l'Elo de l'adversaire du trait
  (`elo = elo_black if turn == WHITE else elo_white`, pour Maia qui prédit les réponses) ; le
  worker enchaîne 4 passes (`FACTORS = (1, 2, 4, 8)`) de `live.analyse_pass` ; cache
  `_finished[(fen, elo)]`.
- `analyse_pass` (`live.py:122`) calcule pour **le camp au trait** : `best` (bleu), `forced`
  (vert), `explosive` (orange), `trap` (cyan), `strategy` (jaune).
- `drawShapes()` (`index.html:323`) dessine ces flèches quel que soit le camp au trait.

Conséquence : quand c'est à l'adversaire du joueur du bas de jouer, l'échiquier propose ses
meilleurs coups, ses pièges et ses coups explosifs. C'est exactement ce que Nico ne veut plus.

Ce qui n'est **pas** propre au moteur live et reste un fait de la partie : flèche d'erreur du
coup joué (`playedError`, les deux camps), cercle blanc sur la pièce du coup joué
(`playedMove`), courbe, liste des coups, précision.

### 2.2 « Joueur du bas » = orientation, qui n'est jamais posée automatiquement

- Orientation : `ground.state.orientation`, blanc par défaut. Seuls `#flip` / `#flip-bar`
  la changent (`ground.toggleOrientation()`, `index.html:1293`). Pas sauvée dans
  `localStorage`.
- « Je joue » (`#playing`) : écrit le nom de Nico dans le champ du camp, sauvé, envoyé à
  `/game` pour l'historique. **N'oriente pas l'échiquier.**
- `openStored` (fiche ouverte depuis `/parties`, sprint 65) pose `playing = stored.playing`
  (camp de Nico dans la fiche) mais pas l'orientation : une partie jouée avec les noirs
  s'ouvre vue des blancs.
- Retourner l'échiquier ne renvoie pas la position au serveur (`#flip` n'appelle pas
  `newPosition`).

### 2.3 Les briques d'anticipation existent déjà

- `difficulty.reply_distribution(fens, elo, models_dir)` : coups les plus probables (Maia-2)
  du camp au trait de chaque FEN, `[(uci, p), …]`, ≤ 6 coups, jusqu'à 90 % cumulés, une passe
  batchée. Elo à passer : celui du camp **au trait** (ici l'adversaire du joueur du bas).
- `explosive._human_replies(engine, after, distribution)` : pour chaque coup de la
  distribution, analyse MultiPV restreinte (`root_moves`), rend
  `{"san", "p", "win", "line_san"}`. `line_san` commence par le coup adverse lui-même ;
  `line_san[1]` est donc **la meilleure réponse du joueur du bas**, la suite est la variante
  demandée en 62-9. `win` est du point de vue du camp qui vient de jouer avant `after`,
  donc ici du joueur du bas. Elle passe par `engine.analyse` : le `EngineProxy` la rend
  interruptible et l'approfondit passe après passe sans rien changer.
- Le cache Maia (`difficulty._load`) est déjà chargé par la page (`_load_maia_in_background`).

### 2.4 Flèches numérotées et pièce surlignée : Chessground 9.2.1 sait faire

Vérifié dans `chessground@9.2.1/dist/draw.d.ts` et `state.d.ts` :

- `DrawShape.label = {text, fill?}` : pastille de texte sur la flèche (équivalent des
  pastilles 1, 2, 3 des miniatures, `chess_coach/render.py:_draw_badge`).
- Pinceau à opacité libre (`DrawBrush.opacity`) : flèche semi-transparente = un pinceau de
  plus dans `drawable.brushes`.
- Pièce surlignée : un `DrawShape` sans `dest` (cercle, déjà utilisé pour le coup joué,
  pinceau `white`), ou `highlight.custom` (classes de cases).

Aucune dépendance à ajouter.

## 3. Écarts entre la demande et le code

| Point | Constat | Conséquence |
|---|---|---|
| Camp du bas inconnu du serveur | `/position` n'envoie pas l'orientation | Ajouter `bottom` au corps de `/position` ; flip doit renvoyer la position |
| Cache du worker | Clé `(fen, elo)` ; une même FEN peut maintenant donner deux analyses (selon le camp du bas) | Mettre le mode dans la clé |
| Elo Maia | `submit` prend l'Elo de l'adversaire du trait | En anticipation : Elo du camp au trait |
| Orientation | Jamais posée par « Je joue » ni par la fiche | Une partie de Nico avec les noirs s'ouvre à l'envers : l'anticipation porterait sur ses propres coups |
| Colonnes / couleurs de courbe | `saved.*` et `pointColor` se nourrissent de l'analyse live | Plus de piège / explosif / stratégie sur les coups du joueur du haut (voulu, à signaler) |

## 4. Règles d'architecture

- Échiquier hors kernel, aucune écriture mémoire, aucun LLM : inchangé. Rien à écrire dans le
  palace. Palace prod non touché → calibrage faible.
- `live.py` reste un module pur (moteur + Maia).

## 5. Ce que le run live doit démontrer

Sur le téléphone, une fiche jouée **avec les noirs** ouverte depuis `/parties` :

1. L'échiquier s'ouvre vu des noirs.
2. Position où Nico (en bas) est au trait : flèches habituelles (bleu, orange, cyan, jaune).
3. Position où l'adversaire est au trait : aucune de ces flèches ; à la place les coups adverses
   probables (pièce surlignée, flèche semi-transparente) et la réponse de Nico en flèche
   numérotée ; le panneau sous l'échiquier liste chaque coup anticipé avec sa probabilité et sa
   variante cliquable.
4. Retourner l'échiquier inverse les rôles à la position affichée.
5. `journalctl` : `board_analysis … result=anticipation` sur les positions de l'adversaire.

## 6. Lenteur (ajoutée au sprint, Nico 2026-11-25)

### 6.1 Journal prod (`journalctl -u aria`, journal du 2026-11-25 seulement)

| Mesure | Médiane | Max |
|---|---|---|
| Passe 1 (`board_analysis pass=1`) | 9,2 s [n=13] | 14,4 s |
| Passe 2 | 13,2 s [n=8] | 18,3 s |
| Passe 3 | 24,8 s [n=6] | 30,9 s |
| Passe 4 | 40,3 s [n=4] | 62,4 s |
| `/eval` (`board_eval`) | 1,6 s [n=16] | 3,4 s |

Ce que voit la page : bleu / vert dès l'analyse de tête (~0,5 s, `on_head`) ; explosif, piège,
stratégie seulement à la fin de la passe 1. `/eval` : une requête à la fois (`evalChain`), un
Stockfish lancé par appel (`position_eval`, `popen_uci` + `Threads 8, Hash 256`).

### 6.2 Profil local d'une passe 1 (`scratchpad/prof.py`, facteur 1, Elo 1700)

Ventilation [2 positions, machine de prod, service actif en parallèle] :

| Poste | Position coup 8 (`none`) | Position coup 13 (`decided`) |
|---|---|---|
| Total passe 1 | 13,1 s | 5,7 s |
| Maia `position_values` (stratégie) | 3,6 s | 1,4 s |
| Maia `reply_distribution` | 1,8 s | 1,0 s |
| `_human_replies` (piège + explosif), 0,3 s/appel | 3,1 s (10 appels) | 1,8 s (6 appels) |
| Recherche explosive (`_deepen`, `_search_position`) | 2,9 s | — |
| Têtes MultiPV | ~1,7 s | ~1,5 s |
| **Anticipation** (Maia 3 coups + 1 `_human_replies`) | 0,9 s | 0,85 s |
| `position_eval` (un `/eval`) | 0,87 s [3 appels], dont 0,15 s de recherche | |

Lecture : Maia pèse ~40 % de la passe 1 [2 positions] ; `/eval` passe ~80 % de son temps à
lancer Stockfish [3 appels]. Pendant les 4 passes, le worker garde Stockfish à 8 threads :
`/eval` et `/game` tournent en concurrence avec lui.

### 6.3 Ouverture d'un PGN collé (`/game`)

`analyze_game` seul, 42 demi-coups : 6,9 s et 7,9 s [2 runs locaux] (8 Stockfish ouverts à chaque
appel par `run_on_engines`, 0,54 s l'ouverture [1 mesure]). S'y ajoute `load_games()` pour
l'historique (lecture de toutes les fiches via le bridge, non mesurée). Une fiche ouverte depuis
`/parties` (`/stored`) ne recalcule rien.

### 6.4 Analyse Telegram (constat, hors échiquier)

Journal du 2026-11-25 [n=2 parties] :

| Étape | Partie 71 demi-coups | Partie 35 demi-coups |
|---|---|---|
| Réception → fin | 3 min 53 s | 2 min 21 s |
| `chess_analysis` (Stockfish + Maia + explosif) | 100 s (dont explosif 49 s, Maia 10,6 s) | 57 s (dont explosif 46 s) |
| Écriture fiche + progression | 19 s | 23 s |
| Préparation avant l'appel LLM (rappels mémoire, contexte) + DeepSeek en 402 | 23 s | 11 s |
| Anthropic (claude-haiku-4-5) | 13 s | 10 s |

**Correction (mesure du 2026-11-25 soir)** : un appel DeepSeek refusé coûte ~1,1 s [1 mesure],
plus 1 s d'attente avant le fournisseur suivant. Les 11 à 23 s de la ligne ci-dessus sont surtout
des rappels mémoire (§6.5). DeepSeek est passé en dernier des chaînes (commit `12b7f4e`) et
Anthropic en `claude-haiku-5-5` (commit `5a59749`), hors sprint, sur demande de Nico.


### 6.5 Où part le temps de l'analyse Telegram

Chronologie de la partie de 35 demi-coups (17:39:05 → 17:41:26) [n=1, la partie de 71 a le même
profil] :

| Étape | Durée | Source |
|---|---|---|
| Réception → début d'`analyze` (lecture fiches, embedder) | 13 s | journal |
| Stockfish (8 moteurs) + Maia difficulté | 11 s | journal |
| Recherche explosive (`find_explosive`) | 46 s | journal (49 s sur la partie de 71) |
| Diagrammes + résumé + écriture fiche | 16 s | journal (non ventilé) |
| Progression (`load_chess_games` + 2 `build_profile`) | 7 s | journal |
| Rappels mémoire + contexte + DeepSeek 402 | 26 s | journal (17:40:38 → 17:41:04) |
| Anthropic | 10 s | journal |
| Écritures épisodique + conversation | 11 s | journal |

Mesures locales (second processus, lecture seule) :

- `load_chess_games` : 0,5 s pour 606 fiches [3 lectures] ; `build_profile` 0,7 s [1 mesure].
- `retrieve_memories` à chaud : 1 à 2 s pour une phrase courte, 4,1 à 5,4 s pour une requête de
  9 000 caractères (taille du prompt d'analyse) [3 mesures] ; 24 s à froid (chargement de
  l'embedder). Le bilan d'une partie fait au moins 2 recherches vectorielles avec tout le prompt
  comme requête (`retrieve_memories`, `retrieve_by_intent`), plus le rappel de document et
  `build_context_block`. Ces rappels n'apportent rien au bilan : il a déjà toutes ses données
  (`skip_history`), et le journal montre un document hors sujet rappelé
  (`document_recall source=…inventaire.txt`).
- Stockfish 1 thread : 305 000 nœuds/s [1 mesure, charge ~5] contre `_NODES_PER_SECOND = 590000`
  supposé : chaque « seconde » demandée en nœuds fixes coûte ~1,9 s.

### 6.6 Machine

- Deux `node tools/splat/cuire_portraits.js` (projet Symbiose, lancés le 2026-11-20 par
  `xargs -P 12`) tournent à 100 % d'un cœur chacun depuis 5 jours.
- Swap : 8,6 Go utilisés sur 11 Go de RAM.
- Ces deux points ralentissent tout ce qui calcule (Stockfish, Maia, embedder) ; hors code ARIA.
