# Sprint 27 — Tronçon 08 : sélection — tournant, seuil du coup unique, fin du repli

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md` (§ Correctif 2),
`docs/sprint27/audit_run_live_07.md` (§2, §3, §6), puis `chess_coach/analysis.py`
(`select_critical`, `analyze`) et `chess_coach/explosive.py` (`find_explosive`,
`_search_position`) en entier.

## Objectif

Run live 07 : sur la partie Von Hennig, le repli « pire coup » a étiqueté 4.Bc4 « erreur » ;
12.Nxe6 n'est pas sorti (écart au 2e 18-19 < seuil 20) ; l'occasion explosive pouvait être le
meilleur coup de la 1re passe (2...Nf6). Sur la partie Écossaise / Göring, le tournant
(7...h6 −18, puni par 8.e5) n'est montré par aucune sorte.

1. **Suppression du repli « pire coup »** (`select_critical`, bloc `if not selected:`) :
   aucune position retenue → liste vide. Mettre à jour la docstring et le commentaire du
   test `test_select_critical_opening_threshold` qui parle du repli (le test reste vert tel
   quel).
2. **Seuil du coup unique 20 → 15** (`p.second_gap >= 20` dans `select_critical`, sorte c).
   Les exclusions existantes (décidé, forcé, reprise) restent.
3. **Nouvelle sorte e — « tournant »** : coup de Nico qui suit une erreur adverse et garde
   l'avantage. Pour un coup de Nico `p` et le demi-coup adverse précédent `prev` :
   - `prev.loss >= 15` ;
   - `p.loss < 10` (Nico ne rate pas la punition ; sinon c'est une b ou rien) ;
   - la partie n'était pas déjà décidée avant l'erreur : % de gain de Nico avant `prev`
     (`100 - prev.win_before`) ≤ 90.
   `CriticalPosition(kind="e", ply=p, score=prev.loss)`. Pas d'exigence sur la phase
   (un tournant en ouverture compte).
   Budget : les e entrent dans le budget ≤ 3 avec a/b/c. Ordre de remplissage :
   a/b par score décroissant, puis e par score décroissant, puis c. Un même ply ne figure
   qu'une fois : s'il est à la fois e et c, garder e. La d en bonus (4e position) est
   inchangée, et ne s'ajoute toujours pas sur un ply déjà retenu.
4. **Occasion explosive ≠ meilleur coup de la 1re passe** : dans `find_explosive`, exclure
   aussi `p.best_uci` des candidats de `_search_position` (aujourd'hui seuls le meilleur de
   la 2e analyse et le coup joué sont exclus). Le passage du paramètre est libre.

`summary.py` : `plies_json` reçoit la nouvelle valeur `kind="e"` sans changement de code
(structure inchangée, palace non touché).

5. **Variante du piège complète, jusqu'au gain** (retour Nico 2026-10-19 : « le piège doit
   être toute la variante jusqu'au gain ») — dans `_deepen`, branche `capture is not None` :
   - la ligne du piège (`trap_line_san`, aujourd'hui coupée à `_TRAP_LINE_PLIES = 8`) va
     jusqu'au gain : on la prolonge tant que l'échange continue, sur le principe de
     `_line_sacrifice` (au moins 8 demi-coups, puis arrêt au premier coup suivant qui n'est
     pas une prise ; jusqu'au mat si la PV mate), borne dure 16 demi-coups ;
   - si la PV de l'analyse `captured` (0,3 s) est trop courte pour cela, l'allonger (temps
     d'analyse de cette seule ligne augmenté, ex. 0,6 s) en restant dans le budget global
     `_BUDGET` (inchangé) ;
   - nouveaux champs de `ExplosiveMove` (avec valeurs par défaut) : `trap_end_fen` (FEN
     au bout de la ligne du piège) et `trap_end_win` (% de gain de Nico au bout de la ligne,
     = 100 − % adverse de l'analyse `captured`). Le bilan matériel et les pièces attaquées
     au bout de la ligne seront calculés par le router (tronçon 09) depuis `trap_end_fen`.

## Tests (cas nominal)

Dans `tests/chess_coach/test_chess_coach.py` (helper `_ply` existant, à étendre si besoin
pour `win_before` / `color`) :
- sélection vide quand aucune sorte ne s'applique (plus de repli) ;
- tournant : erreur adverse ≥ 15 suivie d'un coup de Nico à perte < 10 → `("e", ply)` ;
  pas de e si la partie était déjà décidée avant l'erreur ;
- seuil c : `second_gap=16` retenu en c ;
- exclusion du meilleur coup de la 1re passe : `find_explosive` sur la position Morra du
  test existant (coup 8, Nd5 attendu) avec `best_uci` du ply = `c3d5` → pas de d à ce ply
  (Stockfish requis, comme les tests explosifs existants) ;
- Morra 8.Nd5 (test existant) : `trap_line_san[0] == "exd5"`, ligne de plus de 8 demi-coups
  ou terminée sur un coup qui n'est pas suivi d'une prise, `trap_end_fen` renseigné.

Point de vigilance : `test_explosive_early_queen_nf6` (Dame précoce, d attendue 2...Nf6) —
au run live 07 la 1re passe donnait 2...Nc6 meilleur, mais si elle donne 2...Nf6, l'exclusion
du point 4 retire légitimement la d. Le faire passer 3 fois ; s'il devient instable pour cette
raison, le signaler au rapport (ne pas affaiblir l'exclusion).

`./venv/bin/pytest tests/ -q` vert.

## Hors scope

- Rien dans `execution/routers/chess_router.py` (libellé, légende, bloc de la sorte e :
  tronçon 09). Le router doit simplement ne pas planter sur `kind="e"` : vérifier
  `_KIND_FR[critical.kind]` dans `_build_enriched` → si KeyError, ajouter l'entrée minimale
  `"e": "tournant"` (le libellé définitif est au tronçon 09).
- Pas de changement des seuils a/b, de la fenêtre explosive, du budget de temps.
- Pas de stabilisation du moteur (non-déterminisme accepté).

## Critère de fin

Tests ci-dessus verts, suite complète verte, `00_etat.md` : tronçon 08 ✅ + §REPRISE.
