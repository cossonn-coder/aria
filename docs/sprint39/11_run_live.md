# Sprint 39 — tronçon 11 : run live de la précision (Nico)

Partie : `docs/sprint39/run_live_parties.txt` (partie 1). Peut être fait avec le run 09.

## Préparation

1. `sudo systemctl restart aria.service`
2. `sudo journalctl -u aria -f -o cat | grep -E "board_|Traceback"`
3. Ouvrir `http://192.168.1.124:5002`, Ctrl+F5.

## Scénarios et critères

| # | Action | Ce qu'on doit voir |
|---|--------|--------------------|
| 1 | Charger la partie 1, aller au coup 1 | `joué : 1. e4 … — précision N %` ; `Précision : blancs N % · noirs —` |
| 2 | ▶ quelques coups, dont une perte (ombrage rouge) | précision du coup < 100 sur la perte ; totaux qui bougent à chaque coup |
| 3 | Aller en fin de partie | totaux = précision de toute la partie ; ordre de grandeur cohérent avec le bilan Telegram (même formule) pour le camp de Nico |
| 4 | Jouer une variante de 2 coups | précision du dernier coup de la variante ; totaux sur partie jusqu'au curseur + variante (après les `/eval`) |
| 5 | « Nouvelle partie », jouer 4 coups | précision de chaque coup puis totaux, après les `/eval` |

Échec d'un critère → noter le scénario, la ligne de log et ce que la page affichait.
