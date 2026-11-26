# Sprint 68 — tronçon 03 : recherche explosive plus courte, sans perdre de coups

Lire d'abord `CLAUDE.md`, `docs/sprint68/00_etat.md`, puis `audit_joueur_du_bas.md` §6.2 et §6.5.

## Objectif

Réduire la durée de `find_explosive` (46 et 49 s au journal [n=2]) **sans perdre un seul coup
explosif** sur un corpus de parties réelles. Nico tient à cette analyse (« c'est ce genre
d'analyse que je recherche ») : un réglage qui perd un coup n'est pas retenu.

## Constats (vérifiés au code le 2026-11-25)

- `chess_coach/explosive.py:find_explosive` lance `_search_position` sur chaque position
  éligible via `analysis.run_on_engines` : 8 Stockfish à 1 thread (`STABLE_ENGINE_OPTIONS`),
  temps demandé converti en nœuds fixes (`FixedNodesEngine`, `_NODES_PER_SECOND = 590000`).
- Mesure : 305 000 nœuds/s sur 1 thread [1 mesure, charge ~5] → chaque « seconde » demandée en
  coûte ~1,9.
- Paramètres de la recherche : `_ROOT_TIME = 0.5`, `_DEEP_TIME = 0.3`, `_MULTIPV = 5`,
  `_MAX_DEEP = 3`, `_REPLY_LINE_PLIES`… (`explosive.py` en tête). `_search_position` sert aussi
  à l'échiquier (`chess_coach/live.py`) : un réglage changé l'accélère aussi.
- Maia (`reply_distribution`, torch) est appelée depuis les 8 threads ; aucun
  `torch.set_num_threads` dans le dépôt : sursouscription CPU possible.
- **Ne jamais recalibrer `_NODES_PER_SECOND` pour « aller plus vite »** sans le traiter comme un
  réglage à valider : moins de nœuds = autre résultat.

## À faire

1. **Corpus.** Script `docs/sprint68/mesure_explosive.py` (lecture seule du palace par le
   bridge, comme `scripts/feedback_report.py`) : les fiches dont `minis_json` contient une
   miniature `kind == "d"`, les 8 plus récentes. Partie rejouée depuis `plies_json` (coups
   `uci`), couleur `nico_color`, Elo adverse `elo_opponent`.
2. **Référence.** Pour chaque partie : `analyze_game` puis `find_explosive(plies, nico_color,
   stockfish, elo_opponent, maia_dir, first_move=1)` au réglage actuel ; noter la durée et
   l'ensemble `{(ply, explosive.uci)}`.
3. **Candidats, dans cet ordre** (s'arrêter au premier qui suffit) :
   a. `torch.set_num_threads(n)` (n = 1 ou 2) pendant la recherche : ne change pas les résultats
      si les sorties Maia sont identiques — le vérifier ;
   b. `_MAX_DEEP` 3 → 2 ;
   c. `_DEEP_TIME` 0.3 → 0.2.
   Un candidat est retenu s'il donne **exactement** le même ensemble `{(ply, uci)}` sur tout le
   corpus et réduit la durée totale. Les candidats peuvent se cumuler (a puis b…), chaque cumul
   revalidé sur tout le corpus.
4. Résultats dans `docs/sprint68/mesure_explosive.txt` : durée par réglage, coups trouvés, écarts.
   Chiffres avec leur limite (`[8 parties]`, charge machine).
5. Appliquer le réglage retenu dans le code. Aucun retenu → rien ne change, et la mesure est
   consignée dans `00_etat.md` (dette chiffrée).

## Tests

Si un réglage change : le test existant de `find_explosive` / `_search_position` reste vert ; pas
de nouveau test de performance.

## Hors scope

Pas de changement de la logique d'admissibilité ni du texte des légendes ; pas de passage à
plusieurs threads par Stockfish ; échiquier (04-05).

## Critère de fin

`mesure_explosive.txt` livré ; `pytest tests/ -q` vert ; réglage retenu (ou aucun) justifié par
le corpus.
