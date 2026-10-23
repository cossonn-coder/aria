# Sprint 35 — tronçon 02 : page de l'échiquier

À lire avant : `CLAUDE.md`, `docs/sprint35/00_etat.md`, `docs/sprint35/01_backend_analyse_live.md`
(contrat HTTP), et le code livré au tronçon 01 (`interfaces/board_interface.py`).

## Objectif

Remplacer la page provisoire `interfaces/board/index.html` par l'échiquier jouable : deux
joueurs devant le même écran (Brave, PC Windows de Nico), calque orange du coup explosif,
états de l'analyse, flèche verte du seul coup.

## Fichier

`interfaces/board/index.html` — **un seul fichier** (HTML + CSS + JS module inline).
Commentaires en français, code en anglais.

Librairies (vérifiées le 2026-10-23 sur jsdelivr, HTTP 200) :
- `https://cdn.jsdelivr.net/npm/chessground@9.2.1/+esm`
- `https://cdn.jsdelivr.net/npm/chess.js@1.4.0/+esm`
- CSS : `https://cdn.jsdelivr.net/npm/chessground@9.2.1/assets/chessground.base.css`,
  `…/chessground.brown.css`, `…/chessground.cburnett.css`

## Comportement attendu

- **Échiquier** chessground, coups légaux via chess.js (destinations calculées à chaque coup,
  promotion en dame par défaut acceptée), les deux camps jouables.
- **Boutons** : nouvelle partie, annuler le dernier coup, retourner l'échiquier.
- **Champs** Elo blancs / Elo noirs (saisis par Nico, défaut 1300) ; un changement d'Elo
  renvoie la position.
- **Interrupteurs** : « Calque explosif » et « Seul coup » (indépendants). Interrupteur
  coupé → la flèche correspondante n'est pas dessinée (l'analyse continue côté serveur).
- À chaque position (coup joué, annulé, nouvelle partie, Elo modifié) : `POST /position`,
  mémoriser l'`id` rendu, effacer flèches et panneau.
- **Interrogation** `GET /state` toutes les ~1 s ; ignorer une réponse dont l'`id` n'est
  pas le courant.
- **Flèches** (`drawable.autoShapes` de chessground) :
  - orange = `explosive.uci` (brush à couleur orange définie dans la config `drawable.brushes`) ;
  - verte = `forced.uci` quand non null et « Seul coup » actif.
  - **jamais** de flèche du meilleur coup en dehors de `forced`.
- **Ligne d'état** sous l'échiquier :

  | `result` / `running` | Texte |
  |---|---|
  | `pending` | ⏳ analyse en cours — passe N/4… |
  | `explosive`, running | 🟠 coup explosif X — recherche continue (passe N/4) |
  | `none`, running | aucun coup explosif pour l'instant — recherche continue (passe N/4) |
  | `explosive`, terminé | 🟠 coup explosif X — analyse terminée |
  | `none`, terminé | ✔ aucun coup explosif — analyse terminée |
  | `decided` | — position décidée, pas de recherche |
  | `game_over` | partie terminée |
  | `error` | message d'erreur |

- **Survol** de la flèche orange (ou, si le survol d'une flèche SVG est trop fragile, survol
  de la ligne d'état « coup explosif ») : panneau listant les réponses humaines
  `explosive.replies` — `san`, probabilité en %, `line_san` — puis la suite
  `trap_line_san` si non vide.
- Page utilisable à la largeur d'un écran de PC ; pas d'exigence mobile.

## Tests

Pas de test JS (aucun navigateur sur la VM). Un test pytest : `GET /` sert une page qui
contient l'import chessground (non-régression du fichier servi). `pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Toucher au contrat HTTP ou à `chess_coach/` (sauf bug bloquant constaté : le documenter).
- chess.com, multijoueur, pendule, sauvegarde, PGN import/export.
- Build JS / npm / bundler.

## Critère de fin

Page servie, test vert, `pytest tests/ -q` vert, commit local. Validation visuelle au run
live (tronçon 03).
