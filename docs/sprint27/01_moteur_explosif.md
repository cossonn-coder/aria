# Sprint 27 — Tronçon 01 : recherche des coups explosifs (`chess_coach/`)

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md`, `docs/sprint27/audit_coups_explosifs.md`
(§2 et §2 bis : mesures Stockfish qui justifient les choix ci-dessous).

## Objectif

Ajouter au coach une 4e sorte de position critique, **« d — occasion explosive »** :
une position AVANT un coup de Nico où un coup « explosif » (sacrifice, coup forçant,
piège) tenait la fenêtre de tolérance alors que Nico a joué autre chose.
Module pur : aucun import mémoire / LLM / exécution (comme le reste de `chess_coach/`).

## Fichiers

- **Nouveau** `chess_coach/explosive.py` : recherche des candidats, score, sélection.
- `chess_coach/analysis.py` :
  - `CriticalPosition` gagne un champ optionnel `explosive: ExplosiveMove | None = None`
    (défaut `None` : les constructions existantes `CriticalPosition(kind=, ply=, score=)`
    dans les tests restent valides). `ExplosiveMove` est défini dans `explosive.py`
    ou `analysis.py` (au choix, sans import circulaire).
  - `analyze_game` : `engine.configure({"Threads": 8, "Hash": 256})` après `popen_uci`
    (constantes de module, pas de config). Effet de bord voulu : 1re passe plus profonde.
  - `analyze()` : après `analyze_game`, appeler la recherche explosive (elle ouvre son
    propre `SimpleEngine`, même configuration), puis passer ses positions `d` à
    `select_critical`.
  - `select_critical(plies, nico_color, explosive=())` : ordre de sélection
    **a/b (perte décroissante), puis d (score explosif décroissant), puis c**, ≤ 3,
    re-tri chronologique inchangé. Le repli « pire coup » ne joue que si rien n'est
    sélectionné (d compris).
  - Une position ne peut pas être à la fois a/b et d (d exige perte du coup joué < 10).

## Algorithme (intention ; constantes indicatives, ajustables dans le budget)

Budget global **30 s** (deadline vérifiée avant chaque position ; on s'arrête net).

1. **Positions éligibles** : demi-coups de Nico avec `move_number ≤ 20`,
   `35 ≤ win_before ≤ 75`, `loss < 10`. Ordre chronologique.
2. **Référence** : `analyse(board, Limit(time≈0.5), multipv=5)` → % de gain du meilleur
   coup (`win_best`) + 5 coups candidats. (Au budget 0,15 s, 2…Cf6 sort 6e : ne pas
   réutiliser la 1re passe pour la fenêtre — audit §2.)
3. **Candidats par forme** : coups légaux qui donnent échec, prennent, ou posent la
   pièce jouée sur une case attaquée par l'adversaire. Évalués en **une** recherche :
   `analyse(board, Limit(time≈0.5), root_moves=forme, multipv=len(forme))`.
   (8.Cd5 n'apparaît dans aucun MultiPV 6 jusqu'à d22 — audit §2 bis.)
4. Union MultiPV ∪ forme, en excluant le coup joué par Nico et le meilleur coup.
   Perte de chaque candidat = `win_best − win_candidat` (même budget). Ne garder que
   perte ≤ 15. Plafonner à ~3 candidats à approfondir (ceux qui sont des sacrifices
   ou des échecs/prises d'abord).
5. **Approfondissement** d'un candidat : jouer le coup, `analyse(Limit(time≈0.3), multipv=3)`
   sur la position obtenue → ligne (PV) et réponses adverses.
   - **Sacrifice** (pions, P=1 C=F=3 T=5 D=9) : matériel du camp de Nico perdu entre la
     position de départ et la fin de la ligne (candidat + PV adverse, ~6 demi-coups),
     `max(0, −delta)`. 2…Cf6 3.Dxe5+ Fe7 → 1 ; 8.Cd5 … exd5 exd5 → 2.
   - **Forçant** : échec +1 ; prise +0,5 ; menace (la pièce jouée attaque une pièce
     adverse de valeur supérieure ou non défendue) +0,5.
   - **Piège** (décision Q6) : réponse naturelle = l'adversaire **prend sur la case
     d'arrivée** (capture du plus faible attaquant). Si elle existe :
     `piège = %gain adverse après sa meilleure réponse − %gain adverse après la prise`
     (une analyse de plus, ~0,3 s). Sinon piège = 0.
     8.Cd5 : prise exd5 → noirs ≈ 57 % → 45,8 %, piège ≈ 11-13 (audit §2 bis).
   - **Volatilité** : écart max−min de % de gain entre les 3 réponses adverses du MultiPV 3.
6. **Admissibilité** (décision Q5) : perte ≤ 5 ; ou perte ≤ 15 **et** piège ≥ 10.
   Et explosif réel : sacrifice ≥ 1 **ou** piège ≥ 10.
7. **Score** : `sacrifice (plafonné 5) + forçant + piège / 5 + volatilité / 10`.
   Par position, garder le candidat de meilleur score → `CriticalPosition(kind="d",
   ply=<demi-coup de Nico>, score=<score>, explosive=ExplosiveMove(...))`.

`ExplosiveMove` porte au minimum : `san`, `uci`, `loss`, `win_after` (% de gain de Nico
après le coup), `pv_san` (≤ 6 demi-coups, candidat compris), `sacrifice`, `forcing`
(liste d'étiquettes : `check` / `capture` / `threat`), `trap`, `trap_reply_san`
(ou `None`), `volatility`, `score`.

Log unique en fin de recherche :
`chess_explosive positions=<examinées>/<éligibles> found=<n> duration=<s>`
(via `from logger import get_logger`).

## Tests à ajouter (`tests/chess_coach/`, skip si Stockfish absent comme l'existant)

1. Smith-Morra, Nico blancs, joue 8.e5 :
   ```
   [White "staroflexeur"]
   [Black "Test"]
   1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 Nf6 6. Bc4 e6 7. O-O a6 8. e5 *
   ```
   → `analyze(...)` : une critique `kind == "d"` au coup 8, `explosive.san == "Nd5"`,
   `explosive.trap >= 10`.
2. Dame précoce, Nico noirs, joue 2…Cc6 :
   ```
   [White "Test"]
   [Black "staroflexeur"]
   1. e4 e5 2. Qh5 Nc6 *
   ```
   → critique `kind == "d"` au coup 2, `explosive.san == "Nf6"`, `explosive.sacrifice >= 1`.
3. `select_critical` pur (sans moteur, objets construits) : ordre a/b puis d puis c.

Moteur multi-thread = non déterministe : lancer les tests 1-2 **trois fois** ; si l'un
d'eux est instable, le noter comme écart dans `00_etat.md` (ne pas élargir les seuils
en silence).

## Hors scope (ne PAS faire)

- Router, légendes, rendu, message enrichi, consigne LLM → tronçon 02.
- Toucher `summary.py` / `write_chess_game` : `kind="d"` sort tout seul dans `plies_json`.
- Maia / lc0, analyse d'ouverture sans PGN (#82), bilan joueur (#81), #85.
- Rendre budget / seuils configurables dans `config.py`.

## Critère de fin

`pytest tests/ -q` vert ; tests 1-2 verts sur 3 lancements ; durée de `analyze` sur le
PGN Morra < 40 s ; §REPRISE de `00_etat.md` mis à jour (fait + écarts + choix non tranchés).
