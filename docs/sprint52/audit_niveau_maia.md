# Sprint 52 — Audit : niveau joué estimé par Maia-2

Date : 2026-11-06. Code audité : `main` @ `d031988` (tag `sprint-51`).

## 1. Existant (vérifié au code)

- `chess_coach/difficulty.py` : Maia-2 **rapid**, chargé une fois par process (`_load`), `net.eval()`.
  Trois usages batchés : `assign_difficulty` (P(meilleur coup) et P(coup joué) des coups de Nico
  après le coup 10, Elo de Nico), `reply_distribution` (réponses humaines, explosifs),
  `position_values` (tête de valeur, échiquier live). `elo_self = elo_oppo` partout.
- Tranches Maia-2 (`maia2/utils.py`, `create_elo_dict`) : **11 catégories** — `<1100`,
  1100-1199, …, 1900-1999, `>=2000`. Les deux extrêmes sont ouverts : Maia ne distingue
  pas 900 de 1099, ni 2000 de 2500.
- `chess_coach/analysis.py:analyze` : appelle `assign_difficulty` dans un `try/except`
  (Maia optionnel) ; lit `WhiteElo` / `BlackElo` dans les en-têtes.
- `chess_coach/summary.py:summarize` : `elo_nico`, `elo_opponent` déjà stockés dans la fiche
  (métadonnées scalaires), ainsi que `accuracy` et `accuracy_opponent` (précision Lichess).
  `plies_json` garde `uci` et `difficulty` par coup, **pas les FEN** (rejouables depuis les uci).
- `execution/routers/chess_router.py` : `_header_lines` passe les Elo officiels au LLM (bloc
  enrichi) ; `_moves_line` (bloc déterministe sous le texte LLM) n'affiche **pas** les Elo.
- `interfaces/meta_commands.py` : `/parties` affiche l'Elo adverse par partie ;
  `/ouvertures <nom>` (`_color_section`) affiche « Elo adverse moyen » par issue.
  Ni l'un ni l'autre n'affiche l'Elo de Nico.

## 2. Mesure de la piste du kickoff

Prototype hors repo (scratchpad), lecture seule, parties des fichiers de run live
`docs/sprint*/*parties*.txt` / `*run_live*.txt` avec `WhiteElo`/`BlackElo`, ≥ 40 demi-coups,
dédoublonnées. Coups après le coup 10, positions à plus d'un coup légal.

### 2.a Vraisemblance brute (piste du kickoff)

Pour chaque camp et chaque tranche E : Σ log P_E(coup joué) ; niveau = tranche de vraisemblance
maximale ; fourchette = tranches à moins de 1,92 unités de log du maximum (≈ IC 95 %).
Deux variantes de `elo_oppo` (Elo officiel adverse / même tranche) : résultats quasi identiques.

| Partie (Elo officiels) | Blancs : estimation [fourchette] | Noirs : estimation [fourchette] |
|---|---|---|
| staroflexeur 1307 – Falestinhurra 1352 | ≥2000 [1450-≥2000] | ≥2000 [1250-≥2000] |
| staroflexeur 1338 – YouGotMyRook 1350 | 1850 [1150-≥2000] | ≥2000 [<1100-≥2000] |
| Mu7saad 1332 – staroflexeur 1354 | ≥2000 [1250-≥2000] | 1950 [1450-≥2000] |
| AaronDias16 1539 – staroflexeur 1622 | 1250 [<1100-≥2000] | 1850 [<1100-≥2000] |
| La_Bagouze 1570 – andreadipoggio 1568 | ≥2000 [1750-≥2000] | ≥2000 [1650-≥2000] |
| La_Bagouze 1624 – kushtrimchess 1696 | ≥2000 [1450-≥2000] | ≥2000 [1750-≥2000] |
| Adversaire 1600 – La_Bagouze 1613 | ≥2000 [1550-≥2000] | ≥2000 [1750-≥2000] |
| BaguetteChaussette 1180 – dusha28 1300 | ≥2000 [1250-≥2000] | 1950 [<1100-≥2000] |

Constats [8 parties, 16 camps, 1 run] :
- **Biais vers le haut** : 11 camps sur 16 estimés `>=2000`, pour des joueurs classés 1180-1700.
  Cause : Maia-2 haute tranche prédit mieux les coups en général (distribution plus piquée sur
  les coups naturels) ; la vraisemblance brute récompense la netteté du modèle, pas la
  ressemblance au niveau.
- **Fourchette inutilisable** : elle couvre 600 à 1000 points, souvent toute la plage.
- Courbes de vraisemblance plates : 0,5 à 9 unités de log entre les deux extrêmes de la plage.

