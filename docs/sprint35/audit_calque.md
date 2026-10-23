# Sprint 35 — audit : calque d'analyse sur l'échiquier chess.com (#94)

Date : 2026-10-23. Code au tag `sprint-34` (`0a33483`).

## 1. Besoin (Nico, sprint 29 et 2026-10-23)

Flèches vertes (meilleur coup) / orange (coup explosif) en transparence par-dessus
l'échiquier chess.com, variante affichée au survol de la flèche. Usage : analyse et
enseignement. **Fair-play** : uniquement sur l'écran d'analyse d'une partie terminée,
jamais en cours de partie. Le sprint 29 l'estimait « gros : extension navigateur + lecture
de position + lien ARIA, probablement plusieurs sprints ».

Hors cible : l'échiquier rejouable chessground hébergé par ARIA (autre moitié de #94).

## 2. Ce qu'ARIA calcule déjà (données disponibles)

`chess_coach/analysis.py` — `analyze()` produit un `GameAnalysis` :

| Donnée | Où | Portée |
|---|---|---|
| `fen_before`, `best_uci`, `pv_uci`, `pv_san`, `win_before` | `PlyAnalysis` (l. 50-80) | **chaque demi-coup** de la partie |
| coup explosif `uci`, `pv_san`, `trap_line_san`, `trap_reply_san` | `ExplosiveMove` (`explosive.py:57-87`) | positions critiques de sorte `d` seulement |
| variante du tournant `line_san` | `CriticalPosition` (l. 84-93) | sortes `c` / `e` |

→ Une flèche verte est disponible pour **toute** position de la partie ; l'orange pour les
seules positions `d`. Aucun calcul moteur supplémentaire nécessaire.

## 3. Ce qui est conservé aujourd'hui

- Fiche `chess_game` (`memory/writer.py:141-161`, appelée `chess_router.py:598`) :
  `summary_text` + `summary` (compteurs, niveau, ouverture). **Aucune donnée par coup** :
  pas de FEN, pas de meilleur coup. Les flèches ne peuvent pas être relues du palace.
- Diagrammes PNG : écrits directement par le router dans
  `config.image_output_dir/chess/<uuid>_<i>.png` (`chess_router.py:572-588`), hors
  `memory/writer.py` (artefact de rendu, pas une écriture mémoire). **Précédent** pour
  un fichier d'artefact (ex. JSON de calque) écrit à côté.
- `game_hash` = sha256 des coups UCI, 16 car. (`chess_router.py:592-594`) : clé stable
  par partie, réutilisable comme nom de fichier.

## 4. Infrastructure

- VM `vDebianIA`, LAN `192.168.1.124`, **`tailscaled` actif** → joignable depuis les
  appareils de Nico.
- Précédent de serveur HTTP sur la VM : `memory-viewer.service` (Flask, `0.0.0.0:5001`,
  autre projet).
- Aucun serveur HTTP dans ARIA (grep `aiohttp|fastapi|flask|http.server|uvicorn` : 0).
- Aucun navigateur sur la VM : rien de la partie navigateur n'est testable ici.

## 5. Contraintes techniques côté navigateur (connaissances, non vérifiées sur la VM)

- chess.com est en HTTPS : un `fetch()` de la page vers `http://<VM>` est bloqué (mixed
  content + CORS). Un **userscript** (Violentmonkey / Tampermonkey) contourne les deux
  via `GM_xmlhttpRequest` + `@connect`. Une extension empaquetée le peut aussi, mais
  Firefox exige la signature pour une installation permanente.
- Lecture de position : l'échiquier chess.com (`wc-chess-board`) expose les pièces en
  éléments `.piece` avec classes `wp|bn|…` et `square-XY`. Donne le **placement** des
  pièces, pas le trait. Structure non contractuelle : peut casser à une mise à jour.
- Restriction d'URL : `@match https://www.chess.com/analysis*` (écran d'analyse) ;
  exclut `/game/live/*`, `/play/*`.

