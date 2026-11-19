# Sprint 61 — tronçon 02 : ligne « Pointe », faits « cloue », consigne du Pourquoi

## Objectif

Rendre visibles les données du tronçon 01 (`CriticalPosition.point` et `.defenses`) :
1. un fait **« cloue X sur K »** dans toutes les lignes de faits ;
2. une ligne **« Pointe : »** écrite par le code sous le diagramme des erreurs de Nico ;
3. les mêmes données pour le LLM, et une consigne du **Pourquoi** qui s'en sert sans les
   répéter.

Prérequis : tronçon 01 livré (`chess_coach/combination.py`, `assign_defenses`).

## Fichier

`execution/routers/chess_router.py` uniquement (+ `tests/execution/test_chess_router.py`).

## Comportement attendu

### 1. Fait « cloue » — `_move_fact_items` (l. 265)

Après le coup, pour chaque pièce adverse (hors roi) clouée sur son roi
(`board.is_pinned(not mover, sq)`) qui ne l'était pas avant le coup : fait
`cloue Nb4 sur Ke7` (format `_square_label`). Placé après « attaque … », avant « décloue ».
Exemple : `14.Ba3 (attaque Nb4, cloue Nb4 sur Ke7)`.

### 2. Ligne « Pointe : » — dans `_variant_line` (l. 481), après `_compared_lines`

Présente seulement si `critical.point` existe et a une préparation (`prep` non `None`).
Construite à partir des libellés de coups (`_move_label`, numérotation depuis
`p.move_number` / `p.color` comme `_move_fact_items`). Forme, sur le cas de référence :

```
Pointe : 14.Ba3 cloue Nb4 sur Ke7 (roi amené par 13...Kxe7 ; 12.Qxe7+ a pris Be7, défenseur de Nb4), 15.Bxb4+ gagne Nb4.
Si 14...a5 (93 %) : 15.Bxb4+ Kd7 16.Ba3 ; si 15...axb4, 16.Rxa8.
```

- Sans clouage : `Pointe : 14.Ba3 prépare 15.Bxb4+, qui gagne Nb4.` (+ parenthèse défenseur
  si présent).
- Une ligne « Si … » par défense (3 au plus), probabilité arrondie, réfutation via
  `_format_line`, puis `; si <reprise>, <réponse>` quand `recapture` existe.
- Pas de ligne Pointe sans préparation (gain au premier coup : la suite comparée suffit).

Budget : la légende reste ≤ 1 024 caractères (`_CAPTION_MAX`, l. 867) ; `_split_entries`
coupe déjà l'entrée LLM au budget restant. Ne rien couper dans la partie code.

### 3. Message enrichi — `_build_enriched` (l. 1223), bloc `if critical.best_line_san:` (l. 1278)

Ajouter, si la ligne Pointe existe, une ligne `  pointe (données) : <texte de la ligne
Pointe sans « Pointe : »>` et, si des défenses existent, `  défenses réfutées (données) : …`
(même texte que les lignes « Si … »).

### 4. Consigne — `consigne` (l. 1321)

Ajouter, uniquement si au moins une position a la ligne « pointe (données) », un bloc
`[Consigne : …]` séparé (à la manière des blocs conditionnels ajoutés à `parts`, l. 1362-1431) :
pour ces positions, le Pourquoi garde (1) l'idée probable de Nico et (2) ce qu'elle a
négligé ; (3) devient **le schéma à retenir, en une demi-phrase**, tiré de la ligne
« pointe » (ex. « élimine le défenseur, attire le roi, cloue ») ; pas de coups répétés (la
pointe est sous le diagramme) ; le gain est là où la ligne « pointe » le place, jamais au
premier coup s'il n'y est pas ; entrée de 250 caractères au plus.
Ne pas modifier la consigne principale (l. 1321-1360) ni le prompt AnalystAgent.

## Tests (cas nominal)

1. `_move_fact_items` sur le cas de référence : `14.Ba3` porte `cloue Nb4 sur Ke7`.
2. `_variant_line` d'une `CriticalPosition` construite à la main (point + une défense
   `a5` avec reprise) : contient `Pointe : 14.Ba3 cloue Nb4 sur Ke7` et
   `si 15...axb4, 16.Rxa8`.
3. `_build_enriched` : la ligne `pointe (données)` et le bloc de consigne présents.

Les tests existants qui figent un texte de faits peuvent changer à cause du fait « cloue » :
les mettre à jour, pas contourner.

## Hors scope

- Pas de changement du calcul (tronçon 01), ni des sortes c / d / e.
- Pas de suivi avec relance moteur (dette).
- Pas de modification de l'historique ni des tailles `HISTORY_*`.

## Critère de fin

`pytest tests/ -q` vert ; sur le cas de référence, la légende de la position 1 contient
les deux lignes ci-dessus.
