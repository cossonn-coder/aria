# Sprint 52 — Tronçon 02 : performance Elo dans `/parties` et `/ouvertures`, infos en bas

Lire d'abord `CLAUDE.md` et `docs/sprint52/00_etat.md`. Prérequis : tronçon 01 (`chess_coach/level.py`,
`performance(games)`).

## Règle de Nico

Telegram défile en bas du message : **les informations générales vont en bas**, le détail au-dessus.

## Objectif (fichier `interfaces/meta_commands.py`)

1. `parties_text` (parties du jour) — nouvel ordre :
   - lignes de parties **de la plus ancienne à la plus récente** (aujourd'hui : `reversed(games)`, la plus
     récente d'abord ; `games` arrive trié par timestamp croissant) ;
   - puis les lignes de stats d'ouvertures (`_opening_stat_lines`), si présentes, séparées par une ligne vide ;
   - en **dernière** ligne : `Aujourd'hui : 3 V, 1 D — 75 % · performance 1580 [4 parties]`.
     Le suffixe `· performance …` n'apparaît que si `performance(games)` n'est pas None ; le nombre entre
     crochets est celui des parties comptées par `performance`.
2. `_color_section` (`/ouvertures <nom>` et `/parties <ouverture>`) — dans chaque section :
   - lignes de détail d'abord (coups par partie, Elo adverse moyen, % de gain aux coups 10 / 20, 5 dernières) ;
   - en bas : la ligne titre actuelle `Groupe (couleur) : record [n parties]`, puis
     `Performance : 1420 [12 parties] · 5 dernières : 1510` (5 dernières = mêmes 5 parties que la ligne
     « 5 dernières » existante, tri `_game_date_key` ; segment omis si la section a ≤ 5 parties ou si sa
     performance est None ; ligne omise si la performance totale est None).
   - `opening_report_text` : sections de la **moins jouée à la plus jouée** (la plus jouée en bas).
3. `openings_text` (`/ouvertures` sans argument) : lignes d'ouvertures de la moins jouée à la plus jouée,
   puis la ligne « Issue inconnue… », puis en **dernière** ligne la performance globale de toutes les fiches :
   `Performance : 1580 [140 parties] · 5 dernières : 1610` (5 dernières par `_game_date_key`).

## Fichiers

- `interfaces/meta_commands.py`
- `tests/interfaces/test_meta_commands.py` : adapter les tests d'ordre existants (l. 57, 92, 121, 138,
  175 au moment de l'audit) et ajouter le cas nominal de chaque ligne de performance.

## Hors scope (ne PAS faire)

- Pas de performance par ligne de partie (sans objet sur une partie).
- Pas de correction de #169 (noms anglais) ni #191 (message trompeur de `/parties <ouverture>`).
- Ne pas toucher `telegram_interface.py` (les handlers appellent déjà ces fonctions).

## Critère de fin

`pytest tests/ -q` vert.
