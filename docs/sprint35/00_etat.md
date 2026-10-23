# Sprint 35 — état de conception

**Phase** : B figée (2026-10-23) — prêt pour `/sprint-auto sprint 35`.
**Branche** : `feat/sprint35-echiquier`.

## Objectif

Échiquier hébergé par ARIA (aucune connexion à chess.com) sur lequel Nico et un ami jouent
devant le même écran ; ARIA cherche en continu le coup explosif du camp au trait et le
montre en flèche orange, avec les réponses humaines probables (Maia) au survol.

## Décisions arrêtées

- Cible = #94, réorientée : d'abord calque chess.com, puis échiquier ARIA. Le calque en
  partie live chess.com « indétectable » a été refusé par Claude (outil de triche
  utilisable contre n'importe qui, contournement de l'anti-triche) ; Nico a choisi
  l'échiquier hébergé. #115 et #116 restent en dettes. (2026-10-23)
- Délai : ≤ 10 s par position, sinon trop long. Mesure : 4-7 s par position [n=6] avec
  Maia/Stockfish résidents ; chargement Maia 14 s une fois (audit §7). (2026-10-23)
- Jeu rapide prioritaire : un coup joué interrompt l'analyse. Moyen : proxy autour du
  moteur dont `analyse()` lève `Superseded` si une position plus récente est arrivée →
  `explosive.py` inchangé ; abandon ≤ un appel moteur ou la passe Maia. (2026-10-23)
- Recherche continue : tant qu'aucun coup n'est joué, passes ×1, ×2, ×4, ×8 (le proxy
  multiplie chaque `Limit(time=…)`), arrêt après ×8 (≈ 75 s cumulées) ; chaque passe
  remplace la précédente. La page interroge `GET /state` toutes les ~1 s. (2026-10-23)
- Q1 = serveur intégré à `aria.service` (thread lancé par `bot.py`, Maia partagé via le
  cache `difficulty._load`). Raison : Nico n'utilise jamais les deux en même temps. (2026-10-23)
- Q2 = même ordinateur, pas de multijoueur. (2026-10-23)
- Q3 = explosif cherché pour le camp au trait, les deux camps. (2026-10-23)
- Q4 = meilleur coup jamais montré, sauf « seul coup » (coup légal unique ou 2e coup à
  ≥ 20 pts de % de gain derrière) en flèche verte, avec son propre interrupteur. (2026-10-23)
- Q5 = un champ Elo par joueur ; Maia reçoit l'Elo de l'adversaire du trait. (2026-10-23)
- Q6 = fenêtre 35-75 % de gain reprise : hors fenêtre, état « position décidée ». (2026-10-23)
- Signalement explicite « aucun coup explosif — analyse terminée ». (2026-10-23)
- Défauts de conception : stdlib `http.server` ; port 5002 (`config.board_port`, libre) ;
  chessground 9.2.1 + chess.js 1.4.0 via jsdelivr `+esm` (HTTP 200 vérifié) ; Maia chargé
  à l'ouverture de la page, pas au démarrage du bot.

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_backend_analyse_live.md` — `chess_coach/live.py` + `interfaces/board_interface.py` + `bot.py` + `config.board_port` | ✅ (363 tests verts, non commité) |
| 02 | `02_page_echiquier.md` — `interfaces/board/index.html` (chessground, interrupteurs, Elo, états, survol) | ⏳ |
| 03 | `03_run_live.md` — run live (Nico, Brave/Windows), coups dans `run_live_coups.txt` | ⏳ |

## Dettes

- Traitée : #94, moitié « échiquier rejouable » réorientée en échiquier de jeu avec calque
  explosif (fermeture partielle à décider après run live). Calque chess.com : abandonné.
- Inchangées : #115, #116 (repères ci-dessous).
- À surveiller au run live : mémoire du service avec Maia (#102).

### Repères pré-audit (2026-10-23)

- #116 confirmé dormant : `intent_compression_engine.py:101` affecte une property sans
  setter (AttributeError reproduit) ; déclenché seulement à ≥ 10 intents actifs (prod : 4) ;
  second défaut : originaux non retirés du pool après fusion.
- #115 : le bloc enrichi ne porte des faits que pour les positions critiques ; 12.dxe6
  (run 33) n'en était pas une → l'hypothèse « plafond » est incomplète.

## §REPRISE

Tronçon 01 ✅ (2026-10-23) : `chess_coach/live.py` (proxy `EngineProxy` + `Superseded`,
`analyse_pass`, `FACTORS`), `interfaces/board_interface.py` (`BoardWorker`, routes
`GET /`, `POST /position`, `GET /state`, `start_board_server`), page provisoire
`interfaces/board/index.html`, `config.board_port`, appel dans `bot.py`. Stockfish ouvert
à la première position reçue (pas au démarrage du bot). Champ `pass` de `/state` = passe en
cours (dernière passe quand `running` est faux) ; `result` = dernière passe terminée.
Smoke VM : une passe ×1 réelle (Stockfish + Maia) 21,4 s [n=1, chargement Maia 14 s inclus].
Suite : tronçon 02 (page échiquier), puis remise du protocole `03_run_live.md` à Nico.
