# Sprint 41 — tronçon 03 : run live de l'échiquier mobile (Nico)

## A. Préalable Tailscale (une fois)

Une commande par ligne :

1. VM : `sudo tailscale up` → ouvrir l'adresse affichée, valider avec ton compte.
2. Téléphone : installer l'app Tailscale, se connecter au même compte, l'activer.
3. Console admin Tailscale (login.tailscale.com → DNS) : activer **MagicDNS** et **HTTPS Certificates**.
4. VM : `sudo tailscale serve --bg 5002` → note l'URL `https://<vm>.<tailnet>.ts.net` affichée.
5. VM : ajouter `BOARD_URL=https://<vm>.<tailnet>.ts.net` dans `.env` (sans `/` final).
6. `sudo systemctl restart aria.service`
7. `sudo journalctl -u aria -f -o cat | grep -E "meta_|board_|Traceback"`

## B. Scénario

PGN à coller : `docs/sprint41/run_live_pgn.txt`.

| # | Action | Ce qu'on doit voir |
|---|---|---|
| 1 | Téléphone **en 4G (wifi coupé)**, Tailscale actif : `/board` | l'URL https + bouton « ♟ Ouvrir l'échiquier » |
| 2 | Toucher le bouton | l'échiquier s'ouvre dans Telegram, plein écran, sans défilement horizontal |
| 3 | Jouer 1.e4 e5 2.Nf3 en glissant les pièces, dont un glissé vers le bas | la Mini App ne se ferme pas ; journal `board_analysis …` |
| 4 | Attendre l'analyse | flèches colorées éventuelles, statut, barre d'évaluation à gauche qui bouge |
| 5 | ◀ ◀ puis ▶, puis ⏮ et ⏭ | navigation correcte dans la ligne |
| 6 | Onglets Coups / Courbe / 🟠 / cyan / rose | un panneau à la fois, contenu lisible |
| 7 | ☰ → coller le PGN → Charger | partie chargée, courbe calculée (onglet Courbe), tap sur la courbe = va à la position |
| 8 | Tap sur un coup d'une colonne (si non vide) | mini échiquier ; tap ailleurs le ferme |
| 9 | ☰ → Retourner | échiquier et barre d'évaluation retournés |
| 10 | ☰ → Envoyer à ARIA | « envoyée à ARIA » ; analyse de la partie dans le chat Telegram |
| 11 | ☰ → Exporter PGN | observer : téléchargement et/ou « copié » (dette D-export, juste noter) |
| 12 | PC : ouvrir `http://192.168.1.124:5002` | page identique à avant le sprint |

Échec d'un critère → capture d'écran + ce qui s'est passé.
