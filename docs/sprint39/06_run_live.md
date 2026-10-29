# Sprint 39 — tronçon 06 : run live des retours (Nico)

Exécuté par Nico. Partie à coller : `docs/sprint39/run_live_parties.txt` (partie 1).

## Préparation

1. `sudo systemctl restart aria.service` (page touchée).
2. `sudo journalctl -u aria -f -o cat | grep -E "board_|telegram_external|chess_game_write"`
3. Ouvrir `http://192.168.1.124:5002`, recharger la page (Ctrl+F5), attendre ~15 s.

## Scénarios et critères

| # | Action | Ce qu'on doit voir |
|---|--------|--------------------|
| 1 | « Nouvelle partie », coller la partie 1, « Charger la partie » | courbe de 200 px, zones ombrées rouges avec pointillé au niveau du meilleur coup, « #1 » sur pastille en bas près de la fin ; champs Blancs = staroflexeur, Noirs = Falestinhurra |
| 2 | Naviguer (▶ ◀), « Meilleur coup » décoché | « joué : 7. Bxf7+ (−Z pts) » (numéro, sans nom du meilleur coup) ; « 7… Kxf7 » pour un coup noir |
| 3 | Cocher « Meilleur coup » | la ligne devient « joué : 7. Bxf7+ — meilleur : Y (−Z pts) » sans changer de position |
| 4 | Au coup 10 des blancs, jouer un autre coup que Qxc3, puis 2-3 coups | courbe blanche de la partie intacte ; segment cyan partant du curseur, un point par coup en ≈ 1 s ; ligne « joué » = dernier coup de la variante ; journal `board_eval` |
| 5 | « Revenir à la partie » | segment cyan disparu, ligne « joué » sur le coup de la partie |
| 6 | Modifier Noirs en « Adversaire Test », « Exporter PGN » | fichier `staroflexeur-Adversaire_Test-AAAA.MM.JJ.pgn` ; dans le presse-papier `[Black "Adversaire Test"]` |
| 7 | Recharger la page (F5) | noms modifiés retrouvés |
| 8 | Remettre Noirs = Falestinhurra, « Je joue » : blancs, « Envoyer à ARIA » | analyse habituelle sur Telegram (Nico aux blancs) ; journal `board_send`, `chess_game_write OK hash=ebeb5dae122d4cef` (même fiche que le run 04, remplacée) |
| 9 | « Je joue » : noirs | Noirs = staroflexeur, Blancs vidé (il valait le pseudo) |
| 10 | Retour libre | lisibilité de la courbe, de la variante et des repères |

Le scénario 8 réécrit la fiche `chess_game` de la partie 1 dans le palace prod (même
hash que le run 04). Ne pas envoyer la partie avec « Adversaire Test ».

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.
