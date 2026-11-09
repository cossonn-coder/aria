# Sprint 53 — tronçon 02 : périodes et 5 meilleures / 5 pires parties

Lire d'abord : `CLAUDE.md`, `docs/sprint53/00_etat.md` (décisions du 2026-11-09).

## Objectif

1. `/parties` et `/ouvertures` acceptent une **période** : `/parties month`, `/ouvertures goring week`,
   `/parties goring semaine`…
2. Toutes les réponses `/parties` et `/ouvertures` montrent les **5 meilleures et 5 pires parties
   par précision** de la sélection, pour que Nico voie quelles ouvertures reviennent dans ses
   bonnes et mauvaises parties.

## Fichiers à toucher

- `interfaces/meta_commands.py` : `parties_text`, `parties_opening_text`, `openings_text`,
  `opening_report_text`, `_game_day`, `COMMANDS` (descriptions `parties` et `ouvertures`).
- `interfaces/telegram_interface.py` : `_cmd_parties` et `_cmd_ouvertures` (l.445-461), qui
  joignent aujourd'hui tous les arguments en une requête d'ouverture.
- `tests/interfaces/test_meta_commands.py`.

## Comportement attendu

### Période

- Mots acceptés (insensibles à la casse et aux accents, `_plain` existe) : `day`/`jour`,
  `week`/`semaine`, `month`/`mois`, `year`/`année`, `all`/`tout`.
- Fenêtre **glissante finissant aujourd'hui** : jour = aujourd'hui ; semaine = 7 derniers jours
  (aujourd'hui compris) ; mois = 30 ; année = 365 ; tout = aucun filtre. Jour d'une fiche :
  `_game_day` (date du PGN, sinon jour d'analyse).
- Lecture des arguments : si le **dernier** mot est une période, c'est la période ; le reste
  (s'il en reste) est la requête d'ouverture. Sinon tout est requête, comme aujourd'hui.
- Défauts inchangés : `/parties` = jour, `/ouvertures` = tout.
- `/parties <période>` (période > jour) : **plus de ligne par partie** ; stats d'ouvertures, puis
  classement, puis la ligne de bilan + performance de la période en bas (aujourd'hui
  « Aujourd'hui : … » ; libellé de la période, ex. « 7 derniers jours : … »).
- `/parties` (jour) garde sa liste par partie.
- `/parties <ouverture> [période]` et `/ouvertures <ouverture> [période]` : rapport
  `opening_report_text` sur les fiches de la période.
- `/ouvertures <période>` : `openings_text` sur les fiches de la période.
- Aucune fiche dans la période : message court nommant la période (ex. « Aucune partie sur les
  7 derniers jours. »), en gardant `NO_PARTIES` pour le jour.
- `/help` : descriptions de `parties` et `ouvertures` mentionnant la période (le test
  `test_help_lists_every_command` suit `COMMANDS`).

### Classement par précision

- Fiches classées : celles qui ont `accuracy` non nul, dans la sélection affichée (jour/période,
  ouverture éventuelle, les deux couleurs). Aucune fiche classée → aucune ligne (les tests
  existants, sans `accuracy`, restent verts).
- Plus de 5 classées : `🏆 5 meilleures :` puis 5 lignes, `📉 5 pires :` puis jusqu'à 5 lignes,
  **sans reprendre une partie déjà parmi les meilleures** (de 6 à 9 parties, la liste des pires est
  plus courte). 5 ou moins : une seule liste `Par précision :`.
- Une ligne par partie :
  `92 % · Göring Gambit (blancs) · contre luismota32 (1340) · victoire · 2026-11-06`
  (précision arrondie, groupe d'ouverture `game_opening_group`, couleur `_COLOR_FR`, adversaire
  et Elo s'il existe, issue `_OUTCOME_FR`, jour `_game_day`).
- Place : juste **au-dessus des lignes générales du bas** (bilan / performance) dans `/parties` et
  `/ouvertures` ; pour un rapport d'ouverture (`opening_report_text`), **au-dessus des sections
  par couleur** (le bas du message reste la couleur la plus jouée). Règle sprint 52 : les infos
  générales restent en bas.

## Tests (cas nominaux)

- Lecture des arguments : `["goring", "week"]` → requête « goring », semaine ; `["month"]` →
  pas de requête, mois ; `["goring"]` → requête seule.
- `/parties` sur une semaine (date `today` injectée, comme les tests existants) : pas de ligne
  par partie, fiche hors fenêtre exclue, bilan de la période en bas.
- Classement : 7 fiches avec `accuracy` → 5 meilleures + 2 pires, ordre correct, place au-dessus
  du bilan ; 3 fiches → une liste `Par précision :`.
- `pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Noms d'ouverture en français (`hollandaise`, dette #169).
- `/parties <ouverture>` sans partie (#191), couplage `board_interface` → `meta_commands` (#204).
- Classement ou période sur l'échiquier web, dans le bilan d'analyse, ou toute lecture mémoire
  hors `bridge.load_chess_games` déjà appelé par les handlers.

## Critère de fin

Tests ajoutés verts, `pytest tests/ -q` vert. Rendu Telegram : run live (tronçon 03).
