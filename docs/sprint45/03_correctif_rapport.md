# Sprint 45 — tronçon 03 : correctif du rapport de recherche (décidé par Nico après le run live 02)

## Constat (run live du 2026-10-30, 18:25)

1. **Rapport tronqué** : `document_write OK … chars=5035`. À la relecture, ARIA dit que le
   rapport « s'arrête en plein milieu de la section sur les engrais verts », et la liste des URL
   demandée en fin de rapport est absente (la réponse cite « Semaille », « Enracinés » sans URL).
   Hypothèse : plafond `max_tokens=1500` de l'appel DIGEST (`web_router._handle_research`) atteint.
2. **Nom du document** : « Recherche : fais une recherche sur la rotation des cultures au potager »
   car `subject = message[:80]` garde la phrase de déclenchement.

## À faire (périmètre strict)

1. **Plafond du rapport** : constante de module `_RESEARCH_REPORT_MAX_TOKENS = 3000` utilisée par
   l'appel DIGEST du rapport. Après l'appel, lire les tokens de sortie comme `url_read`
   (`usage.get("completion_tokens", usage.get("output_tokens"))`) et `log.warning(
   "web_research report hit max_tokens=%d", …)` si le plafond est atteint ; ajouter
   `report_tokens=%s` à la ligne `web_research OK`.
2. **Sujet sans phrase de déclenchement** : dans `cognition/cognitive_classifier.py`, à côté de
   `_WEB_RESEARCH_PHRASES`, une fonction `extract_research_subject(message) -> str` : première
   phrase de la liste trouvée (minuscules) → texte qui suit, débarrassé d'un « sur » initial et
   de la ponctuation/espaces de bord ; texte vide ou aucune phrase → message entier.
   `_handle_research` : `subject = extract_research_subject(message)[:80]`.
   Ex. : « fais une recherche sur la rotation des cultures au potager » → « la rotation des
   cultures au potager » ; « fais une recherche approfondie sur le compost ? » → « le compost ».
3. Tests : 1 test de `extract_research_subject` (les deux exemples), et dans le test nominal du
   router, vérifier que `doc_name` passé à `write_document` est « Recherche : <sujet> » et que
   `max_tokens=3000`.

Hors périmètre : compteur `pages=` de `web_research OK` (dette cosmétique), libellé « du fichier »
à la relecture (dette déjà notée).

## Run live de vérification (Nico)

`sudo systemctl restart aria.service`, puis `docs/sprint45/run_live/messages_03.txt` :

| # | Envoi | Attendu |
|---|---|---|
| 1 | `/oublie` | historique coupé |
| 2 | « fais une recherche sur l'association des légumes au potager » | rapport complet terminé par des URL ; journal `web_research OK … report_tokens=…` sans `hit max_tokens` ; fiche nommée « Recherche : l'association des légumes au potager » |
| 3 | « relis la recherche sur l'association des légumes » | relecture complète (pas « s'arrête en plein milieu »), URL présentes |

Succès : 2 et 3 conformes, aucun `ERROR`.
