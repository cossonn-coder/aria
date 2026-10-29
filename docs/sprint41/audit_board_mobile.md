# Sprint 41 — audit : échiquier mobile ouvert depuis Telegram

Date : 2026-10-29. Code lu sur `main` @ `124948a` (post sprint 40).

## 1. Chaîne actuelle

| Maillon | Code | Constat |
|---|---|---|
| Commande | `interfaces/telegram_interface.py:250` `_cmd_board` | envoie `meta_commands.board_text()` en texte brut via `_deliver` |
| Texte | `interfaces/meta_commands.py:38` `board_text()` | renvoie `config.board_url` |
| Config | `config.py:85-87,105` | `board_port = 5002`, `board_url = "http://192.168.1.124:5002"` (surchargeable `BOARD_URL`) |
| Serveur | `interfaces/board_interface.py` `make_server` / `start_board_server` | `ThreadingHTTPServer` stdlib sur `0.0.0.0:5002`, **HTTP seul**, aucune authentification |
| Page | `interfaces/board/index.html` (893 lignes, un seul fichier) | servie sur `GET /` ; chessground 9.2.1 + chess.js 1.4.0 depuis jsDelivr |
| Lancement | `bot.py:37` `start_board_server(telegram.submit_text)` | threads daemon dans le process `aria.service` |

Routes : `GET /`, `GET /state` (sondé toutes les 1 s), `POST /position`, `/game`, `/eval`,
`/accuracy`, `/send`. **`/send` injecte un texte comme un message de Nico**
(`TelegramInterface.submit_text` → kernel, chat `ALLOWED_USER_ID`). Exposer le serveur hors
du réseau local sans authentification = n'importe qui peut parler à ARIA en se faisant passer
pour Nico, et faire tourner Stockfish/Maia à volonté.

## 2. Réseau de la VM

- `ens18` 192.168.1.124/24 (LAN maison). Le lien `/board` ne marche donc que sur le wifi maison.
- `tailscale` installé (`/usr/bin/tailscale`, interface `tailscale0` présente) mais **déconnecté**
  (`tailscale status` → « Logged out »), aucun `serve` / `funnel` configuré.
- Pas de `cloudflared`, `caddy`, `nginx`, `ngrok`.

## 3. Contraintes Telegram (Mini App / Web App)

- Un bouton `web_app` (inline keyboard `InlineKeyboardButton(web_app=WebAppInfo(url))`, ou
  bouton de menu `MenuButtonWebApp`) ouvre la page **dans Telegram** (webview plein écran).
- **L'URL doit être en HTTPS.** `http://192.168.1.124:5002` est refusé par l'API.
- La page est chargée par le téléphone lui-même : une URL HTTPS joignable seulement depuis le
  tailnet (Tailscale `serve`, certificat `*.ts.net` valide) suffit, si le téléphone est sur
  le tailnet. Une URL publique (Tailscale `funnel`, tunnel Cloudflare) impose en plus de
  valider `initData` (signature HMAC du bot) côté serveur sur chaque route, à cause de `/send`.
- Alternative sans Mini App : le lien texte actuel s'ouvre dans le navigateur interne de
  Telegram ; HTTP accepté, mais LAN seulement.
- Bonus HTTPS : `navigator.clipboard` (export PGN, `index.html` ~l. 862) n'existe qu'en
  contexte sécurisé ; il devient disponible.

## 4. Page actuelle vs écran de téléphone

Conçue pour PC (`docs/sprint35/02_page_echiquier.md:57` : « pas d'exigence mobile »).

| Élément | Code (`index.html`) | Problème sur téléphone (≈ 360-430 px de large) |
|---|---|---|
| Mise en page | `main { display: flex }` : 3 blocs côte à côte (échiquier+courbe, contrôles, 3 colonnes) | ≈ 560 + 260 + 3 colonnes : défilement horizontal |
| Échiquier | `#board { width: 560px; height: 560px }` | plus large que l'écran |
| Courbe | `<svg width="560" height="200">`, `GRAPH_W = 560` en dur dans le clic | idem ; le clic (`event.clientX` / `GRAPH_W`) suppose 560 px réels |
| Liste de coups, statut | `width: 560px` / `532px` | idem |
| Marges | `body { margin: 24px }` | perte de place |
| Viewport | **aucune** balise `<meta name="viewport">` | le mobile rend en largeur de bureau (980 px) dézoomée |
| Navigation libre ←/→ | clavier (`keydown`) et molette (`wheel`) seulement, `stepBack` / `stepForward` | **aucun moyen tactile** d'avancer/reculer hors partie chargée (⏮◀▶⏭ désactivés sans `game`) |
| Mini échiquier de survol | `mouseenter` / `mouseleave` sur chaque coup | pas de survol au doigt ; un tap déclenche `mouseenter` émulé, mini resté affiché |
| Panneau « réponses humaines » | survol de `#status` / sortie de `#analysis` | idem, ouvrable au tap, difficile à refermer |
| Clic sur les coups (partie chargée) | `click` → `goTo` | marche au tap |
| Coups sur l'échiquier | chessground (gère le tactile) | OK |
| Colonnes sauvegardées | `max-height: calc(100vh - 48px)` | OK une fois empilées |

## 5. Ce qui ne bouge pas

- Logique d'analyse (worker, `/state`, passes) : indépendante de l'écran.
- `localStorage` (`aria-board`) : propre à chaque navigateur ; la webview Telegram a son
  propre stockage, donc pas de partage d'état PC ↔ téléphone (mais le serveur, lui, est
  unique : un seul `BoardWorker`, la dernière position soumise gagne — PC et téléphone ouverts
  en même temps se « volent » l'analyse live).

## 6. Règles d'architecture

Sujet hors mémoire, hors kernel : `/board` reste une métacommande (hors kernel, hors
historique). `/send` passe déjà par `submit_text` → kernel. Aucune règle 1-6 touchée.
Palace prod non touché → calibrage faible.
