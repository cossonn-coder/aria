# Sprint 27 — audit « coups conseillés explosifs » (#87)

Date : 2026-10-19. Code audité : `main` @ `43a54f7` (tag `sprint-26`).

## 1. Ce que le coach fait aujourd'hui (code réel)

### `chess_coach/analysis.py`
- `analyze()` (seul caller prod : `chess_router.execute`, l. 144) :
  `parse_pgn → detect_color → analyze_game → select_critical`.
- `analyze_game(game, nico_color, engine_path, time_per_position=0.15)` :
  un `engine.analyse(board, Limit(time=0.15), multipv=2)` par position (N+1),
  Stockfish lancé une fois (`SimpleEngine.popen_uci`), **options moteur par
  défaut** (aucun `configure` : Threads=1, Hash par défaut). La machine a 16 cœurs.
- Par demi-coup, on garde : `best_san/best_uci` (PV 1), `pv_san` (6 coups de la PV 1),
  `second_gap` (écart en % de gain entre PV 1 et PV 2). **Les autres coups
  candidats ne sont pas conservés** ; seul l'écart 1→2 survit.
- `_tags()` : capture, échec, pion, roi, roque, recul, pièce en prise (coup joué uniquement).
- `select_critical()` : ≤ 3 positions AVANT un coup de Nico, sortes
  a (erreur ≥ 10), b (idem après erreur adverse ≥ 20), c (coup unique trouvé,
  `second_gap ≥ 20`, hors position décidée / forcée / recapture).
  Repli : pire coup de Nico si rien.

### `execution/routers/chess_router.py`
- Un PNG par position critique, **une seule flèche = `best_uci`** (`render_position`).
- Légendes `_caption` : « joué X, meilleur Y » ou « seul bon coup — bien joué ».
- Message enrichi `_build_enriched` : par position, coup joué, perte, meilleur coup,
  ligne PV 1, étiquettes, phase ; consigne LLM « n'invente aucun coup ni évaluation ».

### `chess_coach/summary.py`
- Fiche `chess_game` : `plies_json` sérialise `best_san` mais pas les candidats MultiPV.

### Constat
Aucune notion de « coup alternatif » : le coach ne connaît que PV 1 (et l'écart à PV 2).
#87 demande des **données nouvelles** (candidats MultiPV dans une fenêtre de tolérance
+ un score d'« explosivité »), pas seulement une reformulation.

## 2. Mesures Stockfish sur le cas de test Nico

Position après 1.e4 e5 2.Dh5 (trait aux noirs), Stockfish 17.1, Threads=1,
cp du point de vue des noirs, % de gain Lichess.

| Budget | Profondeur | Classement (cp) |
|---|---|---|
| 0,15 s (budget actuel) | 9 | Qe7 +49, Nc6 +35, d6 +18, Bd6 −33, Qf6 −15, **Nf6 −18 (6e)** |
| 0,5 s | 11 | Nc6 +41, d6 +40, **Nf6 +32**, Qe7 +26 |
| 2 s | 13 | **Nf6 +28**, Nc6 +34, d6 +30, Qe7 +22 |
| depth 14 (2,9 s) | 14 | Nc6 +36, d6 +33, **Nf6 +32**, Qe7 +21 |
| depth 18 (7,1 s) | 18 | Nc6 +30, d6 +22, **Nf6 +20**, Qe7 +18 |

[1 run par ligne, VM, Threads=1]. Référence Nico SF d22 [1 run] : 2…Cf6 −0,21 vs 2…Cc6 −0,40
(point de vue blancs).

Après 3.Dxe5+ : Fe7 seul coup (Qe7 −134 à −160 cp, 0,15 s) — cohérent avec Nico.

Lecture :
- Au budget actuel (0,15 s, d9), le gambit 2…Cf6 sort **6e** et à −18 cp : une fenêtre
  de tolérance calculée sur la passe actuelle le raterait ou le classerait au hasard.
- Dès d11-14, les 4 premiers coups tiennent dans ~15-20 cp (≈ 2 pts de % de gain) :
  la fenêtre fonctionne, à condition d'une **seconde passe plus profonde** sur les
  positions candidates.
- Coût : ~3 s par position à d14 en Threads=1. Analyser profondément toutes les
  positions de Nico (≈ 30-40) = 1,5-2 min → inacceptable sur Telegram. Il faut
  **restreindre les positions** (et/ou passer Threads > 1).

## 3. Points de conception ouverts (remontés à Nico)

1. Où apparaît le coup explosif (positions critiques existantes ? nouvelle sorte
   « occasion explosive » ? ouverture seulement ?).
2. Composantes du score v1 (sacrifice / forçant / piège / volatilité) et leur coût moteur.
3. Budget moteur : seconde passe profonde sur quelles positions, Threads.
4. Périmètre : #81 (bilan joueur) et rangement wing `echecs` / room par ouverture.

## 4. Règles d'architecture

Tout reste dans `chess_coach/` (module pur) + `chess_router` (message enrichi, légendes,
flèche). Aucune écriture mémoire nouvelle sauf si on enrichit `plies_json`
(via `write_chess_game`, règle 1 respectée). Rangement wing/room = palace prod.

## 2 bis. Exemple Nico : Smith-Morra, 8.Cd5!?

Position après 1.e4 c5 2.d4 cxd4 3.c3 dxc3 4.Cxc3 Cc6 5.Cf3 Cf6 6.Fc4 e6 7.O-O a6
(trait aux blancs). Stockfish 17.1, Threads=8, Hash=256 [1 run par ligne].

| Profondeur | Durée | MultiPV 6 (cp blancs, % de gain) |
|---|---|---|
| 14 | 3,3 s | e5 +42 (53,9), De2 +29, Ff4 −1, Fb3 −13, h3 −21, a3 −38 |
| 18 | 11,0 s | e5 +44 (54,0), De2 +20, Ff4 −7, Fb3 −18, h3 −41, Fe3 −46 |
| 22 | 35,2 s | e5 +51 (54,7), De2 +14, Ff4 −3, Fb3 −18, a3 −37, h3 −44 |

8.Cd5 forcé (`root_moves`) : d18 −98 (41,1 %), d22 −80 (42,7 %) → perte ≈ 12 pts de % de
gain vs 8.e5. **Absent du MultiPV 6 à toutes les profondeurs.**

Réponses noires à 8.Cd5 (d18, cp noirs, % de gain noirs) :
Cxe4 +94 (58,6), Fc5 +68 (56,2), **exd5 −46 (45,8)**, Cg4 −16 (48,5).
→ La prise « naturelle » 8…exd5 fait passer les noirs de ≈ 57 % à 45,8 % : c'est le piège.

Conséquences :
- Une fenêtre fixe ≤ 5 pts exclut 8.Cd5 ; il faut une fenêtre élargie quand le coup
  tend un piège (réponse naturelle perdante pour l'adversaire).
- Les candidats ne peuvent pas venir du MultiPV : il faut les générer par forme
  (sacrifice = pièce offerte / SEE négatif, échec, prise) et les évaluer un par un
  (`root_moves`), puis évaluer les réponses adverses pour le piège / la volatilité.
- Coût : ≈ 2,5 s par candidat à d18 + une analyse des réponses adverses. À multiplier
  par (positions candidates × candidats) → borne de temps indispensable.
