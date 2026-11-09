# Sprint 53 — état de conception

**Phase** : B figée (2026-11-09) — prêt pour `/sprint-auto sprint 53`.
**Branche** : `feat/sprint53-recits-periodes` (créée depuis `main` le 2026-11-09).

## Cible

1. Échecs : récits plus justes — le LLM raconte mal des coups joués (#187) et invente des faits résiduels (#92).
2. `/parties` et `/ouvertures` filtrés par période (`/ouvertures goring week`, `/parties month`), ajout de Nico,
   avec 5 meilleures / 5 pires parties par précision.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---------|-------|------|
| 01 | `01_faits_coups_cites.md` | Bloc enrichi : suite jouée sur chaque position, faits de l'erreur adverse (tournant), coups du déroulé, consigne étendue | ✅ |
| 02 | `02_periodes_classement.md` | Périodes sur `/parties` et `/ouvertures`, 🏆 5 meilleures / 📉 5 pires par précision | ✅ |
| 03 | `03_run_live.md` (+ `03_run_live.txt`) | Run live (Nico) : 2 parties neuves + commandes | ⏳ |

## Décisions arrêtées

- 2026-11-09 — Cible : récits d'échecs plus justes (#187, #92), choisie par Nico.
- 2026-11-09 — Faits pour **tous les coups cités** : coup joué de chaque position commentée
  (toutes sortes + réflexions longues) suivi de la réponse adverse **jouée dans la partie** ;
  erreur adverse d'un tournant ; coups du déroulé (tournants, pire coup). Raison : la réponse
  jouée seule dit si la pièce est reprise (cas Qxf1+). Texte envoyé au LLM seulement, rien de
  changé dans ce que Nico voit directement.
- 2026-11-09 — Faits inventés (#92) : pas de correction à l'aveugle (exemples d'avant sprint 50),
  relevé au run live sur 2 parties.
- 2026-11-09 — Consigne étendue à toutes les positions et au Bilan : pièce prise / échangée /
  reprise / épargnée seulement si une ligne de faits le montre.
- 2026-11-09 — Ajout de Nico au sprint : période sur `/parties` et `/ouvertures`
  (exemples : `/ouvertures goring week`, `/parties month`). Code lu : `interfaces/meta_commands.py`
  (`parties_text`, `parties_opening_text`, `openings_text`, `opening_report_text`, `_game_day`),
  handlers `interfaces/telegram_interface.py:445-461` (args joints en une requête d'ouverture).
- 2026-11-09 — Run live : Nico jouera 2 parties neuves.
- 2026-11-09 — Période = fenêtre glissante finissant aujourd'hui : jour (aujourd'hui), semaine (7 j),
  mois (30 j), année (365 j), tout. Mots acceptés, anglais et français : day/jour, week/semaine,
  month/mois, year/année, all/tout. Défauts inchangés : `/parties` = jour, `/ouvertures` = tout.
- 2026-11-09 — Sur une période plus longue que le jour, `/parties` ne liste plus les parties :
  statistiques seulement (le mois dépasse 4096 car.).
- 2026-11-09 — **Top 5 / flop 5 par précision** (champ `accuracy` des fiches ; sans précision =
  non classée) sur **toutes** les réponses `/parties` et `/ouvertures`, limité à la sélection :
  `/ouvertures goring` → parties de cette ouverture ; `/parties week` → parties de la semaine.
  But de Nico : voir quelles ouvertures reviennent dans les bonnes et mauvaises parties.
- 2026-11-09 — Détails posés en conception (OK de Nico sur le découpage) : classement juste
  au-dessus des lignes générales du bas, au-dessus des sections par couleur pour un rapport
  d'ouverture ; ≤ 5 parties classées → une liste « Par précision » ; de 6 à 9, les pires ne
  reprennent pas les meilleures.

## Questions ouvertes

(aucune)

## Dettes

Visées par le sprint : #187 (à fermer si le run live le confirme), #92 (relevé au run live).
Aucune nouvelle dette à ce stade.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_recits.md`, puis le kickoff du tronçon en cours.
Tronçon 01 fait (2026-11-09) : `story_plies` public dans `chess_coach/summary.py` (utilisé par
`story_line`), helper `_played_facts` dans `chess_router.py` ; 555 tests verts. Dans
`tests/execution/test_chess_router.py`, une fixture autouse neutralise `_played_facts` (coups
factices illégaux, ex. 17...Ng4+) ; le test du tronçon remet la vraie fonction.
Tronçon 02 fait (2026-11-09) : `interfaces/meta_commands.py` — `parse_period_args` (dernier mot =
période), `_in_period`, `_ranking_lines` ; paramètre `period` sur `parties_text`,
`parties_opening_text`, `openings_text` ; classement en tête de `opening_report_text`. Handlers
`_cmd_parties` / `_cmd_ouvertures` : requête + période (défauts jour / tout) ; `/ouvertures <nom>`
passe désormais par `parties_opening_text` (période « all » = aucun filtre). Dans `openings_text`,
le classement est placé au-dessus de « Issue inconnue » et de la performance. 559 tests verts.
Prochaine étape : run live 03 par Nico.
