# Sprint 29 — Tronçon 13 : légende expliquée par des faits coup par coup

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_run_live_11.md` §1.

## Objectif (décision Nico, Q2 A'')
Au run live 11, chaque légende répète « Position équilibrée, matériel égal, aucune pièce
attaquée » et n'explique pas la variante. Causes : la consigne interdit de décrire toute
attaque absente des lignes matériel / attaquées (qui portent sur la position AVANT), et
aucune donnée ne dit ce que fait chaque coup ; le % de gain n'est pas présenté comme
l'état de la position. Le code fournit désormais ces faits ; le LLM les raconte.

## Fichier
`execution/routers/chess_router.py` uniquement (`_build_enriched`, l. ~542, + un helper).

1. **Faits coup par coup** : helper pur `(fen, moves SAN) → texte` qui rejoue la ligne
   (python-chess) et donne, pour chaque coup, les faits observables :
   prise (pièce prise et case), échec, mat, roque, promotion, et pièces adverses
   **nouvellement** attaquées par la pièce jouée qui sont non défendues ou de valeur
   supérieure à l'attaquant (valeurs `_VALUES`). Coup sans fait → coup seul.
   Format indicatif : `14.Ba3 (attaque Bd6) 14...O-O (roque) 15.Bxd6 (prend Bd6) 15...Qxd6 (reprend)`.
   Ligne ajoutée sous chaque variante donnée au LLM : `ligne :` du meilleur coup
   (toutes sortes, depuis `p.fen_before`, `p.pv_san`), variante des sortes c / e
   (`critical.line_san`) et variante d (`e.trap_line_san`, depuis la position après le
   coup explosif). Libellé : `  faits : …`. Numérotation : réutiliser la logique de
   `_format_line` / `_reply_start`.
2. **Évaluation** : ligne `  évaluation : avantage Nico (68 %)` par position, depuis
   `p.win_before` : ≥ 60 « avantage Nico », ≤ 40 « avantage adverse », sinon « équilibre ».
3. **Consigne** (bloc l. ~590-607) : l'idée générale s'appuie sur l'évaluation et sur le
   but du meilleur coup (d'après ses faits) ; la variante est racontée avec les faits
   fournis ; l'interdit devient « Ne décris aucune attaque, défense, menace ou colonne
   absente des lignes matériel / attaquées / faits » ; interdit de recopier ou
   paraphraser « matériel égal » ou « aucune attaquée ». Les autres règles inchangées.

## Tests
- 1 test du helper : position initiale + `["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Bxc6"]`
  → contient « prend Nc6 » et la numérotation `1.e4`.
- `test_execute_returns_text_and_images_and_delegates_reasoning` : assertions sur la
  présence de `faits :` et `évaluation :` dans le contenu délégué ; adapter les
  assertions de consigne qui citent l'ancien interdit.

## Hors-scope
- Pas de changement de `_split_entries`, `_fit_entry`, `_explosive_lines` (hors ajout
  de la ligne faits), du prompt AnalystAgent, ni des consignes e / d sur le fond.
- Pas de faits stratégiques (structure de pions, colonnes ouvertes, sécurité du roi).

## Critère de fin
`pytest tests/ -q` vert.
