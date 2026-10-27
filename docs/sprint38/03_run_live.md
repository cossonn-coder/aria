# Sprint 38 — tronçon 03 : run live (Nico)

Exécuté par Nico sur la page de l'échiquier. Parties à coller :
`docs/sprint38/run_live_parties.txt` (un bloc par partie).

## Préparation

1. `sudo systemctl restart aria.service` (le tronçon 01 touche le serveur).
2. `sudo journalctl -u aria -f -o cat | grep board_`
3. Ouvrir `http://192.168.1.124:5002`, attendre ~15 s (chargement Maia).

## Scénarios et critères

| # | Action | Critère observable |
|---|---|---|
| 1 | Coller la partie 1, « Charger la partie » | échiquier au début, Elo 1307 / 1352 pré-remplis, colonnes vides ; « courbe en calcul… » puis courbe en ≈ 15 s ; journal `board_game plies=78 duration=…` (noter la durée) |
| 2 | Courbe partie 1 | une valeur par position, ligne des 50 % visible, dernier point en bas (mat des noirs 39…Rd1#) ; trait vertical au début |
| 3 | ▶ / ◀ et flèches du clavier, ⏭ puis ⏮ | la position suit, le trait vertical aussi, les flèches d'analyse live apparaissent sur chaque position où l'on s'arrête |
| 4 | Clic au milieu de la courbe | l'échiquier va à ce coup |
| 5 | Parcourir lentement les coups 5 à 12 | blocs dans les colonnes avec « joué : X » (ex. au coup 7 des blancs : « joué : Bxf7+ ») |
| 6 | Au coup 10 des blancs, jouer un autre coup que 10.Qxc3 à la main, puis une réponse noire | bouton « Revenir à la partie » visible ; trait vertical resté sur le coup 10 ; blocs de variante sans « joué : » |
| 7 | « Revenir à la partie » puis ▶ | retour à la position du coup 10, puis 10.Qxc3 joué : la suite de la partie est intacte |
| 8 | En partie, jouer à la main le coup suivant de la partie | on avance dans la partie (pas de bouton « Revenir à la partie ») |
| 9 | Coller la partie 2 (coups seuls) | chargement et courbe OK, Elo inchangés, colonnes vidées |
| 10 | Coller le texte illisible | message d'erreur, la partie 2 reste chargée |
| 11 | « Nouvelle partie » | courbe et contrôles de navigation masqués ou inactifs, échiquier libre comme avant |
| 12 | Retour libre | lisibilité de la courbe sur fond sombre, confort de navigation |

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.

## Mini-run du correctif « joué : X » (2026-10-27)

| # | Action | Ce qu'on doit voir |
|---|--------|--------------------|
| 1 | Charger la partie 1, avancer au coup 7 des blancs | sous l'échiquier « joué : Bxf7+ », fou c4 cerclé de blanc |
| 2 | ▶ / ◀ sur quelques coups | le texte et le cercle suivent à chaque position |
| 3 | Jouer un coup hors partie | texte vide, plus de cercle ; « Revenir à la partie » les rétablit |
| 4 | ⏭ (fin de partie), puis « Nouvelle partie » | texte vide, pas de cercle |
