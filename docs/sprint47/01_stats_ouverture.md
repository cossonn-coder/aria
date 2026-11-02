# Sprint 47 — tronçon 01 : `/ouvertures <nom>`, statistiques d'une ouverture

## Objectif

`/ouvertures göring gambit` répond par les statistiques de cette ouverture, sur toutes ses parties enregistrées.
`/ouvertures` sans argument ne change pas. Aucun LLM, aucun passage par le kernel : c'est une métacommande en lecture seule.

## Fichiers à toucher

- `interfaces/meta_commands.py` : fonction de texte pure `opening_report_text(games, query)` à côté de `openings_text` ; description de `ouvertures` dans `COMMANDS` complétée, sur le modèle de `/logs N`.
- `interfaces/telegram_interface.py` : `_cmd_ouvertures` passe `" ".join(context.args)` à cette fonction s'il y a des arguments, sinon appelle `openings_text` comme aujourd'hui. Précédent d'argument : `_cmd_logs`.
- `tests/interfaces/test_meta_commands.py` : tests ci-dessous.

Fiches lues par `self.bridge.load_chess_games` (règle 2), déjà en place. Réutiliser `game_opening_group` de `chess_coach/player_model.py`.

## Comportement attendu

### Choix de l'ouverture

Comparaison sans accents ni casse (`göring`, `Goring`), entre `query` et le groupe de chaque fiche retenue :
- groupe exactement égal à `query` : lui seul, même si d'autres le contiennent ;
- sinon les groupes contenant `query` ;
- aucun : une ligne qui dit qu'aucune ouverture ne correspond et renvoie à `/ouvertures` ;
- plusieurs : une ligne qui les liste, sans statistiques ;
- un seul : son rapport.

Fiches retenues, comme `opening_stats` : `opening` renseigné et `outcome` parmi `win`, `draw`, `loss`.

### Rapport

Une section par couleur jouée, la plus jouée d'abord, séparées par une ligne vide. Exemple réel sur les fiches du 2026-11-02 :

```
Göring Gambit (blancs) : 8 V, 3 D — 73 % [11 parties]
Coups par partie en moyenne : 27,5
Elo adverse moyen : victoires 1545, défaites 1394
% de gain au coup 10 : victoires 69,1, défaites 62,1
% de gain au coup 20 : victoires 86,3, défaites 41,0
5 dernières : 4 V, 1 D — 80 %
```

Règles :
- **Bilan** : catégories à zéro omises (`8 V, 3 D`) ; % = victoires / parties, arrondi à l'entier ; singulier `[1 partie]`.
- **Coups par partie** : moyenne de `n_plies / 2`, 1 décimale.
- **Elo adverse** : moyenne de `elo_opponent` par issue, entier ; fiches sans Elo exclues.
- **% de gain au coup N** (10 et 20) : par issue, moyenne de `win_before` du demi-coup de `plies_json` où `color == nico_color` et `move_number == N`, 1 décimale ; une partie qui n'atteint pas ce coup est exclue de la moyenne.
- **Ordre et libellés** des issues : victoires, nulles, défaites. Une issue sans donnée est omise ; une ligne sans aucune donnée est omise. **Ne jamais inventer ni afficher de valeur par défaut.**
- **Pas de `[n=…]`** sur les lignes de détail (décision de Nico).
- **Décimales** avec une virgule.
- **5 dernières** : seulement s'il y a **strictement plus de 5** parties pour ce groupe et cette couleur. Tri par date de partie (`date`, où `.` vaut `-`), à défaut `timestamp[:10]` ; à égalité, par `timestamp`. Même format que le bilan.

## Tests à ajouter (cas nominal)

- rapport complet sur fiches factices : texte exact ;
- 5 parties : pas de ligne « 5 dernières » ; 6 parties : la ligne porte sur les 5 plus récentes, par date ;
- aucune partie au coup 20 : pas de ligne « coup 20 » ;
- `goring` trouve `Göring Gambit` ; un mot commun à deux groupes les liste ; un nom inconnu donne le message d'absence ;
- deux couleurs : deux sections.

## Hors-scope

- Pas de LLM, de texte sur ce qui fait gagner ou perdre, de pistes (écartés par Nico).
- Pas de nouvelle `CognitiveOperation`, pas de changement au kernel, au classifieur ou au router.
- Pas d'écriture mémoire.
- `openings_text` et la sortie de `/ouvertures` sans argument inchangés.
- Pas de noms français d'ouvertures (#169), rien sur l'horloge (#170).

## Critère de fin

`pytest tests/ -q` vert ; commit local.
