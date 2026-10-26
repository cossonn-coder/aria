# Sprint 37 — tronçon 03 : run live (Nico)

Exécuté par Nico sur la page de l'échiquier (même protocole que le sprint 36).
Suites de coups à jouer : `docs/sprint37/run_live_coups.txt` (relevées au prototype sur les
parties des runs live ; non-déterminisme Stockfish/Maia, #108 : une flèche absente à une
passe puis présente à une suivante compte comme présente).

## Préparation

1. `sudo systemctl restart aria.service` (le tronçon 01 touche le backend).
2. `sudo journalctl -u aria -f -o cat | grep board_analysis`
3. Ouvrir `http://192.168.1.124:5002`, Elo 1300 / 1300, attendre ~15 s (chargement Maia).

## Scénarios et critères

| # | Action | Critère observable |
|---|---|---|
| 1 | Ouvrir la page | mode sombre : fond et cases sombres, pièces et coordonnées lisibles |
| 2 | Sections 1, 2 et 5 (pièges) | flèche cyan sur le coup indiqué à au moins une passe ; bloc dans la colonne « Pièges » avec la réponse piégeante et sa probabilité ; mini échiquier au survol |
| 3 | Section 4 (position très perdante) | flèche rose (même si c'est le meilleur coup) ; bloc dans la colonne « Stratégie » avec le pronostic humain |
| 3b | Toute la partie, « Stratégie » décochée | flèche bleue seulement quand aucune autre flèche n'est dessinée, jamais avant le coup 10, au plus 3 par camp, jamais deux coups de suite du même camp |
| 4 | Section 3 (piège = stratégie) et toute position avec orange | une seule flèche par coup selon la priorité vert > orange > cyan > rose, bleu seulement si aucune autre ; le coup commun figure dans chaque colonne concernée |
| 5 | Décocher puis recocher « Piège » et « Stratégie » | la flèche correspondante disparaît / revient |
| 6 | Journal | durée des passes `pass=1` à noter (comparaison #122 : ≈ 4,2 s avant [n=6]) |
| 7 | Retour libre en jouant une partie | rose « utile / bruit », cyan « assez / trop / pas assez » |

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.
