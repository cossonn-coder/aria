# Sprint 35 — tronçon 03 : run live (Nico)

Exécuté par Nico : PC Windows, Brave, même réseau local que la VM.
Coups à jouer : `docs/sprint35/run_live_coups.txt`.

## Préparation

1. `sudo systemctl restart aria.service`
2. `sudo journalctl -u aria -f -o cat | grep -E "board|explosive"`
3. Ouvrir `http://192.168.1.124:5002` dans Brave. Attendre ~15 s (chargement Maia).

## Scénarios et critères

| # | Action | Critère observable |
|---|---|---|
| 1 | Elo blancs 1600, noirs 1540 ; jouer les coups de la partie AaronDias16 jusqu'à la position avant 5.Nc3 (fichier, section 1) | une ligne d'état en ≤ 10 s ; log `board_analysis … pass=1 … duration=` ≤ 10 s |
| 2 | Rester sur cette position ~75 s | passes 2, 3, 4 au log ; la page finit sur « analyse terminée » ; un explosif (e3 vu au banc d'essai) apparaît en orange au moins à une passe [banc n=1] |
| 3 | Survoler la flèche orange | panneau des réponses humaines avec % et suites |
| 4 | Enchaîner 5 coups en ~2 s (section 2) | log : `superseded` pour les positions intermédiaires, passe 1 seulement sur la dernière |
| 5 | Interrupteur « Calque explosif » coupé puis remis | la flèche orange disparaît puis revient |
| 6 | Position à coup unique (section 3, 6.Nxg5 attendu), « Seul coup » actif puis coupé | flèche verte présente puis absente |
| 7 | Position décidée (section 4, blancs à 9 %) | « position décidée » (le Nd5 vu au banc d'essai sans fenêtre n'apparaît pas : attendu) |
| 8 | Envoyer `salut` au bot Telegram | réponse normale : le bot n'est pas gêné |

Échec d'un critère → noter le scénario, la ligne de log, ce que la page affichait.
