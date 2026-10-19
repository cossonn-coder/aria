# Sprint 27 — Tronçon 09 : router — format concis, faits calculés, tournant, niveau

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md` (§ Correctif 2),
`docs/sprint27/audit_run_live_07.md` (§4), puis `execution/routers/chess_router.py` et
`chess_coach/summary.py` (`summarize`) en entier. Le tronçon 08 a ajouté la sorte
`kind="e"` (tournant : `ply` = coup de Nico qui punit, `score` = perte de l'erreur adverse,
erreur adverse = `analysis.plies[ply.ply - 1]`).

## Objectif

Nico veut une réponse **courte** : moments critiques, coups au potentiel explosif,
appréciation du niveau de jeu. Plus d'axes de travail (ils reviendront après le sprint 28,
modèle joueur). Le texte du run 07 inventait des relations (« fou c4 attaque f7 ») et le
bilan matériel, gardait la notation française (historique de conversation), omettait la
suite du piège.

1. **Consigne générale réécrite** (`_build_enriched`) — format imposé :
   - 1re ligne exacte : l'ancre (inchangé) ;
   - puis une entrée par position, dans l'ordre Position 1, 2, 3… : **1 à 3 phrases**
     (le coup, l'idée, le chiffre clé) ;
   - puis une ligne **« Niveau : »** de 2 phrases (mal joué / passif / solide / brillant,
     justifié par les données de niveau, cf. 4) ;
   - rien d'autre : pas de sections « ce qui se passe » / « pourquoi », **pas d'axes de
     travail** (retirer « Termine par 1 à 3 axes de travail ») ;
   - garder : uniquement les coups et lignes fournis, notation anglaise ;
   - ajouter : « ne décris aucune attaque, défense, menace ou colonne absente des lignes
     matériel / attaquées ».
   Consigne d'ouverture (idées classiques, gambit = choix assumé) : garder, en la
   ramenant à « une demi-phrase quand c'est pertinent » pour tenir le format court.
2. **Faits calculés par position** (à côté de la ligne `pièces :` existante), depuis
   `fen_before` :
   - `matériel : Nico +N / −N / égal` (valeurs 1/3/3/5/9, du point de vue de Nico) ;
   - `attaquées : …` : pour chaque camp, les pièces (hors pions et roi) attaquées par
     l'adversaire, avec leur(s) attaquant(s), et la mention « non défendue » le cas
     échéant ; plus les pions attaqués non défendus. Format libre et court
     (ex. `attaquées : blancs Nf3 (par Bg4) ; noirs pion e5 non défendu (par Nf3)`),
     « aucune » si rien.
3. **Sorte e — tournant** :
   - `_KIND_FR["e"] = "tournant (erreur adverse punie)"` ;
   - légende : `Position N — coup 8 (blancs) : tournant après 7...h6?, joué 8.e5
     (meilleur 8.e5)` (forme de `_caption` pour a/b, précédée de l'erreur adverse) ;
   - bloc : une ligne `erreur adverse 7...h6 : perte 18 pts (meilleur 7...Be7)` puis la
     **variante de la punition** = la ligne coupée au point d'arrêt fournie par le tronçon 08
     (champ de `CriticalPosition`), suivie du critère atteint ; même affichage
     (ligne coupée + critère) pour les coups uniques c ;
   - consigne (si une e est présente) : « pour chaque tournant, nomme l'erreur adverse et
     montre la variante qui la punit (coups fournis) ». Exigence Nico : la variante doit
     apparaître dans la réponse.
   - flèche : verte = meilleur coup (comportement existant, rien à changer dans
     `render_position`).
4. **Données de niveau** dans le bloc, une ligne tirée de `summarize(analysis)` (déjà
   calculé dans `execute`) : compteurs Nico (ligne existante), précision par phase
   (`accuracy_opening/middlegame/endgame`, phases absentes omises), erreurs adverses punies
   (`opponent_errors_punished` / `opponent_errors`), résultat. Passer `summary` à
   `_build_enriched` au lieu du seul `opening` (paramètre ajouté au tronçon 06).
5. **Occasion explosive — l'accent du message** (retour Nico 2026-10-19, prime sur le
   tronçon 06) : Nico veut l'**idée**, la **variante si l'adversaire joue le coup logique**,
   jusqu'à un avantage clair, et **pourquoi ce coup est difficile à éviter pour l'adversaire**. Il ne
   veut **ni le coût, ni « quand le tenter », ni « ce qui se passe »**.
   - Bloc `_explosive_lines` réécrit :
     - plus de coût / % de gain du coup explosif (ni dans la ligne « explosif », ni
       ailleurs dans le bloc d) ;
     - `réponse logique : exd5 (prend le cavalier offert)` = la prise naturelle
       (`trap_reply_san`) ; à défaut de prise, la 1re réponse de `replies` ;
     - `variante : 8...exd5 9.… …` = `trap_line_san` (déjà coupée au point d'arrêt par le
       tronçon 08), numérotée, suivie du critère atteint en français (`material` → gain
       matériel, `crushing` → position écrasante, `mate` → attaque de mat, `development` →
       avance de développement, `activity` → avance d'activité) ;
     - `fin de variante : matériel Nico ±N, % de gain Nico X %` + ligne `attaquées :`
       (pièces protégées / vulnérables) au point d'arrêt, calculées depuis `trap_end_fen` / `trap_end_win` avec les mêmes
       helpers que le point 2 (pour que le LLM explique l'avantage quand il n'est pas
       matériel sans l'inventer) ;
     - `difficulté pour l'adversaire : …` : la réponse logique gagne du matériel à vue
       (pièce offerte), et combien de réponses de `replies` tiennent réellement (écart ≤ 5
       pts de % de gain pour Nico avec la meilleure réponse), avec la meilleure réponse en
       SAN — ex. `seule réponse qui tient : Qd6 (les 2 autres : Nico ≥ 62 %)` ;
     - garder le matériel offert / sacrifié et les étiquettes forçantes (ce sont l'idée).
   - Consigne d réécrite : « pour chaque occasion explosive : l'idée en une phrase ; la
     variante si l'adversaire joue la réponse logique (coups fournis, rien au-delà) et
     l'avantage atteint (critère fourni), expliqué par les pièces protégées / vulnérables de
     la fin de variante ; pourquoi la bonne réponse est difficile à trouver
     pour l'adversaire, d'après la ligne difficulté. Ne donne ni le coût, ni quand le
     tenter, et ne le présente jamais comme le meilleur coup. » Cette entrée peut dépasser
     les 1 à 3 phrases des autres positions (l'accent du message est là).
6. **Conversion de notation en sortie** : sur `result["text"]` avant le retour, remplacer
   les lettres de pièce françaises non ambiguës devant une case : `C`→N, `F`→B, `T`→R,
   `D`→Q, y compris prises et désambiguïsation (`Dxe5+`→`Qxe5+`, `Cbd7`→`Nbd7`,
   `Tae1`→`Rae1`). **`R` laissé tel quel** (roi en français, tour en anglais). Une petite
   fonction + regex à frontière de mot ; ne pas toucher aux mots français (« Fou », « De »,
   « Cela » : la lettre doit être suivie d'une case ou d'un `x` + case, ou d'une colonne /
   rangée + case). Limite assumée : l'échange écrit en conversation garde le texte brut.

## Tests (cas nominal)

Dans `tests/execution/test_chess_router.py` (adapter les assertions existantes qui
dépendent de la consigne) :
- bloc enrichi : lignes `matériel :` et `attaquées :` sur une position connue ;
- sorte e : légende « tournant après … » et ligne « erreur adverse … » ;
- consigne : contient « Niveau » et ne contient plus « axes de travail » ;
- conversion : `"2.Dh5 Cxe5 Tae1 Fe7, Cela"` → `"2.Qh5 Nxe5 Rae1 Be7, Cela"` ;
- bloc d : contient « réponse logique », « variante », le critère en français, « fin de variante »,
  « difficulté » ; ne contient plus « coût ».

`./venv/bin/pytest tests/ -q` vert.

## Hors scope

- Pas de modification de `chess_coach/analysis.py` / `explosive.py` (tronçon 08).
- Pas de rédaction déterministe du texte (piste structurelle écartée).
- Pas d'axes de travail ni d'appréciation sur l'historique (sprint 28).
- Pas de correction du texte stocké en conversation, ni du Groq 413 (dette).
- Pas de prompt AnalystAgent (la consigne est dans le message enrichi du router).

## Critère de fin

Tests ci-dessus verts, suite complète verte, `00_etat.md` : tronçon 09 ✅ + §REPRISE.
