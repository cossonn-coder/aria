# scripts/archive/

Scripts de diagnostic conservés à valeur historique. Non maintenus —
ils étaient utiles pour caractériser un bug à un instant T mais leur
raison d'être disparaît avec le fix correspondant.

À ne pas relancer en prod sans relire le contexte du sprint dans
lequel ils ont été créés.

## Inventaire

- **`diagnose_classifier_cache_similarity.py`** — Sprint 4 / T7-bis-6.
  Prouvait le mismatch d'embedding entre l'écriture (document JSON
  sérialisé) et la lecture (query message brut) du cache classifier.
  Rendu obsolète par le fix sprint 5 / T2 (dette #20) : le document
  est maintenant le message brut, l'embedding est aligné, le mismatch
  n'existe plus. Le script lit toujours `aria_classifier` mais ne
  trouvera plus de documents JSON après le wipe T2.
