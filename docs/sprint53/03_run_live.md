# Sprint 53 — tronçon 03 : run live (Nico)

Exécuté par Nico, après les tronçons 01 et 02 commités sur `feat/sprint53-recits-periodes`
et `sudo systemctl restart aria.service`. Messages à copier : `docs/sprint53/03_run_live.txt`.

Journal à suivre : `sudo journalctl -u aria -f -o cat` (lignes `chess_router OK`,
`meta_command name=parties` / `name=ouvertures`, aucune `ERROR`).

## Partie A — récits (tronçon 01)

1. Jouer 2 parties neuves (jamais envoyées : un doublon est refusé) et coller chaque PGN.
2. Pour chaque position commentée et pour le Bilan, relever toute affirmation de prise,
   d'échange, de reprise ou de pièce épargnée, et la vérifier sur l'échiquier.

Succès : aucune prise / échange / reprise affirmé à tort ; en particulier, une prise de Nico
sans reprise adverse n'est jamais racontée comme un échange.
Relevé #92 : nombre d'entrées avec un fait inventé (coup, pièce, menace, mat) sur le total des
entrées des 2 parties, à comparer aux 3/21 d'avant le sprint 50.

## Partie B — périodes et classement (tronçon 02)

Envoyer, dans l'ordre : `/parties`, `/parties week`, `/parties month`, `/parties semaine`,
`/ouvertures`, `/ouvertures goring`, `/ouvertures goring week`, `/parties goring mois`.

Succès :
- `/parties` (jour) : liste des parties du jour, classement, bilan du jour en bas.
- `/parties week` / `month` / `semaine` : aucune ligne par partie, stats d'ouvertures,
  `🏆 5 meilleures` / `📉 5 pires` (précision · ouverture · couleur · adversaire · issue · date),
  bilan + performance de la période en bas ; `week` et `semaine` identiques.
- `/ouvertures` : classement sur toutes les parties, au-dessus de la performance globale.
- `/ouvertures goring` : classement des seules parties du Göring, au-dessus des sections.
- `/ouvertures goring week`, `/parties goring mois` : rapport du Göring limité à la période.
- Aucun message coupé, aucune `ERROR` au journal.
