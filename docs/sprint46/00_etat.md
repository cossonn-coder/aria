# Sprint 46 — état vivant

**Phase courante** : B/C — conception figée, prête pour `/sprint-auto sprint 46`.
**Branche** : `feat/sprint46-miniatures-ouvertures` (depuis `main`, tag `sprint-45`).

## Décisions arrêtées

- Sujet : dette #149, miniatures du compte rendu d'une partie centrées sur les coups manqués de Nico (choix de Nico, 2026-10-30).

- Q1 Coups manqués = a/b (imprécision, faute, gaffe) + d (explosif) ; rose / cyan (stratégie, piège) pas calculés sur la partie collée (coût ≈ 1 min/partie [estimation]) → dette.
- Q2 Budget : **4 miniatures** au total, les plus grosses erreurs ; s'il n'y en a pas assez, compléter avec les plus beaux coups (c, e). Nico demande en plus : nommer le joueur **La_Bagouze** dans la config.
- Q3 Pas de place réservée au coup spectaculaire (seulement en complément).
- Q4 Ordre de remplissage des 4 places : erreurs a/b (perte décroissante) → explosifs d (score décroissant) → beaux coups e puis c (score décroissant) ; une position déjà prise est sautée ; affichage chronologique.
- Q5 `config.chess_username = "La_Bagouze"` reconnu **en plus** de `Nico` par `detect_color` ; échiquier live inchangé (`Nico`).

- Demandes ajoutées le 2026-11-02 : flèche bleue du coup joué ; aucune miniature avant le coup 4 ; plan stratégique dans chaque miniature ; score Milieu de jeu dans la progression ; statistiques par ouverture ; une room par ouverture.
- Q6 Plan stratégique : le code calcule des faits structurels (colonnes ouvertes, pions isolés / doublés / passés, sécurité des rois, pièces non développées), le LLM écrit un « Plan : » à partir d'eux.
- Q7 Une room par ouverture du catalogue (12 + ajout d'une ligne), famille Lichess pour le reste ; migration des 66 fiches par script, avec sauvegarde (palace prod : exception au calibrage ; timestamps conservés, #97).
- Q8 Statistiques : ligne de l'ouverture jouée sous le compte rendu (V, N, D, %, par couleur) + commande Telegram `/ouvertures`.
- Détection : table Lichess `chess-openings` (CC0, 3 865 positions, 395 Ko) versionnée, à partir des coups joués ; ni Stockfish ni Maia ne nomment une ouverture.
- Flèche bleue = coup joué ; seule si c'est aussi le meilleur coup. Filtre `move_number >= 4` sur toutes les sortes.
- Progression : nouveau thème `middlegame`, ligne fixe Ouverture / Milieu de jeu / Finale.
- Q9 Anomalie : 8 fiches ont `La_Bagouze` en adversaire et 1 `TardoScoped`, Nico aux blancs par défaut, donc analysées du mauvais camp. **Décision de Nico : les 9 sont supprimées** à la migration (sauvegarde préalable).
- Q10 Pseudos reconnus : `La_Bagouze`, `TardoScoped`, `staroflexeur` (remplace Q5 : liste `config.chess_usernames`, en plus de `Nico`).
- 2026-11-02 : OK de Nico pour figer.

## Carte des tronçons

- 01 miniatures : 4 places, coup 4, flèche bleue, pseudos (`01_miniatures.md`) ✅
- 02 plan stratégique : faits structurels + consigne (`02_plan_strategique.md`) ⏳
- 03 ouvertures et progression : détection, catalogue, room, statistiques, `/ouvertures`, thème Milieu de jeu (`03_ouvertures_progression.md`) ⏳
- 04 script de migration : 9 fiches supprimées, 57 rangées, testé sur copie (`04_migration.md`) ⏳
- 05 run live par Nico, migration comprise (`05_run_live.md`, parties : `run_live_parties.txt`) ⏳

## Questions ouvertes

- (aucune)

## Dettes

- Ferme si run live OK : #149 (résidu → stratégie rose / piège cyan ci-dessous), #126 reste ouverte.
- Nouvelles, à inscrire au kickoff suivant :
  - Stratégie rose et piège cyan non calculés sur une partie envoyée (Q1).
  - Document indexé des fiches migrées non réécrit (« ouverture inconnue » possible), métadonnées seules.
  - 13 fiches `color_source=default`, blancs : camp invérifiable, le nom des blancs n'est pas stocké.
  - `find_explosive` cherche encore sur les coups 1-3, écartés ensuite par `select_critical`.

## À la clôture

`CLAUDE.md` (« room `chess` » → une room par ouverture), `docs/architecture/memory_layers.md`.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳. Audit : `audit_miniatures_erreurs.md`.
Tronçon 01 fait (sélection à 4 places dès le coup 4, flèche bleue, `config.chess_usernames`).
Prochaine étape : tronçon 02, `02_plan_strategique.md` (`/sprint-auto sprint 46`).
