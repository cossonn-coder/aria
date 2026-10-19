# Sprint 28 — tronçon 05 : correctif post-run live (Global, lignes fusionnées, Groq)

Arbitrages de Nico après le run live 04 (2026-10-19). Trois changements, rien d'autre.

## 1. Global = moyenne des thèmes, nouveau thème « Résultats »

Constat : à la partie 1 (défaite 1307 contre 1352), le Global a pris +1, car les coups
trouvés l'alimentaient en plus du résultat. Nico : un coup trouvé fait monter **son
thème**, pas le Global ; le Global est la moyenne des thèmes.

Dans `chess_coach/player_model.py` :

- Nouveau classement `"result": "Résultats"` dans `LABELS` (placé en dernier).
- Le résultat de partie contre l'Elo adverse (K 32, `_RESULT_SCORE`, inchangé) met à jour
  `result` et **plus** `global`. `Trial("résultat", …)` enregistré sur `result`.
- L'épreuve d'ouverture (coups 1-10) met à jour `opening` seulement (plus `global`).
- Les épreuves coup par coup mettent à jour `_move_themes(plies, i)` seulement (plus
  `global`). Une épreuve qui ne relève d'aucun thème ne compte plus nulle part : accepté.
- `global` n'est plus un classement joué : après chaque partie, sa valeur = moyenne
  arithmétique des 6 autres classements (hanging, punish, opening, convert, endgame,
  result). `last_game["global"].delta` = moyenne après − moyenne avant la partie ;
  `top` = None.
- Badge « Coup de maître » : seuil inchangé, comparé à `ratings["global"].value`
  (la moyenne au moment de l'épreuve).
- Constantes, valeur de départ (`elo_nico` de la 1re partie) : inchangées.

Critère : une défaite qui ne change que `result` fait baisser le Global ; une partie où
seul un thème de coup monte fait monter le Global de ΔR / 6.

## 2. Fusion des lignes qui citent le même coup (router)

Constat : « Pièces en prise » et « Convertir l'avantage » citaient le même coup sur
deux lignes. Dans `execution/routers/chess_router.py`, `_progression_block` : les lignes
de thème dont l'épreuve `top` a le même `label` sont fusionnées en une seule, segments
joints par ` · `, texte de l'épreuve une seule fois à la fin :

```
Pièces en prise 1325 (−10) · Convertir l'avantage 1348 (−11) : 19.Bg5 raté (difficulté ≈1240)
```

Ordre : celui de `LABELS` (la ligne fusionnée prend la place du premier thème). Les
flèches ⬆️/⬇️ restent par segment. La ligne Résultats (épreuve « résultat ») suit la même
règle (« victoire contre 1452 » déjà géré par `_trial_text`). Le reste du bloc (règle
« delta arrondi nul → pas de ligne », 1re partie sans ligne de thème ni 📖) : inchangé.

## 3. Groq retiré du rôle REASONING

Constat : l'analyse d'échecs dépasse à elle seule le quota Groq gratuit (7 000 tokens
d'entrée / min) → 413 à chaque analyse, ~3 s perdues avant DeepSeek. Nico : retirer
Groq de `REASONING` (touche aussi web, URL, image interrogative — accepté).

Dans `llm/llm_router.py`, `ROUTING_TABLE[LLMRole.REASONING]` filtre les entrées `groq*`
exactement comme `LLMRole.DIGEST`. Commentaire français d'une ligne avec la raison.
CHAT / PLANNING / REFLECTION gardent Groq (121 réponses Groq en 7 jours).

## Tests

- `tests/chess_coach/test_player_model.py` : adapter les attentes ; cas nominal :
  défaite seule → Global baisse ; coup trouvé → thème monte, Global = moyenne.
- `tests/execution/test_chess_router.py` : une ligne fusionnée pour deux thèmes au même
  coup.
- Routage : REASONING ne contient aucun provider `groq*`.

## Hors scope (sprint 29, via `/conception`)

Thèmes par motif tactique (fourchette, sacrifice, clouage…) : nécessite une détection
de motifs inexistante aujourd'hui. Ne rien en préparer ici.
