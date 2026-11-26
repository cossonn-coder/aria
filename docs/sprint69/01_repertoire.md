# Sprint 69 — tronçon 01 : répertoire connu d'ARIA (lignes 📚 et ❗ du bilan)

À lire avant : `CLAUDE.md`, `docs/sprint69/00_etat.md` (décisions), `docs/sprint69/audit_repertoire.md`
(code actuel, données mesurées).

## Objectif

Le bilan Telegram d'une partie dit à Nico où il en est de son répertoire (dettes 61-5 et 61-10) :

1. jusqu'où la partie a suivi son répertoire, et qui en est sorti (Nico ou l'adversaire) ;
2. si Nico a joué un coup habituel qui perd ≥ 10 pts, hors gambit assumé.

Deux lignes écrites par le code dans le bloc déterministe `_moves_line`, juste après la ligne 🔎.
Rien d'autre ne change : ni miniatures (`first_shown_move` intact), ni texte LLM, ni fiche, ni palace.

## Définitions (reprises de `first_shown_move`, `chess_coach/analysis.py:507`)

- `past_games` : liste `(couleur de Nico, coups UCI)` déjà passée à `analyze()` par
  `ChessRouter._past_games()` (`execution/routers/chess_router.py:1299`). On ne garde que les parties
  de la même couleur que Nico **et** différentes de la partie courante (`line != ucis`), exactement
  comme `first_shown_move`.
