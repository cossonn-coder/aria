# Sprint 39 — tronçon 09 : run live « moi » + liste des coups (Nico)

Partie : `docs/sprint39/run_live_parties.txt` (partie 1).

## Préparation

1. `sudo systemctl restart aria.service`
2. `sudo journalctl -u aria -f -o cat | grep -E "board_|telegram_external|chess_analysis|chess_game_write"`
3. Ouvrir `http://192.168.1.124:5002`, Ctrl+F5.

## Scénarios et critères

| # | Action | Ce qu'on doit voir |
|---|--------|--------------------|
| 1 | Taper du texte dans la zone PGN, « Nouvelle partie » | zone PGN vide |
| 2 | Coller la partie 1, « Charger la partie » | sous la courbe, liste `1. e4 …` numérotée ; coup courant surligné |
| 3 | ▶ ◀, puis clic sur un coup de la liste | l'échiquier va à ce coup, surlignage suit |
| 4 | Au coup 10 des blancs, jouer autre chose que Qxc3, puis 2 coups | `10. Qxc3 (10. … … 11. …) 10… …` ; clic sur le 1er coup de la parenthèse → variante tronquée à ce coup |
| 5 | « Revenir à la partie » | parenthèse disparue |
| 6 | « Je joue » : blancs | champ Blancs = `Nico` |
| 7 | « Envoyer à ARIA » | analyse sur Telegram, Nico aux blancs ; journal `chess_analysis OK … nico=white source=header`, `chess_game_write OK hash=ebeb5dae122d4cef` |
| 8 | « Je joue » : noirs | Noirs = `Nico`, Blancs vidé |
| 9 | « Nouvelle partie », jouer 3 coups à la main | liste `1. e4 e5 2. …`, non cliquable |

Le scénario 7 réécrit la fiche `chess_game` de la partie 1 dans le palace prod (même hash
qu'aux runs 04 et 06).

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.
