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

5. **Règle « avantage clair, visible pour un humain »** (décision Nico 2026-10-19, remplace
   la « variante jusqu'au gain, 16 demi-coups » ; détail dans `00_etat.md` § Correctif 2).
   Un humain calcule 2 coups, 4-5 s'il est fort : la variante montrée doit rendre
   l'avantage clair vite, sinon la position n'est pas montrée.
   - **Helper partagé** dans `chess_coach/analysis.py` (importé par `explosive.py`, qui
     importe déjà ce module) : à partir d'une position `board` (avant le coup de Nico
     évalué), d'une ligne de coups (le coup de Nico en tête), du % de gain de Nico pour
     cette ligne et du fait que le moteur annonce un mat pour Nico, rend `(n, critère)`
     — `n` = nombre de demi-coups montrés — ou `None` si aucun avantage clair.
   - **Point d'arrêt** : le premier demi-coup `n ≥ 2` (au moins la réponse adverse) où un
     critère est vrai. Plafond normal `n ≤ 10` (5 coups de chaque côté). Au-delà de 10, on
     continue **seulement tant que les coups sont forcés** (échec, prise, ou mat annoncé par
     le moteur pour la ligne), borne dure 16. Ligne épuisée avant : critère évalué à sa fin.
   - **Critères** (point de vue de Nico, au point d'arrêt) :
     | critère | mesure |
     |---|---|
     | `material` gain matériel | matériel net ≥ +1 par rapport à `board` (valeurs 1/3/3/5/9) |
     | `crushing` position écrasante | % de gain de la ligne ≥ 80 — point d'arrêt : 1er `n ≥ 2` dont le coup suivant n'est ni échec ni prise (ou fin de ligne) |
     | `mate` attaque de mat | mat annoncé pour Nico — la ligne va jusqu'au mat dans la borne 16, sinon jusqu'à la borne |
     | `development` avance de développement | (pièces mineures hors de la rangée de départ + 1 si roqué) Nico − adversaire ≥ 2 |
     | `activity` avance d'activité | coups légaux de Nico − coups légaux adverses ≥ 10 (compter le camp qui n'a pas le trait sur une copie au trait inversé ; ignorer ce critère si un roi est en échec) |
     Mesures sur l'échiquier, **aucune analyse moteur en plus**.
   - **Lignes plus longues en 1re passe** : `analyze_game` coupe aujourd'hui la PV à 6
     demi-coups (`best_pv[:6]`). Garder la PV jusqu'à 16 demi-coups pour ce helper ; la
     ligne affichée pour les sortes a / b reste à 6 (champ séparé ou troncature au rendu,
     au choix, sans changer l'affichage a/b).
   - **Application** :
     - c (coup unique) et e (tournant) : ligne = PV du meilleur coup depuis `fen_before`,
       % = `win_before` ; retenue seulement si le helper rend un critère ;
     - d (occasion explosive), dans `_deepen` : ligne = coup explosif + réponse logique
       (prise naturelle si elle existe, sinon 1re réponse de `replies`) + suite moteur ;
       % et mat = analyse de la réponse logique (analyse `captured` existante, temps porté à
       0,6 s si la PV est trop courte, budget global `_BUDGET` inchangé). Pas de critère →
       candidat **non admissible**. `trap_line_san` = la ligne coupée au point d'arrêt (sans
       le coup explosif, commence par la réponse logique) ; nouveaux champs (valeurs par
       défaut) `trap_end_fen` (FEN au point d'arrêt), `trap_end_win`, `evidence` (critère).
     - `CriticalPosition` gagne `evidence` (critère) et la ligne coupée (pour c / e), au
       choix du nom — le router (tronçon 09) les affiche.

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
- helper d'évidence, sans Stockfish : une ligne qui gagne une pièce en 3 demi-coups →
  `(n ≤ 4, "material")` ; une ligne calme sans aucun critère → `None` ; une ligne où le
  critère n'arrive qu'après le 10e demi-coup sur des coups non forcés → `None` ;
- Morra 8.Nd5 (test existant) : `trap_line_san[0] == "exd5"`, `len(trap_line_san) ≤ 15`,
  `evidence` renseigné, `trap_end_fen` renseigné.

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
