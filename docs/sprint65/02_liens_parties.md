# Sprint 65 — tronçon 02 : parties cliquables dans `/parties` et `/ouvertures <nom>`

À lire avant : `CLAUDE.md`, `docs/sprint65/00_etat.md`, `docs/sprint65/audit_parties_echiquier.md`
(§1 sorties, §5 mécanismes). Suppose le tronçon 01 livré (l'échiquier ouvre `start_param`).

## Objectif

Chaque ligne qui nomme une partie devient un lien qui ouvre l'échiquier ARIA dans Telegram
sur cette partie (62-3). Mécanisme arbitré par Nico : **lien Mini App principale**
`https://t.me/<bot_username>?startapp=<hash>` (doc Telegram : le paramètre arrive dans
`start_param` / `tgWebAppStartParam`). `hash` = id de fiche sans `chess_game_`
(16 hex, compatible `startapp`). Prérequis hors code : Mini App principale configurée dans
BotFather (fait par Nico avant le run live).

## Lignes concernées (`interfaces/meta_commands.py`)

- `parties_text` avec `details` : la ligne par partie (`:221-229`).
- `_ranking_lines` (`:236`) via `_ranking_line` : classement 🏆/📉 ou « Par précision »,
  dans `/parties details` et `opening_report_text` (`/parties <ouv.>`, `/ouvertures <nom>`).
- Rien d'autre (bilans, stats d'ouvertures : pas de partie nommée).

## Comportement

- Les fonctions texte restent pures : paramètre optionnel `link` (fiche → URL, ou `None`).
  `link=None` → sortie **inchangée** (texte brut, tests existants verts).
  Avec `link` → sortie HTML Telegram : tout le texte échappé (`html.escape(…, quote=False)` :
  `<`, `>`, `&`), chaque ligne de partie entourée de `<a href="URL">…</a>`.
  Le paramètre traverse `parties_text`, `parties_opening_text`, `opening_report_text`,
  `_ranking_lines` seulement là où c'est nécessaire.
- `interfaces/telegram_interface.py` `_cmd_parties` (`:450`) et `_cmd_ouvertures` (`:462`) :
  passent `link = lambda g: f"https://t.me/{self.app.bot.username}?startapp={g['id'].removeprefix('chess_game_')}"`
  (ou équivalent) et envoient en `parse_mode="HTML"`, aperçu de lien désactivé.
  `_deliver` coupe à 4096 caractères bruts au milieu d'une balise possible : l'envoi HTML
  découpe **par lignes** (morceaux ≤ 4096). Garder `_send_with_retry`. `_deliver` texte brut
  inchangé pour les autres commandes.
- Une sortie sans ligne de partie (bilan court, `/ouvertures` sans nom) peut partir en HTML
  aussi (texte échappé) : aucune différence visible.

## Tests (cas nominal)

- `tests/interfaces/test_meta_commands.py` : `parties_text(..., details=True, link=…)` →
  ligne de partie dans `<a href="…startapp=<hash>">`, un pseudo avec `&` échappé ;
  classement idem ; sans `link`, sortie identique à aujourd'hui (tests existants).
- `tests/interfaces/test_telegram_interface.py` : `/parties details` → `send_message` appelé
  avec `parse_mode="HTML"` et un lien `t.me/<username>?startapp=`.

## Hors-scope (ne PAS faire)

- Boutons inline, liens web directs vers `BOARD_URL`.
- Dettes 64-2 (« 1 dernières »), 64-1 (cadence), 65-1 (FEN).
- Toute modification de l'échiquier (tronçon 01) ou de la mémoire.

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests verts.
