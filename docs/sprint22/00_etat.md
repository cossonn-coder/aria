# Sprint 22 — État de conception

**Phase courante** : B — conception FIGÉE (OK Nico 2026-10-16), prête pour `/sprint-auto sprint 22`
**Branche** : `feat/sprint22-web-search`

## Décisions arrêtées

- Cible sprint 22 = accès monde extérieur (choix Nico 2026-10-16).
- v1 = recherche web seule, mais structure évolutive pour ajouter d'autres
  capacités (URL, météo…) sans retoucher le kernel (Nico).
- Déclencheurs explicites : « cherche en ligne », « cherche sur le web »,
  « donne-moi les sources de cette information », « source ? » (Nico).
- Fournisseur = **Tavily** palier gratuit (1000/mois, sans carte) ; clé
  `TAVILY_API_KEY` à créer par Nico avant le run live (Nico).
- Catégorie LLM `web_search` ajoutée au classifier, définie étroitement
  (actualité, résultats, prix, météo, horaires, événements récents), EN PLUS
  des mots-clés (Nico).
- Évolutivité = un `web_router` multi-op (modèle `image_router`) + fournisseur
  isolé dans une fonction `search(query)` ; une capacité de plus = 1 op +
  1 ligne de routing + 1 module. Pas de framework (Nico, reco Claude).
- Design (validé par l'OK de Nico) : requête toujours
  reformulée par LLM à partir du message + dernier tour (gère « source ? ») ;
  5 résultats, extraits ≤ 500 car. ; délégation à `LLMExecutionRouter`
  REASONING + `skip_intent` ; échec recherche → consigne « recherche
  indisponible » au lieu d'une erreur ; heuristique web avant la règle
  « message court → CONFIRMATION ».

## Carte des tronçons

| # | Kickoff | Statut |
|---|---------|--------|
| 01 | `01_effecteur_web.md` — Tavily + `web_router` + kernel + config | ✅ (265 verts) |
| 02 | `02_classification_web.md` — heuristique + catégorie LLM | ⏳ |
| 03 | `03_run_live.md` — run live (Nico) | ⏳ |

## Dettes

Fermée par le sprint (à la clôture) : idée « recherche web » du sprint 5
(ex-#21 perdu par renumérotation).

À ajouter au tableau au kickoff sprint 23 :
- Rappels différés + envoi proactif (scheduler) — sprint dédié.
- Lecture d'URL collée (capacité `web_router` suivante).
- Météo dédiée.
- `print()` dans `core/kernel.py` `_normalize`.
- Code sans caller apparent : `cognition/cognitive_dispatcher.py`,
  `execution/execution_plan_builder.py`, `cognition/dispatcher_types.py`.

## §REPRISE

Lire `CLAUDE.md` + ce fichier + le kickoff du prochain tronçon ⏳.
Tronçon 01 fait (effecteur web câblé, non commité au moment de l'écriture ;
`web_search` atteint `WebExecutionRouter` via `_build_dispatcher`, mais
n'est encore émis par aucun classifier).
Prochaine étape : tronçon 02 (`02_classification_web.md`), puis run live 03
par Nico (clé `TAVILY_API_KEY` dans `.env`).
