# Tronçon 05 — run live (Nico)

Messages à copier : `docs/sprint49/run_live_messages.txt`.

Préalable : `sudo systemctl restart aria.service`. Journal : `sudo journalctl -u aria -f -o cat | grep -E "chess_|board_analysis"`.

| # | Action | Critère observable |
|---|---|---|
| 1 | Envoi 1 (partie déjà enregistrée) | Un seul message « déjà envoyée », en quelques secondes, sans image. Journal : `chess_router duplicate`, pas de `chess_analysis OK`. |
| 2 | Envoi 2 (partie neuve, ≥ 4 erreurs) | Journal : `chess_explosive skipped` ; `chess_analysis OK` nettement plus court qu'avant (environ 18 s attendues [calcul]). |
| 3 | Sur les miniatures de l'envoi 2 | Flèches 1, 2, 3 lisibles. Légende d'une erreur : `62 % → 41 % (−21 pts)`, ou équivalent. |
| 4 | Envoi 3 (partie neuve, peu d'erreurs) | S'il y a une miniature `d` : deux variantes en légende, flèches lisibles avec l'orange. S'il y a un seul coup `c` : écart au 2e meilleur coup. |
| 5 | Envoi 4 (même PGN que le 3) | « déjà envoyée ». `/parties` ne montre la partie qu'une fois. |
| 6 | `/board`, charger le PGN de l'envoi 2, deux fois | Courbe et meilleurs coups identiques aux deux chargements (stabilité d'`analyze_game`). |
| 7 | `/board`, Échiquier A, case cochée | Bleu à chaque coup dès le 1er, en moins d'une seconde environ, y compris à côté d'autres flèches. |
| 8 | Case décochée | Plus de bleu. Autres flèches inchangées. |
| 9 | Échiquier B | Sur un seul coup, vert et pas de bleu en plus. |
| 10 | ← puis → sur une position déjà analysée | Mêmes flèches aussitôt, pas de nouvelle ligne `board_analysis pass=1` pour cette position. |

À consigner : durées `chess_analysis OK`, flèche qui change entre deux passes (attendu, #125 partielle), toute erreur au journal.

Succès : les 10 lignes conformes, OK de Nico. Le texte LLM peut varier, c'est hors périmètre.