### 2.b Variante calibrée (entropie)

Score_E = Σ [log P_E(joué) − E_{m~P_E} log P_E(m)] : un joueur de la tranche E devrait avoir
un score ≈ 0 à E. Niveau = 1re tranche où le score devient négatif.

- Écart absolu médian estimation / Elo officiel : **458** [n=16 camps, 1 run].
- Le score est dominé par un décalage propre à chaque partie (−10 à +9) ; la pente entre
  tranches est faible (2 à 18 unités sur toute la plage). Estimations dispersées de `<1100` à
  `>=2000` pour des joueurs de 1300-1700.
- Agrégé sur 4 parties de staroflexeur (92 coups, Elo moyen 1405) : toujours `>=2000`.
  Agrégé sur 3 parties de La_Bagouze (44 coups, 1602) : `>=2000`.

### 2.c Coût

Une passe batchée par camp sur 11 tranches : **6 à 17 s par partie** [8 parties, 1 run, CPU de la
VM], proportionnel au nombre de coups. Soit +5 à +15 % d'une analyse type, ou plus.

## 3. Diagnostic

La piste « niveau le plus vraisemblable selon Maia-2 + intervalle » **ne produit pas
d'information exploitable** dans notre cadre (20 à 45 coups utiles par camp, plage Maia
bornée à 1100-2000) :
- en version brute, elle afficherait « tu as joué comme un 2000+ » sur la plupart des parties ;
- en version calibrée, l'erreur médiane (≈ 460 [n=16]) dépasse la largeur de la plage utile.
Agréger sur plusieurs parties ne corrige pas le biais [2 joueurs, 3-4 parties chacun].

Hypothèse non testée : sur des dizaines de parties d'un même joueur, la variante calibrée
pourrait converger. Le test demande de rejouer les fiches prod (uci → FEN) : ≈ 10 s par fiche.

## 4. Ce qui reste solide pour « niveau joué »

- **Elo officiels** : lus, stockés, passés au LLM, mais absents du message et de `/ouvertures`
  pour Nico. Coût nul.
- **Précision Lichess des deux camps** : déjà affichée (🎯), déjà stockée.
- **Performance Elo** (formule FIDE : Elo adverse moyen + écart tiré du score) : vraie mesure
  du « niveau joué » sur plusieurs parties, calculable depuis les fiches (`elo_opponent`,
  `outcome`), sans moteur. Sans objet sur une seule partie.

## 5. Échiquier ARIA (ajout demandé par Nico le 2026-11-06)

Vérifié au code :
- `interfaces/board/index.html:622` affiche déjà « Précision : blancs X · noirs Y » (POST `/accuracy`,
  `line_accuracy`, même formule que le bilan). Champs `elo-white` / `elo-black` (l. 135-136),
  préremplis depuis les en-têtes du PGN chargé, envoyés à `/position` pour Maia, sauvés au rechargement.
- `interfaces/board_interface.py` : serveur HTTP « hors kernel : aucune écriture mémoire, aucun router,
  aucun LLM » ; `make_server` : « l'échiquier ne voit ni le kernel ni la mémoire ». Maia déjà chargé par
  le serveur (`_load_maia_in_background` au GET `/`), modèle partagé par process (`difficulty._load`).
- `bot.py:31` construit un `MempalaceBridge(get_by_metadata=…)` pour les métacommandes ;
  `start_board_server(submit_text)` reçoit déjà une dépendance injectée.

Conséquences par volet :
- (a) Elo sur la ligne précision : purement page, valeurs des champs. Aucun serveur.
- (b) Niveau Maia par camp : nouvelle route type `/accuracy`, une passe 11 tranches par camp
  (6-17 s par partie [n=8]) ; même verdict que §3, dépend de la mesure.
