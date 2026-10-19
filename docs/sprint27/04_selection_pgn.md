# Sprint 27 — Tronçon 04 : sélection des positions + en-têtes PGN indentés

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md` (§ Correctif), `docs/sprint27/audit_correctif.md`
(constats « en-têtes indentés », « occasion explosive qui évince le milieu de partie »,
« ouverture assumée »).

Vocabulaire (champ `CriticalPosition.kind` dans le code) :
`a` = erreur de Nico, `b` = occasion manquée après erreur adverse,
`c` = coup unique trouvé, `d` = occasion explosive.

## Objectif

1. **Bug des en-têtes indentés** : un PGN collé avec des lignes d'en-tête indentées
   (`  [Black "staroflexeur"]`) perd ces en-têtes → mauvaise couleur (run live, partie Dame
   précoce : `nico=white source=default`).
2. **Occasion explosive en bonus** (décision Nico) : erreurs / occasions manquées / coups
   uniques gardent leur budget ≤ 3 comme au sprint 26 ; la **meilleure** occasion explosive
   (score explosif le plus haut) s'ajoute en plus (≤ 4 positions au total). Elle n'évince
   jamais rien. Rejeu partie lettone : 12...Qxh5 (coup unique, écart 48) doit revenir.
3. **Ouverture assumée** (décision Nico) : pour les coups 1 à 10 (`move_number <= 10`,
   même borne que `_phase` → `"opening"`), une erreur (`a`) ou occasion manquée (`b`)
   n'est retenue que si la perte est **≥ 20** (au lieu de 10). Au-delà du coup 10, seuil
   inchangé (10). Ne s'applique **pas** aux occasions explosives (cherchées dès le coup 1,
   décision Nico après rejeu Von Hennig) ni aux coups uniques.
4. Occasion explosive quand le coup joué est le meilleur : **garder** (décision Nico) — rien
   à changer.

## Fichiers (vérifiés au code)

- `chess_coach/analysis.py` :
  - `parse_pgn` : passer à `chess.pgn.read_game` les lignes **dépouillées** (`strip()`),
    pas seulement trouver la 1re ligne en `lstrip()`.
  - `select_critical(plies, nico_color, explosive=())` : actuellement
    `selected = (errors + explosives + uniques)[:3]`. Devient : `(errors + uniques)[:3]`
    + la meilleure position de `explosive` (si non vide). Une position déjà retenue comme
    a/b/c ne peut pas être aussi la d (d exige perte < 10 → jamais a/b ; si elle coïncide
    avec une c déjà retenue, ne pas la dupliquer : garder la c). Repli « pire coup » :
    seulement si rien du tout n'est retenu (inchangé). Re-tri chronologique inchangé.
    Mettre à jour la docstring.
  - Seuil d'ouverture : dans la boucle de `select_critical`, la condition `p.loss >= 10`
    devient « ≥ 20 si `p.move_number <= 10`, sinon ≥ 10 ». Une perte 10-20 en ouverture
    n'est donc retenue sous aucune sorte (le coup n'est pas `best`, donc pas un coup unique).
- `tests/chess_coach/test_chess_coach.py` : remplacer
  `test_select_critical_order_ab_then_d_then_c` (ordre devenu faux) par les tests ci-dessous.

## Tests (cas nominal)

- `parse_pgn` / `analyze` sur un PGN aux en-têtes indentés (`[White "Test"]\n  [Black "staroflexeur"]\n  1. e4 …`)
  → `headers["Black"] == "staroflexeur"` (test sans Stockfish via `parse_pgn` suffit).
- `select_critical` avec plies synthétiques (helper `_ply` existant) :
  3 erreurs/coups uniques + 2 d → 4 positions, la d de meilleur score en plus, aucune a/b/c
  évincée.
- Ouverture : perte 12 au coup ≤ 10 → pas d'erreur retenue ; perte 12 au coup 15 → `a` ;
  perte 25 au coup 5 → `a`. (Adapter `_ply` si besoin pour fixer `move_number`.)
- Le test existant `test_analyze_detects_blunder` (3...Nf6?? perte ≫ 20 au coup 3) doit
  rester vert.

## Hors scope

- Moteur explosif (`chess_coach/explosive.py`) : tronçon 05.
- Router, légendes, notation, consignes : tronçon 06.
- Non-déterminisme moteur (Threads=8) : accepté, ne pas toucher aux options Stockfish.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` mis à jour (tronçon 04 ✅ + §REPRISE).
