# Sprint 26 — état de conception

**Phase** : B figée (2026-10-19) — prêt pour `/sprint-auto sprint 26`
**Cible** : coach d'échecs (PGN → Stockfish → positions critiques illustrées + fiche par partie)
**Branche** : `feat/sprint26-coach-echecs`
**Audit** : `docs/sprint26/audit_coach_echecs.md`
**Palace prod touché** : OUI (tronçon 03, nouveau type de document `chess_game`) →
exception au calibrage faible sur ce tronçon.

## Décisions arrêtées

- 2026-10-19 — Cible = coach d'échecs (choix Nico, hors tableau de dettes).
  Pseudo Chess.com de Nico : `staroflexeur`.
- Q1 — Moteur = Stockfish 17.1 local, binaire `/usr/games/stockfish` (installé par
  Nico ; hors PATH systemd → chemin absolu en config). Lib Python `chess` (PyPI).
- Q2 — v1 = PGN seul. Cible à terme (dette #79) : photo d'échiquier physique ET
  capture d'écran d'échiquier virtuel → position.
- Q3 — Contrat router étendu : `{"text": str, "images": [{"path", "caption"}]}`
  (amende la règle inviolable 4). Telegram : photos d'abord (légende courte), puis texte.
- Affichage — échiquier orienté côté Nico ; **une seule flèche : le meilleur coup** ;
  notation française (C, F, T, D, R) dans la réponse et les légendes.
- Rendu Pillow + police DejaVu Sans (glyphes ♔…♟), pas de cairosvg (libcairo2 absent).
- Détection PGN = en-tête `[White "` ou `[Black "` + texte de coups `1.` ;
  passe AVANT la règle URL (en-tête `[Link "https://…"]` des exports Chess.com).
  Une suite de coups sans en-tête dans une question reste au LLM (hors scope).
- Q4 — Parties gardées en mémoire : PAS de `skip_intent` → l'échange (message
  enrichi + réponse) suit le pipeline normal (intent + écriture épisodique).
- Q5 — Couleur : en-tête White/Black == `staroflexeur` ; sinon « je joue les noirs /
  blancs » dans le message ; sinon blancs par défaut, et la réponse le signale.
- Q6 — Position critique = position AVANT un coup de Nico, 3 sortes :
  (a) erreur de Nico, (b) occasion manquée après erreur adverse, (c) coup unique
  (écart MultiPV 1-2 large) même trouvé. Mesure = perte de % de gain (formule Lichess).
  ≤ 3 retenues : a/b d'abord par perte décroissante, puis c pour compléter.
- Qualité de chaque demi-coup (5 niveaux, demande Nico « coups corrects mais pas
  assez forts ») : meilleur / correct (≠ meilleur, perte < 10) / imprécision (≥ 10) /
  erreur (≥ 20) / gaffe (≥ 30), en points de % de gain.
- Q7/Q8 — Fiche par partie dès la v1 (`write_chess_game`, `aria_episodic`,
  type `chess_game`, dédoublonnée par hash des coups) : faits bruts par demi-coup
  (recalcul futur sans Stockfish) + synthèse : répertoire (ECO, ouverture, 12 premiers
  demi-coups), Elo des deux joueurs, 1re erreur Nico/adversaire, compteurs de qualité,
  précision par phase, pendule (`%clk` si présent), conversion/résilience, sanction des
  erreurs adverses, type de fin. Bilan / déviations de répertoire → sprint 27.

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_moteur_rendu.md` — paquet `chess_coach/` : analyse moteur, qualité, positions critiques, notation FR, rendu PNG | ✅ |
| 02 | `02_cablage.md` — CHESS_ANALYSIS : classifier, router, délégation LLM, contrat `images`, `_normalize`, envoi Telegram, règle 4 | ✅ (non commité) |
| 03 | `03_fiche_partie.md` — synthèse de partie + `write_chess_game` (palace prod) | ⏳ |
| 04 | `04_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Ouverte par le sprint : #79 position depuis une image (photo physique + capture
  d'écran) ; #80 relance moteur sur une position citée en texte libre ; #81 bilan
  joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) ;
  #82 questions d'ouverture sans PGN (LLM seul, hallucinations constatées) ;
  #83 lien de partie Chess.com → PGN via API publique.
- Fermée : aucune.

## §REPRISE

Tronçon 01 fait (2026-10-19) : paquet `chess_coach/` (analysis, notation, render),
`config.stockfish_path` / `config.chess_username`, `chess>=1.11` en requirements,
tests `tests/chess_coach/` (pytest 286 verts). Message B (04) : nico=black/header,
3 critiques (15...Ce4, 17...a5, 19...Cd8), 7,4 s [1 run VM].
Écarts : positions terminales (mat/pat) évaluées sans appel moteur ; pas de
`tests/chess_coach/__init__.py` (collision avec le paquet `chess_coach`).
Tronçon 02 fait (2026-10-19) : `CHESS_ANALYSIS` (règle 1b du classifier, avant URL),
`execution/routers/chess_router.py`, routing + `_normalize` → `images_text`, `send()`
Telegram (photos puis texte), règle inviolable 4 amendée dans CLAUDE.md. Tests :
classifier, router, `_normalize`, Telegram (pytest 291 verts). Sandbox message B
(vrai Stockfish, faux LLM) : 3 PNG (15...Ce4, 17...a5, 19...Cd8), message enrichi OK.
Choix non tranchés par le kickoff : sans Elo dans l'en-tête, consigne « joueur
amateur » ; étiquettes et phases traduites en français dans le message enrichi.
Suite : tronçon 03 (`03_fiche_partie.md`), puis run live 04 par Nico.