- (c) Tendance : l'échiquier doit lire les fiches. Chemin conforme à la règle 2 : injecter
  `bridge.load_chess_games` dans `start_board_server` (comme `submit_text`), route GET en lecture seule.
  Change la doctrine « l'échiquier ne voit pas la mémoire » (lecture seule, pas d'écriture).
  Route sans authentification sur `0.0.0.0:5002` (#166) : exposerait les stats de parties au réseau
  local ; lecture seule, à signaler.

## 6. Mesure sur les fiches prod (copie du palace, 2026-11-06)

70 fiches sur 166 mesurées (arrêt d'analyse à mi-parcours, mesure complète en cours),
140 camps avec Elo officiel et ≥ 8 coups utiles (70 Nico, 70 adversaires).

| Méthode | Écart abs. médian | Biais moyen | Estimés `>=2000` | Spearman estimation / officiel |
|---|---|---|---|---|
| Brute | 341 [n=140] | +223 [n=140] | 51/140 | 0,37 [n=140] |
| Calibrée | 423 [n=140] | −62 [n=140] | 44/140 | 0,33 [n=140] |

Agrégats chronologiques sur Nico (variante calibrée ; Elo officiel moyen → estimation) :
- fenêtres de 10 parties [n=7 fenêtres] : 1324 → 1090, 1423 → 1131, 1504 → 1822, 1617 → 1126,
  1619 → ≥2000, 1660 → ≥2000, 1679 → 1649. L'officiel monte régulièrement de 1324 à 1679 ;
  l'estimation saute de 1090 à ≥2000 sans suivre. Écart médian 318 [n=7].
- fenêtres de 20 parties : écart médian 272 [n=3 fenêtres] ;
- les 70 parties ensemble : 1547 officiel → 1386 calibrée, 1950 brute [n=1 agrégat].

Verdict : corrélation faible (Spearman ≈ 0,35 [n=140]). Par partie, l'erreur (340-420) dépasse
l'écart entre Nico et ses adversaires. En tendance sur 10 parties, les sauts (≈ 900 points)
dépassent de loin la progression réelle (≈ 350 points sur la période). **Maia-2 n'est pas un
estimateur de niveau exploitable ici**, ni par partie ni en tendance.

### 6.b Mesure complète (166 fiches)

251 camps : brute écart médian 313, biais +163, `>=2000` 94/251, Spearman 0,31 ; calibrée écart
médian 407, biais −104, `>=2000` 79/251, Spearman 0,21 [n=251, 1 run]. Maia abandonné (Nico).

## 7. Piste « précision → Elo » (Game Rating façon chess.com)

Précision Lichess des deux camps recalculée depuis `plies_json` (`_game_accuracy`), 135 fiches à
≥ 30 demi-coups et deux Elo :
- précision → Elo : Spearman 0,16 [n=270 camps] ; plage d'Elo étroite (1180-2055), adversaires
  appariés (|ΔElo| médian 32) : nos fiches ne peuvent pas calibrer la loi ;
- écart de précision → écart d'Elo : Spearman 0,46 [n=135], mais ΔElo trop petit pour servir ;
- précision de Nico : écart-type 10,1 pts d'une partie à l'autre [n=135].
- Cadence : 152 fiches sur 166 en `600` (10 min sans incrément, format chess.com).
Piste : calibrer précision → Elo une fois, hors ligne, sur la base publique Lichess (parties
annotées `%eval`, Elo 400-2800), table figée dans le repo. Échelle Lichess ≠ chess.com : à traiter.

### 7.b Calibration sur la base Lichess (janvier 2014)

Parties annotées `%eval`, ≥ 30 demi-coups ; précision par camp = `_game_accuracy` (formule du bilan),
% de gain Lichess depuis les cp. 56 480 camps (toutes cadences), 17 044 en base 8-15 min.

Précision médiane par tranche d'Elo (base 8-15 min) : 1200-1399 → 73,9 % ; 1400-1599 → 78,1 % ;
1600-1799 → 80,6 % ; 1800-1999 → 83,9 % ; 2000-2199 → 86,0 %. Écart interquartile **dans** une tranche :
≈ 17 points (ex. 1600-1799 : 73,1-87,1).
Inverse : précision 85-90 % → Elo médian 1685, P25-P75 1544-1803, P10-P90 1446-1904.

**Erreur médiane d'une estimation par partie : 128, identique à la constante « tout le monde à 1628 »
(128)** [17 044 camps, 10 min] ; 141 contre 148 toutes cadences [56 480 camps].

Verdict : sur une seule partie, la précision ne dit presque rien de l'Elo. +800 Elo ne déplacent la
précision médiane que de ≈ 12 points, alors qu'un même niveau s'étale sur ≈ 17 points (P25-P75).
Comme Maia, ça bute sur le nombre de décisions dans une partie (30-40). Le « Game Rating »
de chess.com affiche un nombre, mais il ne peut pas être plus précis (même limite de données).

## 8. Ce qui reste mesurable et honnête par partie

- **Précision rapportée à l'habitude** : « 87 % : ta 12e meilleure partie sur 135 », ou percentile parmi
  les joueurs de même Elo (table Lichess ci-dessus). Dit « au-dessus / en dessous de ton niveau
  habituel » sans prétendre à un Elo.
- Sur plusieurs parties : performance Elo (résultats + Elo adverses), Elo officiel.
