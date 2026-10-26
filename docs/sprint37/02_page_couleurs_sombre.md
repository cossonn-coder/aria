# Sprint 37 — tronçon 02 : page — flèches cyan/rose, trois colonnes, mode sombre

Lire d'abord : `CLAUDE.md`, `docs/sprint37/00_etat.md` (décisions lots 2-3),
`docs/sprint37/01_analyse_piege_strategie.md` (format de `trap` / `strategy` dans `/state`).

Seul fichier de prod : `interfaces/board/index.html` (servie relue à chaque GET : pas de
redémarrage pour la page seule).

## État de départ (à relire dans le fichier)

Flèches `orange` (brosse perso), `green`, `blue` dans `drawShapes`, cases `show-explosive`,
`show-forced`, `show-best`. Marge droite `#saved` (Map clé FEN → `{explosive, best}`,
`renderSaved`), fonctions `variation(fen, sans)` (coups survolables + mini échiquier),
`explosiveDetails(fen, explosive)`. Thème clair (`#f4f1ec`), échiquier chessground `brown`.

## Comportement attendu

1. **Flèches** : brosses perso `cyan` et `pink` (à côté de `orange`). Cases à cocher
   « Piège » (`show-trap`) et « Stratégie » (`show-strategy`), cochées par défaut.
   **Une flèche par coup**, priorité : seul coup (vert) > explosif (orange) > piège (cyan) >
   meilleur coup (bleu) > stratégie (rose). On empile dans cet ordre les calques cochés et on
   saute un coup (uci) déjà dessiné. Le bleu suit la règle du point 4 (dernier recours).
2. **Trois colonnes** à droite des contrôles, sur toute la largeur restante de l'écran :
   « Coups explosifs » (orange, existant), « Pièges » (cyan), « Stratégie » (rose), chacune
   avec sa pastille de couleur en titre, défilement vertical propre. Chaque colonne garde ses
   blocs par FEN jusqu'à « Nouvelle partie » (même règle que l'orange : une passe plus
   profonde remplace le bloc de la même position).
   - Cyan : titre `numéro + coup` (survolable), « (aussi le meilleur coup) » si
     `trap.uci === best.uci` ; puis pour chaque réponse piégeante :
     `réponse — p % — ` + `variation(fen, [trap.san, ...reply.line_san])`.
   - Rose : sauvegardé seulement quand sa flèche est dessinée (uci ≠ seul coup ; voir
     point 4), « (aussi le meilleur coup) » si `strategy.uci === best.uci`. Titre `numéro + coup`, ligne « pronostic humain X % (meilleur coup Y %) »
     (`value`, `best_value` arrondis), puis `variation(fen, strategy.pv_san)`.
   - Orange : inchangé, plus « (aussi le meilleur coup) » dans le titre si c'est le cas.
3. **Mode sombre permanent** : fond, texte, panneaux, boutons et champs sombres ; cases de
   l'échiquier en tons sombres (surcharger le fond de `cg-board`, pour le grand échiquier et
   le mini). Les cinq couleurs de flèches et les pièces doivent rester lisibles ; les
   coordonnées aussi. Pas de bouton, pas de `prefers-color-scheme`.
4. **Flèche bleue rationnée, en dernier recours** (Nico, 2026-10-26, lot 4, ajout en
   cours de sprint ; remplace la priorité du point 1 pour le bleu). Ordre de dessin :
   vert > orange > cyan > rose (un coup déjà dessiné est sauté), puis le bleu **seulement si
   aucune autre flèche n'est dessinée dans la position** (calques cochés uniquement : une case
   décochée ne bloque rien). Si une autre flèche est le même coup que le meilleur coup, c'est
   l'autre couleur qui s'affiche et le bleu n'est pas décompté. En plus, le bleu n'est
   dessiné que si :
   - le numéro de coup du FEN (fullmove) est ≥ 10 ;
   - le camp au trait a eu moins de 3 flèches bleues dans la partie ;
   - le même camp n'a pas eu de flèche bleue à son coup précédent (position deux demi-coups
     plus tôt dans l'historique).
   Mémoire : un `Map` FEN → camp des positions où le bleu a été dessiné, vidé par
   « Nouvelle partie ». Une position déjà dans le `Map` garde sa flèche (passe plus profonde,
   retour en arrière) sans recompter. Seul le bleu réellement dessiné compte. Conséquence
   assumée : le rose étant rendu dans toute position non terminale, le bleu ne s'affiche en
   pratique que si « Stratégie » est décochée. La case « Meilleur coup » du bloc et les
   mentions « (aussi le meilleur coup) » de la marge restent inchangées.

Garder le style du fichier (commentaires français, `textContent` / `append`, pas de
`innerHTML`). Réutiliser `variation` et le schéma de `renderSaved` ; factoriser le rendu
d'un bloc seulement si les trois colonnes le rendent naturel.

## Tests

`tests/interfaces/test_board_interface.py::test_index_serves_chessboard_page` : ajouter
l'assertion que la page servie contient `show-trap` et `show-strategy`. Pas de test JS.

## Hors scope (ne PAS faire)

- Backend (`live.py`, `board_interface.py`) : tronçon 01.
- Nouvelles options (sélecteur de thème, réglage des seuils).
- Retoucher le panneau de survol de la ligne d'état au-delà de ce qu'imposent les couleurs.

## Critère de fin

`pytest tests/ -q` vert ; page chargée sans erreur JS de syntaxe (`node --check` sur le
module extrait du `<script type="module">`, en fichier jetable) ; rendu visuel à valider
au run live (tronçon 03).
