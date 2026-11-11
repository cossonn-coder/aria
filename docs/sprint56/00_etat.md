# Sprint 56 — État vivant

**Phase** : B figée (kickoffs écrits) → `/sprint-auto sprint 56`
**Branche** : `feat/sprint56-verite-parties`
**Audit** : `docs/sprint56/audit_session_2026-11-11.md` (constats 1 à 6)

## Sujet

Aria dit des choses fausses sur les parties et sur ce qu'elle fait : doublons de fiches (PGN
tronqué), issue « * » non corrigeable, LLM qui affirme avoir corrigé la base / nie avoir accès
aux parties / calcule des variantes sans moteur / promet des fonctionnalités. Besoin de fond :
consignes durables données depuis Telegram. Exemples versés par Nico : 11/11 08:01-08:26,
10/11 13:03, 14:16, 16:44, 19:17. Nico : « ça termine le périmètre pour cette passe ».

## Périmètre proposé (non validé)

0. Hors sprint, d'abord : diagnostic + réparation de la recherche vectorielle (`Error finding id`, constat 5).
1. Doublons : une partie dont les coups sont le début d'une fiche du même adversaire (ou l'inverse)
   est la même partie ; la plus longue gagne. Nettoyage palace : Amateurspoeler-47, UIALY-101.
2. Issue : `/issue <adversaire> victoire|nulle|défaite` (sans LLM, writer) ; renvoi du PGN
   complet d'une partie connue = remplace la fiche.
3. Liste des parties fournie au LLM sur les questions d'échecs (lignes façon `/parties`), assemblée
   par le kernel / llm_router (règle 3 : l'agent ne lit rien).
4. Consigne d'honnêteté injectée par le code : ne jamais prétendre avoir écrit / corrigé ;
   pas de variante sans données moteur ; pas de « noté » sans `/consigne` ; une demande de
   fonctionnalité = « il faut du code », pas une promesse.
5. `/consigne <texte>`, `/consignes`, retrait : stockage via `writer.py` (`aria_semantic`, dette #17),
   injection dans chaque prompt système (AnalystAgent compris → test garde-fou
   `tests/agents/test_analyst_prompt_guard.py`).
6. Alerte adversaire suspect dans le bilan, ligne calculée par le code (voir décisions).
7. Run live.

Hors sprint (dettes) : moteur sur les questions de suivi d'une position (#82/#84/#92) ;
analyse LLM de N parties au-delà de la liste ; PGN sans en-tête White/Black routé au LLM.

## Décisions arrêtées

- 2026-11-11 : périmètre 0-7 validé par Nico.
- 2026-11-11 : alerte adversaire incluse : ligne `⚠️ précision adverse X % sur N coups (Y Elo)`,
  si ≥ 20 coups adverses et précision adverse ≥ 95 % ; un seul seuil, le nombre de coups affiché.
- 2026-11-11 : réparation palace (0) FAITE. Fork `mempalace-fork` commit `252c96a5` (index gardé
  après suppressions : `total_elements_added >= labels`, test ajouté, 69 tests verts) ; palace
  reconstruit (`migrate_embedder.py` mpnet→mpnet, 1959/1959, 12:14) ; sauvegarde
  `~/.mempalace/palace.pre-sprint56-repair-20261111` + `~/.mempalace/embedder-migration-marker.pre-sprint56-repair`.
  Vérifié au redémarrage 12:18 : plus de `Error finding id`, nouvel index non mis en quarantaine.
  Réponse 12:19 « Je corrige ma mémoire… il n'y en a qu'une seule enregistrée » : fausse (2 fiches
  au palace) → illustre encore le constat 3.

## Arbitré pour le sprint 57 (« évaluer et classer les parties »), 2026-11-11

Hors sprint 56, à concevoir à la suite :
- Classement 🏅 au sein d'une catégorie longueur (courte / moyenne / longue, seuils à fixer)
  × cadence (blitz / rapide, `TimeControl`) ; précision affichée = brute. « On teste ça. »
  Temps passé par coup : plus tard.
- Occasions manquées = (a) erreur adverse non punie + (b) coup explosif non joué. Dans les
  miniatures, elles passent AVANT les erreurs de Nico (« plus important à voir ; les petites
  erreurs sont moins importantes ») ; à faire apparaître aussi dans le bilan final.
  Code actuel : `chess_coach/analysis.py:524` `select_critical`, budget 4 : a/b → d → e → c.

- 2026-11-11 : découpage validé par Nico (6 tronçons ci-dessous).
- 2026-11-11 : parties fournies au LLM : 20 par défaut ; « N dernières » → N ; « toutes » → toutes
  (paramètre lu dans le message).
- 2026-11-11 : retrait d'une consigne = `/consigne retire N`.

## Carte des tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_doublons.md` — même partie = préfixe + même adversaire ; script de nettoyage | ✅ (568 verts ; script à blanc sur prod : 2 paires attendues, 301 fiches lues) |
| 02 | `02_issue.md` — `/issue <adversaire> victoire\|nulle\|défaite` | ✅ (571 verts ; `update_chess_game_result` + `_cmd_issue`) |
| 03 | `03_alerte_adversaire.md` — ligne ⚠️ précision adverse ≥ 95 % sur ≥ 20 coups | ⏳ |
| 04 | `04_consignes.md` — `/consigne`, `/consignes`, `/consigne retire N` + règles d'honnêteté | ⏳ |
| 05 | `05_parties_au_llm.md` — liste des N parties dans le contexte LLM | ⏳ |
| 06 | `06_run_live.md` + `06_run_live.txt` — run live (Nico) ; nettoyage palace au début | ⏳ |

## Dettes ouvertes par le sprint (à reporter au kickoff 57)

- PGN sans en-tête `White`/`Black` (ex. 11/11 08:01, avec `Termination`) routé au LLM, qui écrit
  une analyse sans moteur.
- Questions de suivi sur une position : LLM sans moteur (recoupe #82, #84, #92) ; atténué par les
  règles du tronçon 04.
- `/issue` ne réécrit pas le texte indexé de la fiche (« résultat * (issue inconnue) »).
- Bilan calculé sur N parties (stats) au-delà de la liste brute du tronçon 05.
- Fork `mempalace-fork` : commit `252c96a5` local sur `feat/configurable-embedder`, non poussé.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis l'audit. Tronçons 01-02 faits (02 non commité à sa sortie). Prochaine étape : `/sprint-auto sprint 56` (tronçons 03 → 05), puis run live 06 par Nico (`scripts/sprint56_dedup_games.py --apply` au début, service arrêté, sauvegarde).
