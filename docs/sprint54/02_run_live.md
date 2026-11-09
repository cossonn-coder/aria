# Sprint 54 — tronçon 02 : run live (Nico)

Après le tronçon 01 commité et `sudo systemctl restart aria.service`.
Journal : `sudo journalctl -u aria -f -o cat`.

1. Sur chess.com, télécharger le PGN de la partie du 2026-11-09 contre Ashiki321x321
   (lien `https://www.chess.com/analysis/game/live/186832335594/analysis`) **avec la pendule**
   (`%clk`). Sans pendule, elle est refusée comme doublon ; avec, elle est réanalysée
   (journal : `chess_router reanalyze hash=… reason=clock`).
2. Le coller dans Telegram.

Succès :
- Position 1 (9...Qd7) : le « Pourquoi : » dit que 9.Ba3 chassait la dame, que Qd7 voulait
  déclouer Nc6, et que la dame s'est mise derrière Nc6 face à Bb5 (Nc6 cloué), d'où 10.Ne5 ;
  le temps passé sur 9...Qd7 peut être mentionné.
- Aucun fait inventé dans cette entrée ; journal : `chess_router OK`, aucune `ERROR`.
- Erreur après le coup 10 (même partie ou une autre) : la ligne de données contient
  « Maia : coup choisi par N % » et une « suite probable » ; le « Pourquoi : » s'appuie sur un
  indice présent (intention, Maia, temps) ou dit que l'idée n'est pas claire, sans en inventer.
  Journal : pas de `maia_human_lines FAILED`.
- Bonus : sur une partie neuve avec une erreur, l'entrée suit la même forme en 3 temps.
