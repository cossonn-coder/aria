# Sprint 29 — Tronçon 08 : précision Lichess, meilleur et pire coup de la partie

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_retours_run_live.md` §3.

## Objectif

1. Précision de la partie = algorithme Lichess complet (au lieu de la moyenne arithmétique).
2. Afficher le **pire coup** et le **meilleur coup** de Nico de la partie.

## 1. Précision (`chess_coach/summary.py`)

Algorithme Lichess (`lila/modules/analyse/src/main/AccuracyPercent.scala`) :
- par coup : `103.1668100711649 * exp(-0.04354415386753951 * drop) - 3.166924740191411 + 1`,
  borné [0, 100] ; 100 si le % de gain du joueur ne baisse pas. `drop` = perte du coup
  (garder `_effective_loss` : meilleur coup → 0).
- série des % de gain point de vue blancs sur toutes les positions (N+1) ;
  `window = clamp((len(série) − 1) // 10, 2, 8)` ; fenêtres glissantes de taille window
  (Lichess complète le début en répétant la première fenêtre pour avoir une fenêtre
  par coup) ; poids d'un coup = écart-type de sa fenêtre borné [0,5 ; 12].
- précision d'une couleur = (moyenne pondérée + moyenne harmonique) / 2 sur ses coups.
  Moyenne harmonique : planchers à 1 % par coup pour éviter la division par 0 (noter
  l'écart à Lichess en commentaire).
- Nouvelle clé `accuracy` (float, 1 décimale, None si aucun coup de Nico). Les clés
  `accuracy_{phase}` restent inchangées (compatibilité des fiches) mais ne sont plus
  affichées.

## 2. Pire coup
Coup de Nico à la plus forte perte ; clés `worst_move` (SAN avec numéro, ex. « 39.Bb2 »),
`worst_win_before`, `worst_win_after`. Aucun si perte max < 10.

## 3. Meilleur coup (« coup qui pose problème »)
Décision Nico : le coup qui provoque des fautes et donne le plus de potentiel de
conversion ; Maia ET Stockfish, jamais Maia seule. Nouvelle fonction dans
`chess_coach/explosive.py` (réutilise `reply_distribution`, `_human_replies`), appelée
dans `analysis.analyze` après `find_explosive`, Maia absent → None (pas de WARNING en plus).

Pour chaque coup de Nico : perte ≤ 5, coup précédent adverse **pas** une erreur
(perte < 15), position après le coup non terminée.
1. Réponses adverses = top Maia (`reply_distribution`, Elo adverse) ∪ top 3 Stockfish
   (MultiPV 3, `_DEEP_TIME`). Stockfish évalue chacune (% de gain de Nico).
2. Faute = réponse qui donne à Nico ≥ 5 pts de plus que la meilleure défense Stockfish.
3. Score = Σ p_maia(réponse) × (win Nico après réponse − win Nico après meilleure défense),
   p brutes Maia (réponses Stockfish hors top Maia : p = 0).
4. Maia hésitante (p max < 0,15) : score = part des 5 meilleures réponses Stockfish
   (MultiPV 5) qui sont des fautes × écart moyen de ces fautes.
5. Bonus ×1,5 si l'adversaire a effectivement commis une faute (perte ≥ 10) au coup suivant.
Résultat : SAN du coup, meilleure défense (SAN), sa probabilité Maia, coup réellement
joué par l'adversaire, score. Clés de résumé `best_move`, `best_defense`,
`best_defense_p`, `best_reply_played`.
Une seule passe Maia batchée sur toutes les positions (comme `_search_position`).
Log `chess_best_move OK move=… score=… duration=…`.

## 4. Affichage (`execution/routers/chess_router.py`)
- Ligne **déterministe** ajoutée par le router juste avant le bloc Progression (pas par
  le LLM) : « 🎯 Précision 85 % · meilleur coup 24.Qa4 (défense Rhb8 : 12 % de chances,
  joué …) · pire coup 39.Bb2 (88 % → 2 %) » ; parties absentes omises.
- `_level_line` : remplacer la précision par phase par `précision Nico : 85 %`.

## Tests
- `summary` : précision sur une liste de plies synthétique (une gaffe fait baisser nettement
  la valeur par rapport à la moyenne arithmétique) ; pire coup.
- Meilleur coup : test de la fonction de score avec réponses/probabilités injectées
  (pas de moteur réel).

## Hors-scope
- Pas de recalcul des fiches existantes. Pas de changement du modèle joueur.

## Critère de fin
`pytest tests/ -q` vert ; précision + meilleur/pire coup mesurés sur les 4 parties de `run_live_retours_parties.txt`
et notés dans `00_etat.md`.
