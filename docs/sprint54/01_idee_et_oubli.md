# Sprint 54 — tronçon 01 : idée et oubli d'une erreur de Nico

Lire avant : `CLAUDE.md`, `docs/sprint54/00_etat.md`, `docs/sprint54/audit_pensee_erreur.md`.
Branche : `feat/sprint54-pensee-erreur`.

## Objectif

Sur chaque erreur de Nico commentée (positions critiques de sorte a ou b, celles qui ont
`critical.best_line_san`), le LLM doit pouvoir dire **à quoi Nico a pensé** et **ce que son idée a
négligé**, au lieu de comparer seulement deux suites moteur.

## Fichier de prod à toucher

`execution/routers/chess_router.py` uniquement.

### 1. Nouvelle ligne de données (fonction dédiée, calcul pur python-chess)

Dans `_build_enriched`, boucle des positions critiques, à l'intérieur de
`if critical.best_line_san:` (là où sont écrites « suite du meilleur coup » / « suite du coup
joué »), ajouter une ligne :

    idée du coup joué, faits : <coup adverse précédent> (<ses faits>) ; ton coup : <faits d'intention> ; après ton coup : <clouages créés> ; temps : <N> s

Chaque segment est omis s'il est vide (le segment « temps » est omis sans pendule).

- **Coup adverse précédent** : `analysis.plies[p.ply - 1]` (s'il existe), avec ses faits via
  `_move_facts(prev.fen_before, [prev.san], prev.move_number, prev.color)` (réutilise le
  mécanisme déjà employé pour la sorte e, l. ~1060).
- **Faits d'intention du coup joué** (sur `p.fen_before`, coup `p.san`) :
  - `met à l'abri X` : la pièce jouée était attaquée par l'adversaire avant le coup et ne
    l'est plus sur sa case d'arrivée ;
  - `défend X` : pièce de Nico attaquée avant le coup, non défendue avant, défendue après ;
  - `décloue X` : reprendre le fait existant (`_move_fact_items` le calcule déjà).
- **Clouages créés** (`après ton coup`) : pièces de Nico qui, après le coup joué, sont clouées
  par une pièce à longue portée adverse sur une pièce de Nico de plus grande valeur (dame ou
  tour ; le roi est déjà couvert par `is_pinned`), et qui ne l'étaient pas avant le coup.
  Libellé : `Nc6 cloué sur Qd7 (par Bb5)`.
- **Temps** : temps passé sur `p` (liste `times` de `move_times`, déjà calculée dans `execute`) ;
  la transmettre à `_build_enriched` par un paramètre optionnel (défaut : pas de temps).

Ne pas modifier `_move_fact_items` : il sert à toutes les lignes « faits » et aux légendes.

### 2. Consigne « Pourquoi : »

Dans la consigne principale (l. ~1112), remplacer la partie « explique en 1 à 2 phrases pourquoi
le meilleur coup vaut mieux que le coup joué, en comparant uniquement ces deux suites… » par :
3 phrases au plus — (1) l'idée probable de Nico, au conditionnel (« tu voulais sans doute… »),
tirée de la ligne « idée du coup joué » (menace du coup adverse précédent, met à l'abri / défend /
décloue, temps : coup rapide = réflexe, long = réfléchi) ; (2) ce que cette idée a négligé, d'après
« après ton coup » et la suite du coup joué ; (3) ce que fait le meilleur coup, d'après sa suite.
Garder les règles existantes (citer « décloue », pièce prise/épargnée seulement si un fait le
montre, ne pas énumérer la variante, au plus un chiffre).

## Comportement attendu (partie de référence)

PGN de `00_etat.md`/audit (Scandinave, Nico noirs), position 1, 9...Qd7 après 9.Ba3 :

    idée du coup joué, faits : 9.Ba3 (attaque Qd6) ; ton coup : met à l'abri Qd6, décloue Nc6 ; après ton coup : Nc6 cloué sur Qd7 (par Bb5)

(Nc6 était déjà défendu par Qd6 : pas de « défend Nc6 ».)

## Tests (cas nominal, `tests/execution/test_chess_router.py`)

Un test sur la fonction de la nouvelle ligne : position après 9.Ba3 de la partie de référence,
coup 9...Qd7 → la ligne contient `9.Ba3 (attaque Qd6)`, `met à l'abri Qd6`, `décloue Nc6`,
`Nc6 cloué sur Qd7 (par Bb5)`. Un cas avec temps fourni → `temps : N s` présent.
`pytest tests/ -q` vert.

## Hors scope

- Pas de Maia, pas de moteur supplémentaire.
- Pas de changement des légendes / captions ni des lignes « Variante » / « Ton coup ».
- Pas de modification de `_move_fact_items`, ni du prompt AnalystAgent, ni de `soul.md`.
- Réflexions longues, sortes c/d/e : inchangées.
- Dette #115 (suivi en conversation) : non touchée.

## Critère de fin

Ligne présente dans le bloc pour les erreurs a/b, consigne réécrite, tests verts, commit local.
