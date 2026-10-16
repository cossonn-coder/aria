# Sprint 22 — Tronçon 02 : classification `web_search`

À lire avant : `CLAUDE.md`, `docs/sprint22/00_etat.md`,
`docs/sprint22/audit_monde_exterieur.md` (§2, §7). Prérequis : tronçon 01
commité (`CognitiveOperation.WEB_SEARCH` existe, `web_router` câblé).

## Objectif

Faire émettre `web_search` par le classifier, de deux façons :
1. **Heuristique explicite** (phrases de Nico), sans appel LLM ;
2. **Catégorie LLM** `web_search` étroite dans `CLASSIFIER_PROMPT`.

## Fichier à toucher

`cognition/cognitive_classifier.py` uniquement (+ tests).

1. Nouvelle fonction `detect_web_search_intent(message: str) -> bool`, sur le
   modèle de `detect_image_generation_intent` :
   - vrai si le message (minuscules) contient « cherche en ligne », « cherche
     sur le web », « cherche sur internet », « recherche en ligne »,
     « recherche sur le web », « donne-moi les sources », « donne moi les
     sources » ;
   - vrai si le message, nettoyé (strip, minuscules, sans ponctuation finale
     ni espaces), vaut exactement « source » ou « sources » (couvre « source ? »,
     « Sources ? », « source? »).
   - **Pas** de match sur le mot « source » à l'intérieur d'une phrase
     (« source d'eau », « la source de la Seine »).
2. Dans `classify_operation`, insérer l'heuristique web en **nouvelle première
   règle texte**, avant l'heuristique image (actuelle étape 2) et donc avant
   la règle « message court → CONFIRMATION » (étape 3, qui avalerait
   « source ? », 8 caractères). L'étape 1 (metadata image) reste en tête.
   Mettre à jour le commentaire d'en-tête du pipeline (liste numérotée).
3. `CLASSIFIER_PROMPT` : ajouter une ligne, après `reasoning` :
   `- web_search : information récente ou externe que tu ne peux pas connaître (actualité, résultats sportifs, prix, météo, horaires, événements récents) ("quel temps demain à Caen", "score du match d'hier", "prix actuel du cuivre")`.
   Ne pas modifier les autres catégories.
   `_parse_operation` gère déjà la nouvelle valeur via l'enum ; le cache
   `aria_classifier` mémorisera `web_search` comme les autres verdicts — rien
   à faire.

## Tests à ajouter

Dans `tests/cognition/` (nouveau `test_classifier_web_search.py`) :
1. `classify_operation("source ?")` → `WEB_SEARCH` sans `llm_router`.
2. `classify_operation("cherche sur le web le score du match de Caen")` →
   `WEB_SEARCH` sans `llm_router`.
3. `detect_web_search_intent("il faut trouver une source d'eau pour le potager")`
   → `False`.
4. `"web_search"` présent dans `CLASSIFIER_PROMPT`.

`pytest tests/ -q` vert.

## Hors scope (NE PAS faire)

- Ne pas toucher au router web, au kernel, ni au seuil `MIN_MESSAGE_LENGTH`.
- Ne pas retoucher les mots-clés image ni les autres catégories du prompt.
- Ne pas purger le cache `aria_classifier`.

## Critère de fin

Tests verts ; « source ? » et les phrases explicites sortent `web_search`
sans appel LLM.
