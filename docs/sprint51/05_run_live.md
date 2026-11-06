# Sprint 51, tronçon 05 — run live (Nico)

## Préparation
`sudo systemctl restart aria.service`

⚠️ Palace prod : le message 1 réécrit **une** fiche existante (partie dusha28), même id, date
d'origine conservée.

## À envoyer
Fichier copiable : `docs/sprint51/05_run_live.txt` (PGN de la partie dusha28 avec `%clk`,
obtenu par l'API publique chess.com, identique aux coups de la fiche).
1. Message 1 : le PGN.
2. Message 2, après la réponse : le même PGN.

## À vérifier sur Telegram (message 1)
1. Pas de « déjà envoyée » : la partie est réanalysée.
2. Sous le déroulé, la ligne Conversion : ≈ 47 coups à 80 % ou plus (coups 9 à 55), idées
   **activer le roi (Kd3…, joué au 37)** et **pousser le pion passé (b5…, joué au 52)** ;
   ni Nd5 ni Nc2.
3. Ligne Temps : toi ≈ 10,9 s par coup, adversaire ≈ 7,4 s ; dès le coup 9, pendules
   ≈ 9:43 contre 9:31, puis ≈ 12,4 s contre 8,1 s [calcul sur le PGN, à ±0,1 près] ;
   « Perdu au temps. »
4. Trois coups longs analysés : 14.Rxb4 (54 s), 22.Re1 (43 s), 37.Kd3 (35 s), chacun avec
   miniature, verdict du code (attendu : « un coup simple suffisait » pour les trois, écart au
   2e < 5 [fiche]) et une entrée « Pour jouer vite : » du LLM. Si l'un d'eux est déjà une
   position critique, une ligne « ⏱️ réfléchi » dans sa légende à la place.
5. Miniature Conversion (b5, coup 43) après les coups longs, avant la courbe.
6. Le bilan explique les concepts « activer le roi » et « pousser le pion passé » et ne
   parle du temps qu'avec les chiffres de la ligne Temps.
7. Pastilles : 🔵 sur un coup joué meilleur, ⚪ correct, 🟢 seulement sur les coups du moteur ;
   légende avec les comptes « toi / adversaire » ; courbe : points bleus (meilleur) et blancs
   (correct).

## Message 2
8. « Cette partie contre dusha28 a déjà été envoyée le … » (la fiche a maintenant des horloges).

## À vérifier dans les journaux
`sudo journalctl -u aria --since today -o cat | grep -E "chess_router reanalyze|chess_game_write|chess_router OK|duplicate"`
- `chess_router reanalyze hash=… reason=clock` au message 1, `chess_router duplicate` au message 2.

## Critère de succès
Points 1 à 8 observés. La progression garde la partie à sa place (même numéro de partie qu'à
l'envoi du matin, 137, aux variations près des parties envoyées depuis).
