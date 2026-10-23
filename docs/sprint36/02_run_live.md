# Sprint 36 — tronçon 02 : run live (Nico)

Exécuté par Nico : PC Windows, Brave, même réseau local que la VM.
Coups à jouer : `docs/sprint36/run_live_coups.txt`.

## Préparation

1. `sudo systemctl restart aria.service`
2. `sudo journalctl -u aria -f -o cat | grep -E "board|explosive"`
3. Ouvrir `http://192.168.1.124:5002`, Elo 1500 / 1500, attendre ~15 s (chargement Maia).

## Scénarios et critères

| # | Action | Critère observable |
|---|---|---|
| 1 | Section 1 (Göring, blancs au trait) | flèche orange sur c3 (ou Fc4) à au moins une passe ; passe ×1 ≤ 10 s au log |
| 2 | Section 2 (suite) | flèche orange sur Fxf7+ (c'est aussi le meilleur coup) |
| 3 | Section 3 (Colle, blancs au trait) | flèche orange sur Fxh7+ |
| 4 | Section 4 (Italienne calme) | aucune flèche orange à la passe 1 ; une flèche aux passes suivantes est à noter, pas un échec |
| 5 | Survoler une flèche orange (scénario 2 ou 3) | panneau des réponses humaines (Rxf7 / Rxh7 en tête) |
| 6 | Envoyer le PGN de la section 5 au bot Telegram | analyse rendue normalement, aucun traceback au journal |
| 7 | Retour libre de Nico en jouant une partie | fréquence des flèches : « assez », « trop » ou « pas assez » |

Les mesures du banc d'essai sont [n=1, non déterministes] : un scénario 1 à 3 raté à la
passe 1 puis réussi à une passe suivante compte comme réussi. Échec d'un critère → noter
le scénario, la ligne de log et ce que la page affichait.
