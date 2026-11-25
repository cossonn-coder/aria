# Sprint 66 — tronçon 03 : charger une position FEN dans l'échiquier (dette 65-1)

Lire d'abord : `CLAUDE.md`, `docs/sprint66/00_etat.md`.

## Objectif

Une FEN collée dans le champ « Coller une partie PGN » (`#pgn`) puis « Charger la partie » place
la position et lance l'analyse live, au lieu de « PGN illisible ».

Constat (Nico, 2026-11-20) : `r7/P4rbk/… w - - 2 25` → « PGN illisible » ; `loadGame`
(`interfaces/board/index.html:1019`) ne lit que des coups.

## Fichier

`interfaces/board/index.html` seul.

## Comportement attendu

- Dans le chemin de « Charger la partie » : si le texte (espaces de bord retirés) est une FEN
  valide pour chess.js, jeu libre depuis cette position : `game = null`, coups devant vidés,
  colonnes vidées (comme « Nouvelle partie »), `chess.load(fen)`, `newPosition()` → analyse live,
  évaluation `/eval`, courbe et liste des coups de la ligne libre à partir de cette position.
  Ligne d'état : « position chargée ». Sinon, comportement PGN actuel.
- Rechargement de la page : la position de départ FEN est conservée (aujourd'hui `saveState`
  ne garde que la ligne libre rejouée depuis la position initiale) : ajouter la FEN de départ à
  l'état sauvé, `restoreState` la recharge avant de rejouer la ligne.
- « Exporter PGN » / « Envoyer à ARIA » depuis une position FEN : vérifier que le PGN porte les
  en-têtes `SetUp`/`FEN` (chess.js le fait s'il a été chargé par `load`) ; sinon les ajouter.

## Tests

Pas de test JS : `pytest tests/ -q` vert ; vérification au run live (tronçon 04).

## Hors scope

- Aucun changement serveur. Pas de FEN par paramètre d'URL ni depuis Telegram.

## Critère de fin

`pytest tests/ -q` vert ; page chargée sans erreur de syntaxe.
