# Sprint 29 — Tronçon 07 : occasions explosives, règle hybride

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_retours_run_live.md` §1.

## Objectif

Retrouver les « idées risquées » du sprint 28 (sacrifices, pièces offertes, pièges) sans
perdre l'espérance humaine Maia du tronçon 04. Constat : seuil 10 jamais atteint
(gain max 5,9 sur 174 candidats [n=4 parties]).

## Règle (décision Nico 2026-10-22)

Un candidat est admissible si l'**avantage clair** tient (`evidence is not None`, inchangé) ET :
- **ancienne règle** (tag `sprint-28`, `git show sprint-28:chess_coach/explosive.py`,
  `_admissible` + calcul de `trap` dans `_deepen`) : (perte ≤ 5, ou perte ≤ 15 si
  piège ≥ 10) ET (sacrifice ≥ 1 pion OU piège ≥ 10) ; piège = % de gain adverse après
  sa meilleure réponse − après la prise naturelle (`_natural_capture`) ;
- **OU** règle Maia : perte ≤ 15 ET E(candidat) ≥ E(meilleur) + **5** (`_GAIN_MIN` 10 → 5).

Seuil fixe : Maia reçoit déjà l'Elo adverse.

## Fichiers à toucher

### `chess_coach/explosive.py`
- Réintroduire le calcul `trap` (prise naturelle analysée en `root_moves=[capture]`, comme
  sprint 28) dans `_deepen` ; champ `trap: float = 0.0` sur `ExplosiveMove`.
- `_admissible` : règle hybride ci-dessus (garder les constantes `_WINDOW = 5`,
  `_TRAP_MIN = 10`).
- Classement entre candidats et positions (`score`) : garder le gain Maia
  (`expected − best_expected`) ; à égalité d'admissibilité c'est lui qui trie.
- Docstrings / commentaire d'en-tête mis à jour.

### `execution/routers/chess_router.py`
- `_explosive_lines` : si la règle Maia n'est pas satisfaite (gain < 5), ajouter une ligne
  « pari : face à un humain l'espérance n'est pas meilleure que le meilleur coup » pour
  que le LLM le présente comme une idée risquée. Consigne d (l. ~600) : une demi-phrase
  « idée risquée » quand cette ligne est présente.

## Tests
- Un test unitaire de `_admissible` : candidat « ancienne règle » (sacrifice 3, gain Maia 0)
  admis ; candidat gain Maia 6 sans sacrifice admis ; candidat gain 3 sans sacrifice ni
  piège refusé. Pas de test moteur réel supplémentaire.

## Hors-scope
- Pas de budget de temps, pas de changement des positions éligibles (35-75 %).
- Ne pas toucher `select_critical` (≤ 3 d en bonus inchangé).

## Critère de fin
`pytest tests/ -q` vert. Mesure (script libre, non commité) sur les 4 parties de
`run_live_retours_parties.txt` : nombre d'occasions trouvées par partie noté dans `00_etat.md`.
