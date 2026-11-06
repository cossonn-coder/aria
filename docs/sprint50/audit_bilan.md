# Sprint 50 — audit du bilan de partie (2026-11-05)

Base : 1 partie réelle (La_Bagouze – Mama_dor_de_pene, 0-1, 33 coups). Entrée du LLM reconstruite en local avec le code actuel (`analyze` + `_build_enriched`), sans écriture mémoire. Réponse : celle reçue sur Telegram à 09:37. Fréquence de ces erreurs sur les autres parties : non mesurée [n=1].

## Chaîne actuelle
- `execution/routers/chess_router.py::_execute_game` : diagrammes, fiche, progression, appel LLM (rôle REASONING), `_split_entries`, puis lignes écrites par le code (courbe, `_moves_line`, `_progression_block`).
- `_build_enriched` : faits par position critique + consignes. Partie entière résumée par `Compteurs Nico` et `Niveau (données)` : précision, erreurs adverses punies, résultat.
- Écrit par le LLM : titre, « Plan » de chaque position, ligne « Niveau ». Écrit par le code : légende factuelle, variantes, ligne 🎯, bloc Progression.

## Diagnostic

| Phrase du bilan | Vrai ? | Cause réelle | Vérifié |
|---|---|---|---|
| « deux mats en un coup (Bd8!?) » | Non : ni mat ni échec ; 31 et 30 réponses légales | L'entrée dit « si Bxd8 (36 %) : 20...Bxd8 21.Qxd8#, 98 % » : donnée juste, déformée par le LLM. Rien ne dit en toutes lettres « piège, mat seulement si l'adversaire prend ». | python-chess |
| « La défaite vient de ces occasions manquées » | Infondé | La consigne demande de juger le niveau, mais le LLM ne reçoit aucune donnée sur le déroulé : ni évolution du % de gain, ni moment de bascule. Il ne peut qu'inventer une cause avec ce qu'il a, les positions critiques. | `_level_line`, entrée reconstruite |
| « le roi noir vient de roquer » | Non : 17...Kf8 puis 20...Kg8 | **Erreur de notre code, pas du LLM** : `chess_coach/structure.py:54` déduit « roqué » de la seule case du roi. L'entrée dit « roi adverse : g8, roqué ». | `structure.py`, entrée reconstruite |

## Défaut supplémentaire trouvé : le mat disparaît de la légende
Légende affichée : « Variante : 20.Bd8 ; 20...Bxd8 prend Bd8. » Le coup qui justifie tout, 21.Qxd8#, manque, et le critère affiché est « avance de développement ».

Cause : `chess_coach/analysis.py::clear_advantage`. Le commentaire annonce « Mat annoncé : la ligne va jusqu'au mat », mais à n=2 le test du critère matériel/développement/activité s'exécute même quand `mate` est vrai et renvoie avant d'atteindre le mat. Touche aussi les sortes c et e (même fonction), non mesuré.

## Ce qui n'est pas un bug
- « Pire coup 18.Nc5 (−10 pts) » dans une défaite : exact. Pertes de 0 à 10 pts par coup, de 68 % (coup 17) à 6 % (coup 33) [rejeu local].
- « Aucune gaffe », précision 90 % : conformes au calcul existant.

## Limite de la correction par consigne
La consigne interdit déjà d'inventer (« n'invente aucun coup ni évaluation », « Ne décris aucune attaque, défense, menace… absente ») : le LLM a quand même déformé [n=1]. Ajouter des interdictions ne garantit rien ; seul le texte écrit par le code le garantit.

## Règles d'architecture
Rien à écrire de plus en mémoire, aucune lecture nouvelle : calcul depuis `analysis.plies`, déjà disponible dans le router. Palace prod non touché. `AnalystAgent` : à vérifier en phase B si la consigne d passe par son prompt (test garde-fou).

## Compléments après les arbitrages de Nico
- **Recherche web :** `web/tavily_search.py::search` est un module, pas un router : `chess_router` peut l'appeler sans contourner le kernel. Toute erreur y remonte en exception, à attraper pour ne pas bloquer l'analyse. Aucune écriture mémoire nouvelle.
- **Flèches :** `chess_coach/render.py` trace le coup joué en bleu (`PLAYED_ARROW`) et l'explosif en orange (`ALT_ARROW`) ; le routeur sait la sorte de position avant de dessiner.
- **Piège et explosif sont deux notions distinctes :** à l'échiquier, le piège cyan (`chess_coach/live.py`) suit sa propre règle ; il n'est pas calculé sur une partie envoyée (dette #157). Les réponses humaines nécessaires sont déjà dans `explosive.replies`.
- **Risque conservé :** le LLM reste rédacteur du bilan. Le bilan du code lui donne le déroulé qui lui manquait, mais rien ne garantit qu'il ne le déformera pas [n=1 observé].
