# Sprint 28 — tronçon 01 : difficulté des coups par Maia-2

À lire avant : `CLAUDE.md`, `docs/sprint28/00_etat.md` (§ Spike Maia-2 et décisions).

## Objectif

Chaque coup de Nico après le coup 10 reçoit une **difficulté en Elo** estimée par Maia-2,
stockée dans la fiche `chess_game` (`plies_json`) avec l'écart au 2e coup (`second_gap`).
Ces deux champs alimentent le modèle joueur (tronçon 02).

## Définition (arrêtée, spike du 2026-10-19)

- R = Elo de Nico dans l'en-tête du PGN (`WhiteElo` / `BlackElo` selon sa couleur) ;
  à défaut 1300 (constante du module).
- P = probabilité, selon Maia-2 (modèle `rapid`, `elo_self = elo_oppo = R`), que Nico
  joue le **meilleur coup Stockfish** (`best_uci`) dans la position `fen_before`.
  P bornée à [0,01 ; 0,99].
- difficulté = R − 400 · log10(P / (1 − P)), arrondie à l'entier.
- Calculée seulement pour les coups **de Nico** avec `move_number > 10` (Maia n'est pas
  fiable en ouverture : 1.e4 ≈ 1700). Les autres demi-coups : `difficulty = None`.
- **Une seule passe batchée** par partie (toutes les positions concernées dans un tenseur),
  pas un appel `inference_each` par coup (×3 à ×10 plus lent).

Référence d'implémentation qui marche : `~/.cache/aria-spike-maia/work/spike2.py`
(`inference.preprocessing` par position, `torch.stack`, `m(boards, elos, elos)`,
`inference._masked_softmax`, `inference.mirror_move` pour les coups des noirs — le
plateau est retourné quand c'est aux noirs de jouer).

## Installation (à faire en début de tronçon)

1. Dans le venv d'ARIA, **jamais** `pip install maia2` seul (versions épinglées : il
   rétrograderait `chess` 1.11.2 / `numpy` et retéléchargerait torch CUDA, plusieurs Go,
   et `/tmp` est un tmpfs en RAM). Commande exacte :
   `TMPDIR=$HOME/.cache/aria-spike-maia/tmp venv/bin/pip install --no-cache-dir --no-deps maia2==0.10.0 einops==0.8.0 pyzstd backports.zstd gdown beautifulsoup4 soupsieve`
   Vérifié en conception : ces paquets + torch 2.11 / chess 1.11.2 / numpy 2.4.3 du venv
   ARIA chargent le modèle et donnent des probabilités cohérentes avec le spike
   (position du coup 17 ci-dessous, R = 1300 : e5c4 0,30, b1c3 0,18, e5g4 0,13).
   Après installation, vérifier que `venv/bin/pip list` montre toujours `chess 1.11.2`.
2. Ajouter ces 7 lignes (épinglées) à `requirements.txt`, avec un commentaire disant
   qu'elles s'installent en `--no-deps`.
3. Poids : copier `~/.cache/aria-spike-maia/maia2_models/` (`rapid_model.pt` + `config.yaml`)
   vers `/home/nico/.cache/aria-maia/` (hors Nextcloud : 280 Mo). Nouveau champ
   `config.maia_models_dir = "/home/nico/.cache/aria-maia"` (section coach d'échecs de
   `config.py`). `model.from_pretrained(type="rapid", device="cpu", save_root=…)` ne
   télécharge rien si le fichier existe.

## Fichiers à toucher

- **Nouveau** `chess_coach/difficulty.py` : chargement paresseux du modèle (une fois par
  process, à la première analyse — la VM a 4 Go) ; fonction publique
  `assign_difficulty(plies, nico_color, nico_elo, models_dir)` qui remplit
  `p.difficulty` ; log `maia_difficulty OK n=<positions> duration=<s>`.
- `chess_coach/analysis.py` : champ `difficulty: float | None = None` dans `PlyAnalysis`
  (après les champs à défaut existants) ; appel dans `analyze()` juste après
  `analyze_game(...)`. **Un** `try/except Exception` autour de cet appel avec
  `log.exception` : Maia est une dépendance lourde optionnelle, son échec laisse
  `difficulty = None` partout et l'analyse continue (même logique que l'écriture de fiche
  non bloquante du router).
- `chess_coach/summary.py` : `plies_json` gagne `"difficulty"` (entier ou None) et
  `"second_gap"` (arrondi à 0,1 ou None). La présence de la clé `difficulty` marque une
  fiche de la **saison 1** (tronçon 02).

## Tests (cas nominal)

- `tests/chess_coach/test_difficulty.py` : la formule et le filtrage avec Maia remplacé
  par une fonction de probabilités factice (monkeypatch) — coup de Nico au coup 17 avec
  P = 0,5 → difficulté = R ; coup au coup 5 → None ; coup adverse → None.
- Un test réel `skipif` (poids absents) : la position du spike
  `r6r/pQp1n1p1/3qbk1p/3nN3/8/8/PP3PPP/RNB1R1K1 w - - 2 17`, meilleur coup `b7b3`,
  R = 1307 → difficulté > 1700 (spike : ≈ 1950).
- `test_summary.py` : `plies_json` contient `difficulty` et `second_gap`.

## Hors scope

- Pas de modèle joueur, pas de rendu (tronçons 02, 03).
- Pas de ré-analyse des fiches existantes (saison 1 repart de zéro, Q6).
- Ne pas toucher à la sélection des positions critiques ni au prompt.

## Critère de fin

`pytest tests/ -q` vert ; `chess 1.11.2` intact dans le venv ; le test réel passe en local.