## 6. Diagnostic / pistes

### Source des flèches
- **A. ARIA calcule à l'analyse Telegram, stocke, sert en lecture** : au passage dans
  `chess_router`, écrire un JSON par partie (placement FEN → meilleur coup, PV, explosif) ;
  un petit serveur HTTP en lecture seule répond `GET /overlay?fen=…`. Garde la valeur
  propre d'ARIA (Maia, explosif). Pas de recalcul (analyse ≈ 60 s CPU).
- B. Stockfish WASM dans le navigateur : pas d'ARIA, perd explosif / Maia. Ce n'est plus ARIA.
- C. Analyse à la demande déclenchée par le calque : recalcul 60 s, et ARIA pourrait
  analyser une position de partie en cours → **contraire au fair-play**.

### Garde fair-play structurelle de A
Recherche par position **déjà analysée** : le serveur ne calcule jamais rien ; une position
issue d'une partie en cours (non envoyée à ARIA) ne renvoie rien. La restriction d'URL
s'ajoute par-dessus.

### Règles d'architecture
- Règle 1 (écriture mémoire) : le JSON est un artefact de rendu comme les PNG, pas une
  écriture palace → hors `memory/writer.py`, comme le précédent PNG. Palace prod non touché.
- Règle 5 / « bypasser le kernel » : le serveur ne route aucun message et n'appelle aucun
  router ; il lit des fichiers. Pas de contournement du kernel, à condition qu'il reste
  en lecture seule sur ces fichiers.

### Limites connues de A
- Seules les parties envoyées à ARIA **après** le sprint ont un calque (renvoyer le PGN
  d'une ancienne partie le crée).
- Clé = placement seul (le DOM ne donne pas le trait) : collision possible si le même
  placement survient avec les deux traits dans une partie [non mesuré, rare].
- Partie JS non testable par pytest : validée au run live uniquement.

## 7. Réorientation (2026-10-23) : échiquier hébergé par ARIA, sans chess.com

Nico écarte chess.com (calque en partie live refusé par Claude) et retient un échiquier
hébergé par ARIA sur lequel il joue avec un ami, calque orange désactivable.
Contrainte : position affichée → flèche en ≤ 10 s.

### Mesure du délai (VM, 16 cœurs, Stockfish `Threads=8`, Maia-2 rapid)

Script scratchpad, `_search_position` (`explosive.py:279-328`) appelée telle quelle sur
6 positions de la partie du run 33 (demi-coups 8, 14, 20, 26, 32, 38), Elo 1600 :

| Étape | Durée |
|---|---|
| chargement Maia (une fois par process) | 14,3 s |
| position 1 (inclut le démarrage moteur) | 7,3 s → explosif e3 |
| positions 2-6 | 3,9 / 4,3 / 4,5 / 4,3 / 4,5 s → 1 explosif (Nd5) |

→ 4-7 s par position [n=6, une partie] **si Maia et Stockfish restent chargés** dans un
process qui tourne en continu. Coût dominant : temps fixes `_ROOT_TIME` 0,5 s ×2,
`_DEEP_TIME` / `_EVIDENCE_TIME` par candidat (≤ 3 candidats, `_MAX_DEEP`). Marge
vs 10 s : 3 s dans le pire cas mesuré. Une analyse Telegram en parallèle (même CPU)
n'a pas été mesurée.

### Mémoire

VM 4,6 Gio, 2,5 Gio disponibles au relevé ; `aria.service` 377 Mo sans Maia chargé
(2,2 Go après 4 analyses, #102 [1 relevé]). Un second process avec Maia résident
s'ajoute à ARIA quand celui-ci a aussi chargé Maia [non mesuré].

### Dépendances réelles de l'échiquier

`_search_position` n'utilise que `chess_coach` (python-chess, Stockfish, Maia) : ni
kernel, ni palace, ni LLM. L'échiquier n'a donc pas besoin du service ARIA, seulement
de sa bibliothèque d'échecs.
