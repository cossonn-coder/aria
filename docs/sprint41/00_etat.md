# Sprint 41 — état : échiquier mobile ouvert depuis Telegram

**Phase courante** : **CLOS** (run live OK par Nico 2026-10-30, tag `sprint-41`).
**Branche** : `feat/sprint41-echiquier-mobile` (depuis `main` @ `124948a`, tag `sprint-40`).
**Audit** : `docs/sprint41/audit_board_mobile.md`.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_page_mobile.md` | `index.html` : disposition mobile façon lichess (≤ 700 px), barre d'éval, onglets, barre du bas, menu ☰, tap au lieu du survol, init Mini App Telegram ; PC inchangé | ✅ |
| 02 | `02_bouton_board.md` | `/board` : bouton `web_app` si `board_url` en https, sinon lien texte actuel | ✅ |
| 03 | `03_run_live.md` | run live Nico : préalable Tailscale + scénario téléphone en 4G (PGN : `run_live_pgn.txt`) | ✅ (OK Nico 2026-10-30) |

## Décisions arrêtées

- D1 : cible = version mobile de la page d'échiquier, ouverte depuis Telegram (choix de Nico, sujet neuf hors tableau des dettes).
- D2 : même `index.html`, rendu responsive (pas de page séparée) — une seule page à maintenir.
- D3 : périmètre = toutes les fonctions actuelles, adaptées au doigt.
- D4 : ouverture = Mini App Telegram (bouton `web_app` sur `/board`) servie en HTTPS par `tailscale serve` (tailnet seul → pas d'auth `initData`). Prérequis Nico avant run live : `tailscale up` VM + téléphone, MagicDNS + HTTPS activés, `tailscale serve --bg 5002`, `BOARD_URL=https://…ts.net` dans `.env`.
- D5 : bouton Mini App seulement si `board_url` est en https ; sinon `/board` garde le lien texte (l'API refuse un `web_app` en http).
- D6 : référence visuelle = échiquier d'analyse mobile de lichess, avec nos fonctions.
- D7 : disposition lichess sur téléphone seulement (≤ 700 px) ; PC strictement inchangé.
- D8 : sous l'échiquier, onglets Coups / Courbe / 🟠 / cyan / rose, un panneau à la fois ; barre du bas ☰ ⏮ ◀ ▶ ⏭ ; ☰ = menu des contrôles actuels.
- D9 : barre d'évaluation verticale à gauche de l'échiquier (mobile), nourrie par `evals` (/eval, /game), aucun calcul serveur en plus.
- Pas de navigateur headless sur la VM (ni chromium ni playwright) : rendu validé au run live seulement.
- Calibrage faible : palace prod non touché, aucune règle d'architecture 1-6 concernée.

## Dettes

Ouvertes par le sprint (à reporter au kickoff 42) :
- #135 : un seul `BoardWorker` côté serveur — PC et téléphone ouverts en même temps se volent l'analyse live (la dernière position soumise gagne).
- #136 : « Exporter PGN » (téléchargement `blob:`) peut ne pas marcher dans la webview Telegram ; presse-papier disponible en HTTPS. Run live : « tout bon » global de Nico, export non détaillé → à confirmer.

## Correctifs du run live (commit `27a8fb1`)

- Fenêtre qui « cherche à se recaler » (page un peu trop large / haute) : sur téléphone,
  `overflow-x: hidden` + `overscroll-behavior: none` sur `html, body`, mots longs coupés.
- Ligne de précision qui clignotait (effacée à chaque nouvelle évaluation le temps de
  `POST /accuracy`) et faisait sauter les onglets : dernière précision gardée en attendant
  (`lastAccuracy`). Touche aussi le PC (même défaut, antérieur au sprint) — écart assumé à D7.
- Colonnes 🟠 / cyan / rose (arbitrage Nico) : demi-coup décroissant sur PC et téléphone ;
  sur téléphone, seul le bloc de la position affichée est visible (classe `other` masquée).
- Préalable Tailscale fait : `https://vdebiania.tail25c240.ts.net` (`tailscale serve --bg 5002`),
  `BOARD_URL` posé dans `.env`.

Fermées : aucune.

## §REPRISE

Sprint clos : tronçons 01-02 + correctifs run live, 398 tests verts, run live OK par Nico.
Suite : `docs/sprint42/context_kickoff_sprint_42.md`, `/conception sprint 42`.
