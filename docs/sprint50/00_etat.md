# Sprint 50 — état vivant (bilan de partie, flèches)

## Phase courante
Run live 1 fait (2026-11-05, 2 parties), corrections appliquées, run live 2 par Nico à suivre.

## Objectif
Un bilan de partie qui ne fait pas retenir une fausse leçon à Nico, et des miniatures dont les flèches disent la gravité de l'erreur et le piège.

## Branche de travail
`feat/sprint50-bilan`, créée depuis `main`.

## Constat de départ
Partie du 2026-11-05 (La_Bagouze – Mama_dor_de_pene, 0-1) : « deux mats en un coup (Bd8!?) », « la défaite vient de ces occasions manquées », « le roi noir vient de roquer » : trois affirmations fausses ou infondées [n=1]. Diagnostic : `docs/sprint50/audit_bilan.md`.

## Décisions arrêtées (Nico, 2026-11-05)
- **Bilan :** rédigé par le LLM d'ARIA à partir d'un bilan factuel calculé par le code, avec recherche web sur l'ouverture et le type de position.
- **Affichage :** bilan du code au-dessus du texte du LLM.
- **Recherche web :** essayée au run live 1, retirée (Nico, 2026-11-05) : sources génériques ou boutiques, pas d'apport visible au bilan.
- **Pièges :** flèche cyan selon la règle de l'échiquier (`_TRAP_GAIN`, `_TRAP_P_MIN`), sur des données déjà calculées ; autres explosifs en orange ; ligne « Piège » écrite par le code dans la légende, le LLM ne parle plus du piège.
- **Erreurs jouées :** sortes a et b, flèche de la couleur de la gravité, échelle fixe et dégradé continu : 10 pts rose pâle (255, 190, 205), 25 pts rouge (215, 20, 35), 50 pts et plus noir (0, 0, 0), opacité 235. Autres coups joués en bleu ; erreurs adverses sans flèche.
- **Échiquier :** la stratégie passe du rose au blanc, pour ne pas confondre avec la couleur des erreurs.
- **Matériel (run live 1) :** la ligne donnée au LLM nomme les pièces et les pions (`Nico R contre N, 3 pions contre 4`) : le solde en points (+2) était lu comme « deux pions ».
- **Chutes proches (run live 1) :** le déroulé cite aussi tout coup d'au moins 20 pts et d'au moins 3/4 de la perte maximale (seuil 3/4 posé à l'implémentation, à juger au run live 2).
- **Corrections de code :** variante jusqu'au mat annoncé dans `clear_advantage` ; « roqué » remplacé par « à l'aile ».

## Carte des tronçons
- 01 flèches et corrections (`01_fleches_corrections.md`) ✅ 519 tests verts ; rendus erreur et piège contrôlés en image ; à valider au run live.
- 02 bilan (`02_bilan_web.md`) ✅ ; recherche web retirée après le run live 1.
- 03 run live par Nico (`03_run_live.md`) ⏳ run 1 fait, run 2 à faire.

## Dettes
Fermées par le sprint : aucune. #157 reste ouverte : le piège est lu sur les explosifs retenus, sans calcul du piège ni de la stratégie sur toute la partie.

À arbitrer à la clôture : le LLM peut encore mal raconter un coup joué (« Qxf1+ échange ta dame contre un cavalier », alors qu'il gagne le cavalier) [n=1] ; il ne reçoit pas ce que le coup joué capture. Variantes d'un seul coup (34.Qa4, 33...Qa6) [n=2], cause non cherchée.

## §REPRISE
Lire `CLAUDE.md`, ce fichier, puis `03_run_live.md`. Après le run live 1 : recherche web retirée (`web_block`, `_sources_line`, `structure_terms`, `memory_message` supprimés, `llm_router.py` revenu à son état d'avant le sprint), `_material_line` en toutes lettres, chutes proches dans `story_line`. Écarts conservés du tronçon 02 : `story_line` prend `outcome`, issue inconnue traitée comme une nulle, `nico_wins` dans `summary.py`. Tronçon 01 : ligne « Piège » entre « Variante » et « Variante du meilleur coup », position libellée « piège affiché » pour le LLM, `_human_moves` passe par `trapping_replies`. Prochaine étape : run live 2 par Nico, sur la branche `feat/sprint50-bilan`.