- Nombre de parties passées qui atteignent le demi-coup k : celles dont `line[:k] == ucis[:k]`.
- Sortie du répertoire : premier demi-coup (de n'importe quel camp) d'indice k tel que moins de 2
  parties passées (`_KNOWN_MOVE_GAMES`) partagent `ucis[:k + 1]`. Le nœud d'avant (`ucis[:k]`) est
  donc atteint par ≥ 2 parties.
- Dernier coup suivi : le demi-coup k − 1 (n'importe quel camp), avec le nombre de parties qui
  partagent `ucis[:k]`.
- Coup habituel : demi-coup de Nico d'indice j tel que ≥ 2 parties passées partagent `ucis[:j + 1]`.

## Comportement attendu

### Calcul (`chess_coach/analysis.py`, fonction pure, aucun moteur)

- Nouvelle fonction (nom au choix, ex. `repertoire_facts(plies, nico_color, past_games)`) qui rend
  `None` ou un petit dict / dataclass contenant ce qu'il faut pour écrire les deux lignes :
  - le dernier demi-coup suivi (`PlyAnalysis`) et son nombre de parties ;
  - la sortie : le demi-coup qui sort, qui l'a joué, et, si c'est Nico, son coup habituel au même
    endroit (le coup le plus fréquent des parties passées à ce nœud, SAN, et son nombre de parties) ;
    si c'est l'adversaire, combien de parties passées avaient ce coup (0 ou 1) ;
  - absence de sortie : la partie entière est dans le répertoire ;
  - la liste des coups habituels mauvais : coups habituels de Nico avec `loss >= 10` et non assumés
    (voir plus bas), chacun avec son nombre de parties ; `p.best_san` donne le meilleur coup.
- `None` quand aucun demi-coup n'est suivi (sortie au demi-coup 0) **et** aucun coup habituel mauvais :
  pas de ligne.
- La perte d'un coup habituel est celle de la partie courante (`p.loss`) : même position et même
  coup donnent la même évaluation, pas de moyenne sur les parties passées (décision 00_etat).
- `analyze()` (l. 797-848) appelle la fonction avec les `past_games` qu'il reçoit déjà et range le
  résultat dans un nouveau champ de `GameAnalysis` (l. 140), avec valeur par défaut `None` : les
  ~25 constructions `GameAnalysis(...)` des tests ne doivent pas changer.

### Gambits assumés

Un coup habituel n'est jamais signalé ❗ s'il est assumé :

- la position **après** le coup a, dans la table Lichess (`chess_coach/openings.py`, `_table()`,
  clé `board.epd()`), un nom contenant « Gambit » (couvre Blackmar-Diemer, Latvian Gambit,
  « Colorado Countergambit », Portsmouth, Göring, Scotch Gambit, Rousseau, Icelandic, von Hennig,
  Busch-Gass, Benko…) ;
- ou c'est l'une des deux positions sans nom choisies par Nico, en constante dans le module :
  `1.e4 e5 2.Nf3 Bc5 3.b4` et `1.e4 e6 2.d4 d5 3.Be3 Nf6 4.f3` (comparer l'EPD après le coup).

Seul le coup qui atteint la position est assumé : la suite reste jugée (5.d5 après
`1.e4 c5 2.Nf3 Nc6 3.b4 cxb4 4.d4 e6` est signalé, 6.exd5 du Göring aussi). Vérifié au code le
2026-11-26 : les positions après 5.d5 et après 6.exd5 n'ont pas de nom dans la table.

Import : `analysis.py` importe déjà depuis `chess_coach` ; `openings.py` est un module pur, l'import
`from chess_coach.openings import _table` (ou une petite fonction publique ajoutée dans
`openings.py`) ne crée pas de cycle — à vérifier en lançant les tests.

### Texte (`execution/routers/chess_router.py`, `_moves_line` l. 676)

Juste après `missed = _missed_line(analysis)` / son `append` (l. 697-699), ajouter les lignes
suivantes si le champ n'est pas `None`. Numérotation des coups avec `_move_label` (l. 150), comme
les autres lignes.

- Nico sort : `📚 Répertoire suivi jusqu'à 4.c3 (77 parties) ; tu en sors au coup 5 : 5.Bc4 au lieu de 5.Nxc3 (joué 40 fois)`
- L'adversaire sort : `📚 Répertoire suivi jusqu'à 3.b4 (29 parties) ; l'adversaire en sort avec 3...d5 (jamais vu)`
  — `(vu 1 fois)` si une partie passée l'avait.
- Pas de sortie : `📚 Partie entièrement dans ton répertoire (N parties)`.
- Une ligne par coup habituel mauvais : `❗ 5.d5, ton coup habituel ici (9 parties), perd 16 pts ; meilleur 5.a3`
  (perte arrondie à l'entier).
- Aucun demi-coup suivi : pas de ligne 📚 (la ligne ❗ peut quand même exister).

Pas de ⚠️ : il sert déjà à « Précision adverse ». Les chiffres ci-dessus sont des exemples de forme.

## Tests à ajouter (cas nominal)

- `tests/chess_coach/test_chess_coach.py` : avec `_line_plies` et `_ucis` (l. 234-249) :
  - Nico sort : 2 parties passées partagent un préfixe, Nico dévie → dernier coup suivi, coup
    habituel et nombre de parties corrects ;
  - l'adversaire sort → sortie attribuée à l'adversaire ;
  - coup habituel avec `loss = 16` → signalé ; même chose sur un gambit nommé (ex. `1.e4 d5 2.d4`)
    → non signalé.
- `tests/execution/test_chess_router.py` : un test `_moves_line` (modèle : l. 1057-1064,
  `_colors_analysis()`) avec le champ rempli → ligne 📚 et ligne ❗ présentes au bon format.

`pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Toucher `first_shown_move`, `select_critical`, le budget de miniatures ou leur seuil.
- Ajouter une consigne ou un fait au prompt LLM du bilan ; modifier le prompt AnalystAgent.
- Écrire quoi que ce soit dans le palace, changer la fiche `chess_game` ou `_past_games`.
- Gérer les transpositions, l'échiquier (Mini App), `/parties`.
- Rendre la liste des gambits configurable.

## Critère de fin

Tests ci-dessus verts, `pytest tests/ -q` vert, commit local. Validation réelle : run live
`docs/sprint69/02_run_live.txt` (Nico).
