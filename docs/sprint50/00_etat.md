# Sprint 50 — état vivant (bilan de partie, flèches)

## Phase courante
Implémentation : tronçon 01 fait (non commité), tronçon 02 à suivre.

## Objectif
Un bilan de partie qui ne fait pas retenir une fausse leçon à Nico, et des miniatures dont les flèches disent la gravité de l'erreur et le piège.

## Branche de travail
`feat/sprint50-bilan`, créée depuis `main`.

## Constat de départ
Partie du 2026-11-05 (La_Bagouze – Mama_dor_de_pene, 0-1) : « deux mats en un coup (Bd8!?) », « la défaite vient de ces occasions manquées », « le roi noir vient de roquer » : trois affirmations fausses ou infondées [n=1]. Diagnostic : `docs/sprint50/audit_bilan.md`.

## Décisions arrêtées (Nico, 2026-11-05)
- **Bilan :** rédigé par le LLM d'ARIA à partir d'un bilan factuel calculé par le code, avec recherche web sur l'ouverture et le type de position.
- **Affichage :** bilan du code au-dessus du texte du LLM, et ligne des sources web.
- **Recherche :** 2 requêtes Tavily de 3 résultats par partie ; échec non bloquant. Essai, à juger sur les tokens du run live.
- **Pièges :** flèche cyan selon la règle de l'échiquier (`_TRAP_GAIN`, `_TRAP_P_MIN`), sur des données déjà calculées ; autres explosifs en orange ; ligne « Piège » écrite par le code dans la légende, le LLM ne parle plus du piège.
- **Erreurs jouées :** sortes a et b, flèche de la couleur de la gravité, échelle fixe et dégradé continu : 10 pts rose pâle (255, 190, 205), 25 pts rouge (215, 20, 35), 50 pts et plus noir (0, 0, 0), opacité 235. Autres coups joués en bleu ; erreurs adverses sans flèche.
- **Échiquier :** la stratégie passe du rose au blanc, pour ne pas confondre avec la couleur des erreurs.
- **Corrections de code :** variante jusqu'au mat annoncé dans `clear_advantage` ; « roqué » remplacé par « à l'aile ».

## Carte des tronçons
- 01 flèches et corrections (`01_fleches_corrections.md`) ✅ 519 tests verts ; rendus erreur et piège contrôlés en image ; à valider au run live.
- 02 bilan et recherche web (`02_bilan_web.md`) ⏳
- 03 run live par Nico (`03_run_live.md`) ⏳

## Dettes
Fermées par le sprint : aucune. #157 reste ouverte : le piège est lu sur les explosifs retenus, sans calcul du piège ni de la stratégie sur toute la partie.

## §REPRISE
Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳ (`02_bilan_web.md`). Tronçon 01 : la ligne « Piège » est placée entre « Variante » et « Variante du meilleur coup » ; la position piégeante est libellée « piège affiché » dans les faits donnés au LLM ; `_human_moves` utilise la nouvelle `trapping_replies`. Le `#ff5fb0` du badge de mat de la courbe (`index.html`) n'est pas la stratégie : inchangé. Prochaine étape : `/sprint-auto sprint 50`, sur la branche `feat/sprint50-bilan`.
