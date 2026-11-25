# Sprint 66 — tronçon 02 : onglet « Miniatures » et deuxième chance dans l'échiquier

Lire d'abord : `CLAUDE.md`, `docs/sprint66/00_etat.md`, `docs/sprint66/01_miniatures_fiche.md`
(format `minis`).

## Objectif

Rejouer la position d'une miniature comme une **deuxième chance de trouver le coup** : position
sans indice, Nico joue, la page juge ; l'explication (légende Telegram + Pourquoi) et les suites
jouables viennent après.

## Fichier

`interfaces/board/index.html` seul. `openStored` (`:1001`) reçoit `stored.minis` (tronçon 01) ;
les garder (ex. `game.minis`). Une partie chargée autrement (PGN, nouvelle partie) n'a pas de
miniatures.

## Comportement attendu

1. **Onglet « Miniatures »** dans `#tabs` (`:112`) + panneau `#minis` (même mécanique que les
   autres panneaux : un seul visible sur téléphone, tous sur PC). Une entrée par miniature :
   libellé neutre qui ne donne pas la réponse, ex. « Position 1 — coup 12 (blancs) » /
   « Conversion — coup 30 (blancs) » (numéro et camp tirés du FEN `game.fens[ply]`). Sans
   miniatures : « Pas de miniatures pour cette partie. »
2. **Tap sur une entrée → exercice** : `goTo(ply)` ; mode exercice actif. Masqué pendant
   l'exercice tout ce qui donne la réponse : flèches (`drawShapes` sans formes), barre
   d'évaluation, ligne `#played` (« joué … meilleur … »), `#accuracy`, panneau d'analyse live
   (`#analysis`), colonnes explosif/piège/stratégie, courbe. Ligne d'état : « À toi de jouer :
   trouve le meilleur coup. » + bouton « Voir la solution ».
3. **Coup joué par Nico pendant l'exercice** :
   - réussi si SAN = `best` ou ∈ `also`, ou si la perte < seuil (pts de % de gain du camp au
     trait : % de gain de la position, connu par `evals.get(game.fens[ply])`, moins celui
     après le coup, obtenu par `POST /eval`) → « ✔ Trouvé » (ou « ✔ Bon coup, −X pts ») puis
     solution affichée (point 4) ;
   - raté → « ✘ −X pts, réessaie », retour à la position (`goTo(ply)`), le mode exercice reste.
   - L'adversaire ne répond pas.
4. **Solution** (réussite ou bouton) : fin du mode exercice (tout réapparaît), `caption`
   affichée (retours à la ligne conservés), puis une ligne cliquable par `lines` :
   « Meilleur coup : Nf5 exf5 Qxf5 ». Tap → échiquier à la position de la miniature avec la
   suite en coups devant (`ahead`, sommet = 1er coup) : ▶ la joue coup par coup en variante,
   « Revenir à la partie » inchangé.
5. **Seuil réglable** : curseur dans `#controls` « Seuil 2e chance : N pts », `type="range"`
   1 à 30, défaut 10, conservé dans l'état `localStorage` (`saveState` / `restoreState`).
6. Toute navigation hors exercice (autre entrée, ⏮◀▶⏭, liste des coups, nouvelle partie)
   termine le mode exercice.

## Tests

Pas de test JS dans le repo (comme les sprints précédents sur la page) : `pytest tests/ -q`
reste vert ; vérification au run live (tronçon 04).

## Hors scope

- Aucun changement serveur (tronçon 01 fournit `minis`).
- Pas de miniatures pour un PGN collé ; pas de FEN (tronçon 03).
- Ne pas modifier la mécanique existante des variantes au-delà de ce qu'exige le point 4.

## Critère de fin

`pytest tests/ -q` vert ; page chargée sans erreur de syntaxe (le module JS se lit).
