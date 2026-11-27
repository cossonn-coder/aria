# Sprint 69 — audit : répertoire connu d'ARIA (61-5 + 61-10)

Audit du 2026-11-26 sur `main` (`9d0fe20`, tag `sprint-68`). Lecture seule.

## 1. La demande

- 61-5 (Nico, 2026-11-19) : « ARIA doit savoir ce qu'il joue et le prévenir quand il sort de la
  meilleure ligne de son répertoire, y compris quand sa ligne habituelle est mauvaise ».
- 61-10 : VitalGas, pire coup 5.d5 (−21 pts) sans miniature car dans le répertoire (`first_move=8`).

## 2. Ce que le code fait aujourd'hui

Le répertoire n'existe qu'en négatif : il **masque** des coups, il n'est jamais **dit**.

### 2.1 Calcul (`chess_coach/analysis.py`)

```python
# l. 73
_KNOWN_MOVE_GAMES = 2

# l. 507-523
def first_shown_move(plies: list, nico_color: str, past_games=()) -> int:
    ucis = [p.uci for p in plies]
    known_lines = [line for color, line in past_games if color == nico_color and line != ucis]
    return next(
        (p.move_number for p in plies if p.color == nico_color
         and sum(line[:p.ply + 1] == ucis[:p.ply + 1] for line in known_lines) < _KNOWN_MOVE_GAMES),
        plies[-1].move_number + 1,
    )
```

- Coup connu = joué dans ≥ 2 autres parties de la même couleur après exactement les mêmes coups
  (pas de transposition). La nouveauté = premier coup de Nico non connu, qu'il dévie lui-même ou
  que l'adversaire l'ait sorti.
- `analyze()` (l. 797-848) : `first_move = first_shown_move(...)` puis `find_explosive(..., first_move)`
  et `select_critical(..., first_move)` ignorent tout coup d'avant. Le log porte `first_move=N`.
- **Seul effet** : aucune miniature (a, b, d) avant `first_move`. Rien d'autre ne lit `first_move` :
  il n'est ni dans `GameAnalysis`, ni dans la fiche, ni dans le texte.

### 2.2 Source des parties passées (`execution/routers/chess_router.py`)

```python
# l. 1299-1306
def _past_games(self) -> list:
    try:
        return [(g["nico_color"], [p["uci"] for p in json.loads(g["plies_json"])])
                for g in self.mempalace_bridge.load_chess_games()]
    except Exception:
        log.exception("chess_past_games ERROR")
        return []
```

Callers : `execute` (l. 1209, une partie) et `_execute_many` (l. 1343, plusieurs parties). Lecture par
le bridge (règle 2 respectée). Le kernel n'est pas concerné.

### 2.3 Texte

- `chess_router.py:1674-1679` : si aucune position (`n == 0`), consigne LLM « Partie entièrement dans
  le répertoire » — le mot n'est pas montré à Nico, seule la consigne le porte.
- `_progression_block` (l. 767, ligne 📖 vers l. 798-806) : ligne `📖 <groupe> (<couleur>) : V/N/D — %` par `opening_group`,
  statistique de résultats par famille, pas par coup.
