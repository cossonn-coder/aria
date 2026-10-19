# Sprint 28 — modèle joueur façon RPG (#81) — état

**Phase** : B figée (2026-10-19) → exécution `/sprint-auto sprint 28`.
**Branche** : `feat/sprint28-modele-joueur` (créée depuis `main` @ `sprint-27`).
**Audit** : `docs/sprint28/audit_modele_joueur.md`.
**Palace prod** : lu seulement ; seule écriture = fiches `chess_game` existantes
(`write_chess_game`, inchangé) enrichies de deux champs par coup.

## Carte des tronçons

| # | Tronçon | Kickoff | État |
|---|---|---|---|
| 01 | Difficulté des coups par Maia-2 (install `--no-deps`, `chess_coach/difficulty.py`, champs fiche) | `01_difficulte_maia.md` | ✅ |
| 02 | Modèle joueur pur (XP Elo par thème, niveaux, badges, ouvertures) + `bridge.load_chess_games` | `02_modele_joueur.md` | ⏳ |
| 03 | Bloc « Progression » écrit par le router + ligne historique pour le LLM + injection du bridge | `03_router_progression.md` | ⏳ |
| 04 | Run live (Nico) — PGN dans `run_live_parties.txt` | `04_run_live.md` | ⏳ |

## Décisions arrêtées

- Q1 (a) — Profil **recalculé à chaque analyse** depuis les fiches, aucune écriture de
  profil ; #17 / #54 restent ouvertes (cadrage « consolidation mémoire » écarté : le
  profil serait un cache dérivé).
- Résidus texte sprint 27 (#89-#93) hors sprint.
- Q2 — Vrai ressenti RPG : XP gagnée / perdue, paliers avec raison, badges, ludique ;
  thèmes : pièces en prise, punir les erreurs, ouverture, convertir l'avantage, finale ;
  Elo adverse = difficulté de la partie, défaite contre plus faible plus sévère ;
  inventaire d'ouvertures avec win rate.
- Q3 — Difficulté **dans le coup**, en Elo.
- Q4 (a) → spike fait. Q7 — **Maia-2** : difficulté = R − 400·log10(P/(1−P)), P = proba
  qu'un joueur du niveau de Nico joue le meilleur coup Stockfish ; hors coups 1-10
  (Maia absurde en ouverture) ; épreuve = perte ≥ 10 ou écart au 2e ≥ 10.
- Q5 — Classement Elo par thème façon puzzles (détail et constantes : kickoff 02) ;
  niveau = palier de 100 ; résultat de partie contre l'Elo adverse (K 32).
- Q6 (a) — Saison 1 depuis zéro : fiche saison 1 = `plies_json` avec clé `difficulty`.
- Q8 — 8 badges (kickoff 02) ; inventaire famille × couleur, ligne de l'ouverture jouée
  à chaque analyse ; inventaire complet sans PGN → dette #95.
- Q9 — Bloc « Progression » écrit par le router sous la réponse LLM ; le LLM ne reçoit
  qu'une ligne de données d'historique pour « Niveau : ».
- Install Maia : `--no-deps` dans le venv ARIA (vérifié : torch 2.11 / chess 1.11.2 OK) ;
  poids dans `/home/nico/.cache/aria-maia/` (hors Nextcloud).
- Constantes (K 16/8/32, seuils 10/15/70/20) : choix Claude, révisables au run live.

## Spike Maia-2 (2026-10-19)

Venv isolé `~/.cache/aria-spike-maia/` (scripts `work/spike.py`, `work/spike2.py`,
poids `maia2_models/`, test croisé venv ARIA via `extra/`). `/tmp` est un tmpfs en RAM :
y installer torch l'a rempli.
- Coût [n=3 parties] : chargement 2,2 s ; une passe groupée par partie 1,5-4,8 s
  (23-38 positions) ; RSS du process de test 620 Mo, torch compris.
- « Elo à partir duquel Maia joue le meilleur coup » : inutilisable (>2100 presque
  partout, Maia prédit le coup humain ; courbes P(Elo) plates 1100-1900).
- Définition retenue plausible au milieu de partie (reprises ≈ 950, 28.Nf6+ raté
  P = 0,78 ≈ 1100, 7.Bxf7+ ≈ 1900) ; absurde en ouverture (1.e4 ≈ 1700).

## Dettes

- Ouvertes par le sprint :
  - #95 Inventaire / bilan complet sans PGN (« où j'en suis aux échecs ? ») ;
  - #96 `summary.unconverted` vrai sur les parties à résultat `*` (outcome unknown) ;
  - #97 Renvoyer une ancienne partie la replace en dernier dans la chronologie (timestamp
    d'analyse) ;
  - #98 Fiches parasites « Test » ×2 / « Ami » dans le palace prod (ignorées : hors saison).
- Traitée partiellement : #81 (modèle joueur ; déviations de répertoire non traitées).
- Inchangées : #17, #54 (consolidation mémoire non nécessaire ici).

## §REPRISE

Tronçon 01 fait (pytest 314 verts) : maia2 installé `--no-deps` (chess 1.11.2 intact),
poids dans `/home/nico/.cache/aria-maia/`, `chess_coach/difficulty.py`, `difficulty` +
`second_gap` dans `plies_json`. Écart : `analyze()` prend un paramètre
`maia_models_dir` (défaut None = pas de Maia, passé par le router depuis `config`).
Position du spike b7b3 : P = 0,005 → bornée 0,01 → difficulté 2105 (spike : ≈ 1950).
Prochaine étape : tronçon 02, puis 03, puis run live 04 par Nico. Lire `CLAUDE.md`, ce fichier, le kickoff du tronçon courant.
