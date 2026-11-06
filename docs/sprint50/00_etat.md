# Sprint 50 — état vivant (bilan de partie, flèches)

## Phase courante
CLOS (2026-11-06) : run live 5 fait par Nico, clôture demandée. Suite : `docs/sprint51/context_kickoff_sprint_51.md`.

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
- **Échiquier :** la stratégie passe du rose au jaune (d'abord blanc, illisible dans la liste des coups), pour ne pas confondre avec la couleur des erreurs.
- **Matériel (run live 1) :** la ligne donnée au LLM nomme les pièces et les pions (`Nico R contre N, 3 pions contre 4`) : le solde en points (+2) était lu comme « deux pions ».
- **Chutes proches (run live 1) :** le déroulé cite aussi tout coup d'au moins 20 pts et d'au moins 3/4 de la perte maximale (seuil 3/4 posé à l'implémentation, à juger au run live 2).
- **Corrections de code :** variante jusqu'au mat annoncé dans `clear_advantage` ; « roqué » remplacé par « à l'aile ».

## Retours du run live 2 (Nico, 2026-11-05)
- Courbe de la partie : points reliés par des segments droits. Fait.
- Échiquier : flèche d'erreur (même échelle que les miniatures, 10 pts et plus, les deux camps), case « Erreurs » cochée par défaut ; « Meilleur coup » coché par défaut et plus jamais décoché par le code (annule le retour sprint 39) ; bouton + entre le menu et le retournement sur la barre mobile. Fait, rendu à valider au run live.
- Observés : courbe conforme au déroulé, dégradé des erreurs, stratégie blanche. Non observés : flèche cyan, variante de mat.
- **Explication des erreurs (arbitré par Nico) :** sur les sortes a et b, légende en deux suites, « Meilleur coup » et « Ton coup », chacune suivie de sa fin (matériel, % de gain) ; « Pourquoi » écrit par le LLM à la place de « Plan ». Coup forcé = échec, prise ou menace (la menace est l'« attaque » déjà calculée, `new_targets`) ; le coup et sa réponse sont toujours montrés ; moteur relancé si sa ligne est tronquée. Borne de 10 demi-coups. Fait, « Pourquoi » à juger au run live 3. Le % de fin est celui de la ligne moteur, pas une nouvelle évaluation de la position de fin.
- Mesure avant correction : variante de 1 coup sur 21/162 positions, de 2 coups au plus sur 53/162 [2 parties, moteur à 0,15 s par position].

## Retours du run live 3 (Nico, 2026-11-05)
Partie glend0, nulle, sans erreur : les deux suites et « Pourquoi » restent à observer ; flèche cyan observée (coup 17).
- Points de la courbe colorés, Telegram et échiquier : le point d'une position porte le coup joué depuis elle ; priorité erreur, piège, explosif, stratégie, meilleur coup, neutre. Fait, interprétation à confirmer par Nico. Sur Telegram : tous les explosifs trouvés, côté Nico, sans stratégie (non calculée) ; meilleur coup en vert comme sa flèche. À l'échiquier : piège, explosif et stratégie n'apparaissent que sur les positions déjà analysées ; meilleur coup = perte sous 1 pt.
- Liste des coups de l'échiquier à la couleur de leur point ; erreurs en pastille, lisibles sur fond sombre. Fait.
- À arbitrer à la clôture : l'analyse a duré 211,6 s dont 197,7 s de recherche d'explosifs [n=1, 31 positions], alors que le message annonce « jusqu'à 2 minutes ».

## Retours du run live 4 (Nico, 2026-11-05)
Partie Ranacha vs La_Bagouze : suites comparées, « Pourquoi », liste et courbe colorées, échiquier validés par Nico. Deux corrections :
- `24...Kc7` n'expliquait pas le clouage levé : fait « décloue X » ajouté aux suites (clouage sur le roi seulement), à citer dans « Pourquoi ».
- Clic sur un coup de la liste : ajouté en jeu libre (`goToLine`) ; la liste n'est plus reconstruite à chaque passe du moteur, ce qui pouvait perdre un tap (introduit par `22378aa`).

Arbitrages de Nico après ce run :
- Point et coup de la liste gardent la couleur de l'occasion (cyan au coup 17 même si le meilleur coup a été joué).
- Meilleurs coups de la liste en bleu même si « Meilleur coup » est décoché.
- Pas de fait « cloue X » seul : à ajouter pour toutes les tactiques ou pas du tout. À reporter au tableau des dettes du sprint 51.

## Demandes de Nico avant le run live 5 (2026-11-06)
Arbitrages : bilan des deux camps, pastilles sur les coups nommés, règle chess.com pour le brillant, rapport /ouvertures du jour.
- Bilan sous le texte du LLM : précision toi / adversaire (Lichess), meilleurs coups `n/total` des deux camps, erreurs par gravité (imprécision ≥ 10, erreur ≥ 20, gaffe ≥ 30), coups brillants de Nico, meilleur et pire coup, clé des pastilles. Fait.
- Légendes : pastille emoji (Telegram en texte brut) sur le coup joué, le meilleur coup, l'explosif (🩵 si piège) et le 1er coup des lignes « Meilleur coup » et « Ton coup ». Coups des variantes sans pastille. Fait.
- Coup brillant (`explosive.is_brilliant`, porté en JS `isBrilliant`) : perte < 2 pts, < 90 % de gain avant le coup, pièce (cavalier ou plus) laissée en prise et prenable avec gain de matériel, ≥ 2 pions nets. Orange sur la courbe Telegram et dans la liste de l'échiquier (les deux camps), après piège et explosif ; listé dans le bilan pour Nico seulement. Fait, non observé sur partie réelle.
- `/parties <ouverture>` : rapport de `/ouvertures <nom>` limité aux parties du jour. Fait.

## Carte des tronçons
- 01 flèches et corrections (`01_fleches_corrections.md`) ✅ 519 tests verts ; rendus erreur et piège contrôlés en image ; à valider au run live.
- 02 bilan (`02_bilan_web.md`) ✅ ; recherche web retirée après le run live 1.
- 03 run live par Nico (`03_run_live.md`) ✅ runs 1 à 5 faits.

## Dettes
Fermées par le sprint : aucune. #157 reste ouverte : le piège est lu sur les explosifs retenus, sans calcul du piège ni de la stratégie sur toute la partie.

À arbitrer à la clôture : le LLM peut encore mal raconter un coup joué (« Qxf1+ échange ta dame contre un cavalier », alors qu'il gagne le cavalier) [n=1] ; il ne reçoit pas ce que le coup joué capture. Variantes d'un seul coup (34.Qa4, 33...Qa6) [n=2], cause non cherchée.

## §REPRISE
Lire `CLAUDE.md`, ce fichier, puis `03_run_live.md`. Après le run live 1 : recherche web retirée (`web_block`, `_sources_line`, `structure_terms`, `memory_message` supprimés, `llm_router.py` revenu à son état d'avant le sprint), `_material_line` en toutes lettres, chutes proches dans `story_line`. Écarts conservés du tronçon 02 : `story_line` prend `outcome`, issue inconnue traitée comme une nulle, `nico_wins` dans `summary.py`. Tronçon 01 : ligne « Piège » entre « Variante » et « Variante du meilleur coup », position libellée « piège affiché » pour le LLM, `_human_moves` passe par `trapping_replies`. Prochaine étape : run live 5 par Nico (voir « Retours du run live 4 »), sur la branche `feat/sprint50-bilan`.