- `_rank_line` (l. 623, segment ouverture l. 641-645) : rang de précision dans la même famille.
- `player_model.py:340-345` : badge « Répertoire » (5 parties d'un même groupe).

Aucune ligne ne dit « tu as suivi ton répertoire jusqu'au coup N », « tu en es sorti »,
« d'habitude tu joues X ici », ni « ton coup habituel perd ».

## 3. Données disponibles (palace, 2026-11-26)

622 fiches `chess_game` (318 blancs, 304 noirs). Chaque demi-coup de `plies_json` porte `san`, `uci`,
`loss`, `best_san`, `win_before`, `move_number` : l'arbre du répertoire **et** le jugement de chaque
coup habituel se calculent sans moteur, depuis les fiches.

Arbre (extraits, nombre de parties) :

| Couleur | Ligne | n |
|---|---|---|
| Blancs | 1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.c3 (Göring) | 77 |
| Blancs | 1.e4 c5 2.Nf3 Nc6 3.b4 | 29 |
| Blancs | 1.e4 c6 2.d4 d5 3.Nc3 dxe4 4.Bc4 | 22 |
| Blancs | 1.e4 d5 2.d4 dxe4 3.Nc3 (Blackmar-Diemer) | 20 |
| Noirs | 1.d4 f5 (Hollandaise) | 64 |

Coups habituels (≥ 2 parties, même chemin) dont la perte moyenne est ≥ 10 pts (seuil d'erreur
du sprint 61), 30 premiers demi-coups :

| Perte moy. | n | Coup habituel | Meilleur | Après |
|---|---|---|---|---|
| 26,6 [n=2] | 2 | 5.Bxf7+ | 5.Bb3 | 1.e4 Nf6 2.e5 Nd5 3.Nf3 d6 4.Bc4 Nb6 |
| 16,4 [n=9] | 9 | 5.d5 | 5.a3 | 1.e4 c5 2.Nf3 Nc6 3.b4 cxb4 4.d4 e6 (cas 61-10) |
| 15,0 [n=6] | 6 | 3.b4 | 3.Nxe5 | 1.e4 e5 2.Nf3 Bc5 |
| 13,7 [n=3] | 3 | 4.f3 | 4.e5 | 1.e4 e6 2.d4 d5 3.Be3 Nf6 |
| 12,2 [n=2] | 2 | 2...f5 | 2...e5 | 1.e4 Nc6 2.Nf3 |
| 11,7 [n=3] | 3 | 6.exd5 | 6.O-O | Göring … 4...d5 5.Bd3 Bg4 |
| 11,5 [n=2] | 2 | 6...Qe7 | 6...Bf5 | 1.e4 d5 2.exd5 Nf6 3.c4 e6 … |
| 11,3 [n=25] | 25 | 2.d4 | 2.exd5 | 1.e4 d5 (gambit Blackmar-Diemer) |
| 10,8 [n=2] | 2 | 8...Bg4 | 8...Nh5 | (même ligne) |
| 10,1 [n=2] | 2 | 2...f5 | 2...Nc6 | 1.e4 e5 2.Nf3 |

Script de mesure (jetable) : scratchpad de la session, non versionné.

## 4. Écarts et constats

1. **61-10 est une conséquence directe de `first_shown_move`** : un coup connu est hors budget de
   miniatures, donc un coup habituel mauvais n'est jamais jugé, quelle que soit sa perte. Le cas 5.d5
   se reproduit 9 fois [n=9] sans un mot.
2. Une partie du tableau ci-dessus sont des **gambits choisis** (2.d4 Blackmar-Diemer, 3.b4 contre
   2...Bc5 façon Evans) : la consigne Göring (`chess_router.py:1680`) traite déjà un gambit comme
   « choix assumé, pas une faute ». Les signaler à chaque partie serait du bruit.
3. « Sortir de la meilleure ligne de son répertoire » est ambigu : (a) Nico joue un autre coup que
   son coup habituel au même endroit ; (b) Nico joue un coup habituel moins bon qu'un autre coup qu'il
   joue aussi au même endroit ; (c) l'adversaire sort Nico de la théorie qu'il connaît.
4. Tout se calcule dans `chess_coach` (fonction pure sur `past_games`, déjà passés à `analyze`) :
   pas de nouvelle lecture palace, pas de nouvelle écriture, règles 1-3 respectées. Ligne écrite
   par le code (comme 🔎, 📖), pas par le LLM : évite l'invention (61-11).
5. Palace prod : lecture seule. Calibrage faible.

## 5. Hors scope (dettes adjacentes)

- Transpositions (même position par un autre ordre de coups) : non comptées aujourd'hui.
- Échiquier (Mini App) : aucune notion de répertoire ; non traité ici.
- 61-9 (deux noms pour une même ouverture) : sans effet sur l'arbre par coups.
