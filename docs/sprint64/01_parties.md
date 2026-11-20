# Sprint 64 — tronçon 01 : `/parties` et `/ouvertures` (tri, cadence, details)

Lire d'abord `CLAUDE.md`, `docs/sprint64/00_etat.md` (décisions arrêtées), `audit_parties.md`.

## Objectif

Trois changements de présentation, sans LLM, sans écriture mémoire, palace non touché :
1. **62-4 tri** des lignes d'ouvertures ;
2. **62-5 filtre de cadence** `rapide` / `blitz` ;
3. **62-6 `/parties` court par défaut**, sortie complète avec `details`.

## Fichiers (vérifiés au code, `main` @ `9ab136f`)

- `interfaces/meta_commands.py` : `parse_period_args` (l. 160), `parties_text` (l. 215),
  `_opening_stat_lines` (l. 259), `openings_text` (l. 268), `parties_opening_text`.
- `interfaces/telegram_interface.py` : `_cmd_parties` (l. 450), `_cmd_ouvertures` (l. 461),
  seuls callers de ces fonctions. Ils restent minces : lire les options, filtrer, appeler le texte.
- `tests/interfaces/test_meta_commands.py` : tests existants de `parties_text` (l. 57, 78, 201-218)
  et `parse_period_args` (l. 194) à adapter au nouveau comportement.

## Comportement attendu

### Arguments
`/parties` et `/ouvertures` acceptent, à n'importe quelle place, les mots (sans accent ni casse,
via `_plain`) `rapide`, `blitz` et — pour `/parties` seulement — `details`. Ils sont retirés
avant le découpage existant : dernier mot restant = période s'il en est une, reste = requête
d'ouverture. Exemples : `/parties blitz week`, `/parties details`, `/ouvertures rapide`,
`/parties evans blitz all`. Forme de retour libre (prolonger `parse_period_args` ou fonction
voisine), tant que les deux handlers l'utilisent.

### 62-4 Tri
`_opening_stat_lines` trie par : nombre de parties (desc), puis % de victoires (desc), puis
nombre de nulles (desc). `parties_text` affiche dans cet ordre ; `openings_text` garde
l'inversion `[::-1]` (la plus jouée en bas du message, Telegram affiche le bas).

### 62-5 Cadence
Fonction pure : `time_control` de la fiche (`"600"`, `"180+2"`, vide…) → `"rapide"`,
`"blitz"` ou `None`. Durée = base + 40 × incrément (règle chess.com) ; `< 600 s` → blitz,
`≥ 600 s` → rapide (pas de bullet/classique : aucune fiche, cf. audit §3 ; ne pas les inventer).
Vide ou illisible → `None`. Avec un mot de cadence, les fiches sont filtrées **avant** tout
(période, ouverture, stats) ; fiches `None` exclues. Sans mot de cadence : rien ne change.

### 62-6 `/parties` court / `details`
- **Sans `details`** (requête d'ouverture absente) : uniquement
  ```
  Aujourd'hui : 3 V, 1 D — 75 % · performance 1450 [4 parties]
  10 dernières : 6 V, 1 N, 3 D — 60 %
  ```
  1re ligne = bilan actuel de la période (libellé et performance inchangés). Si la période
  n'a aucune partie, 1re ligne = le message actuel de `_no_games_text`. 2e ligne = `_record`
  des 10 fiches les plus récentes (tri `_game_date_key`), toutes périodes, après filtre de
  cadence ; omise s'il n'y a aucune fiche. Moins de 10 fiches : libellé « N dernières ».
- **Avec `details`** : la sortie actuelle complète de `parties_text`, mais la ligne par partie
  s'affiche quelle que soit la période (plus seulement `day`), la plus ancienne d'abord.
- `/parties <ouverture>` : inchangé (rapport d'ouverture), seul le filtre de cadence s'applique.

## Tests à ajouter / adapter (cas nominal)
- Tri : deux ouvertures à égalité de parties et de % → la plus de nulles d'abord.
- Cadence : `"600"`, `"180+2"`, `"300+3"`, `""` → rapide, blitz, blitz, None.
- Arguments : `["evans", "blitz", "week"]` → requête `evans`, cadence blitz, période week ; `details` repéré.
- `/parties` court : deux lignes attendues ; `details` : lignes par partie sur `week`.
- Adapter les tests existants qui figent l'ancienne sortie de `parties_text`.

## Hors scope
- Aucun lien cliquable, aucun bouton (62-3, étape 4).
- Ne pas toucher `opening_report_text` ni `/ouvertures <nom>` hors filtre de cadence.
- Pas de bullet / classique, pas de nouvelle métadonnée de fiche, pas d'écriture.
- Ne pas modifier l'aide `COMMANDS` au-delà de mentionner `rapide|blitz` et `details`.

## Critère de fin
`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` : tronçon 01 ✅ + §REPRISE.
