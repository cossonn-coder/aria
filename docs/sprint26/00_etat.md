# Sprint 26 — état de conception

**Phase** : correctif 05 figé (2026-10-19) — prêt pour `/sprint-auto sprint 26` (tronçon 05), puis run live 06
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
| 01 | `01_moteur_rendu.md` — paquet `chess_coach/` : analyse moteur, qualité, positions critiques, notation FR, rendu PNG | ✅ `7b3ad38` |
| 02 | `02_cablage.md` — CHESS_ANALYSIS : classifier, router, délégation LLM, contrat `images`, `_normalize`, envoi Telegram, règle 4 | ✅ `4ee056f` |
| 03 | `03_fiche_partie.md` — synthèse de partie + `write_chess_game` (palace prod) | ✅ `b3d79f0` |
| 04 | `04_run_live.md` — run live (Nico) | ❌ partiel (voir ci-dessous) |
| 05 | `05_correctif.md` — intent `jeux echecs` imposé (bug 1) + ancre « Partie contre … » (bug 2) | ⏳ |
| 06 | `06_run_live.md` — run live du correctif (Nico) | ⏳ |

## Dettes

- Ouverte par le sprint : #79 position depuis une image (photo physique + capture
  d'écran) ; #80 relance moteur sur une position citée en texte libre ; #81 bilan
  joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) ;
  #82 questions d'ouverture sans PGN (LLM seul, hallucinations constatées) ;
  #83 lien de partie Chess.com → PGN via API publique.
- Fermée : aucune.
- Ouvertes au run live 04 : #84-#87 (voir § Correctif 05).

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
Tronçon 03 fait (2026-10-19) : `chess_coach/summary.py` (`summarize`, `summary_text`),
`memory/writer.write_chess_game` (id `chess_game_<sha256 UCI[:16]>`, room `chess`,
W4), appel non bloquant dans `chess_router` avant la délégation LLM, CLAUDE.md
(règle 1 + couches mémoire). Tests : summary, writer (W4 + dédoublonnage), router
(pytest 293 verts). Sandbox message B (vrai Stockfish, palace temporaire, 2 envois) :
1 seule fiche, nico_color=black, outcome=unknown (Result « * »), opening_line OK,
plies_json 8 020 car. [1 run VM].
Choix non tranchés par le kickoff : perte des coups « best » ramenée à 0 pour la
précision (bruit moteur) ; `opening` = segment brut d'`ECOUrl` (tirets conservés).
Constat : ChromaDB n'enregistre pas les métadonnées None (clé absente à la relecture).
Suite : run live 04 par Nico.

## Correctif 05 (phase A, 2026-10-19)

Run live 04 : A/B/C/D/E envoyés. Conformes : D (même hash), E, analyse/fiche/images
partout, durées 2-8 s [1 run par message]. Non conformes : (1) A-D `intent SKIPPED
reason=namer_aucun` → échange non écrit en épisodique (contredit Q4) ; (2) C répond
sur la Position 1 de A au lieu de B. Audit : `docs/sprint26/audit_correctif_05.md`.

Décisions arrêtées :
- 2026-10-19 — Nico : tronçon correctif dans le sprint 26 (bugs 1 et 2), le reste en dettes.
- 2026-10-19 — Nico : cible sprint 27 = coups conseillés « explosifs » (dette #87).
- 2026-10-19 — Q11 (b) : ancre « Partie contre <adversaire> <date> <ouverture> » en tête
  du bloc enrichi ET en tête de la réponse (consigne), pour ancrer les questions de suivi.
  Pas de retouche du prompt AnalystAgent.
- 2026-10-19 — Idée Nico (wing `echecs`, room par ouverture pour les fiches) : proposée
  comme arbitrage d'entrée du sprint 27 (avec #81, #87) — à confirmer.

- 2026-10-19 — Q9 (a) : le chess_router pose `metadata["forced_intent_name"]` ; le
  llm_router saute resolve + namer et fait `apply(create, intent_name=…)`. Déterministe,
  ne touche pas les autres sujets (le prompt du namer reste tel quel).
- 2026-10-19 — Q10 : nom `jeux echecs` (réutilise l'intent créé par E au run 04).
- 2026-10-19 — Fiches `chess_game` inchangées (room `chess`) ; rangement wing/room par
  ouverture = arbitrage d'entrée du sprint 27. Nico : fiche de partie ≠ souvenir de la
  discussion (room = intent), compris.

Questions ouvertes : aucune.

Dettes ouvertes par le run live :
- #84 récit LLM inventé autour des coups corrects (matériel/menaces absents du bloc enrichi).
- #85 meilleur coup instable entre deux analyses de la même partie (15…g5 vs 15…Fc7).
- #86 413 Groq systématique sur requêtes échecs (bloc enrichi + historique enrichi > ITPM 7000).
- #87 CIBLE SPRINT 27 — coups conseillés explosifs : fenêtre de tolérance sur MultiPV
  (perte ≤ X pts de % de gain) + score pièges / coups forçants / déséquilibre /
  volatilité ; Maia (lc0) en option v2 ; orienté gambits et compensation de
  sacrifices. Cas de test Nico : 1.e4 e5 2.Dh5 Cf6 3.Dxe5+ Fe7 4.d3 O-O (SF d22 [1 run] :
  2…Cf6 −0,21 vs 2…Cc6 −0,40 ; 3…Fe7 seul coup ; après 4…O-O −0,22). Nico fournira
  d'autres cas par ouverture.

§REPRISE correctif : conception figée. Exécution : `/sprint-auto sprint 26` (tronçon 05),
puis run live 06 par Nico. Lire `CLAUDE.md`, ce fichier, `audit_correctif_05.md`, puis
`05_correctif.md`.
