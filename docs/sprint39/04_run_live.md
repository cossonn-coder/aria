# Sprint 39 — tronçon 04 : run live (Nico)

Exécuté par Nico. Parties à coller : `docs/sprint39/run_live_parties.txt`.

## Préparation

1. `sudo systemctl restart aria.service` (serveur, Telegram et page touchés).
2. `sudo journalctl -u aria -f -o cat | grep -E "board_|telegram_external|chess_game_write"`
3. Ouvrir `http://192.168.1.124:5002`, attendre ~15 s (Maia).

## Scénarios et critères

| # | Action | Ce qu'on doit voir |
|---|--------|--------------------|
| 1 | Échiquier vide, jouer à la main 1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 | courbe visible dès le 1er coup, un point par coup en ≈ 1 s ; journal `board_eval` |
| 2 | Après 3…Nf6 | zone ombrée sur 3…Nf6 ; sous l'échiquier « joué : Nf6 — meilleur : … (−Z pts) » et « mat en 1 pour les blancs » ; repère « #1 » en haut de la courbe |
| 3 | « Annuler le dernier coup » | la courbe raccourcit, la ligne parle de 3.Qh5 |
| 4 | Recharger la page (F5) | même position, même courbe |
| 5 | « Je joue » : blancs, « Exporter PGN » | fichier .pgn téléchargé ; coller le presse-papier dans un éditeur : `[White "staroflexeur"]`, `[Black "?"]`, Date, Elo, coups |
| 6 | « Nouvelle partie », coller la partie 1, « Charger la partie » | courbe complète, zones ombrées sur les grosses erreurs, « #1 » en bas près de la fin (39…Rd1#) |
| 7 | Naviguer (▶ ◀) | « joué : X — meilleur : Y (−Z pts) » suit le coup affiché |
| 8 | Au coup 10 des blancs, coup hors partie | courbe inchangée, « Revenir à la partie » ; export = ligne de l'échiquier (vérifier dans le presse-papier), puis « Revenir à la partie » |
| 9 | « Je joue » : blancs, « Envoyer à ARIA » | « envoyée à ARIA » sur la page ; sur Telegram : « écrit… », ⏳, puis l'analyse habituelle de la partie 1 (images + texte) ; journal `board_send`, `telegram_external source=board`, `chess_game_write OK hash=…` |
| 10 | Rechargement pendant une partie chargée | partie et curseur retrouvés |
| 11 | Retour libre | lisibilité de l'ombrage et des repères, utilité de « meilleur : Y » |

Le scénario 9 écrit une fiche `chess_game` dans le palace prod (partie réelle : la
fiche est créée ou remplacée si la partie 1 a déjà été envoyée). Ne pas envoyer la
mini-partie du scénario 1 (fiche parasite, cf. #98).

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.
