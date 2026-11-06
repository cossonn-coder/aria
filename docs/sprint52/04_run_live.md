# Sprint 52 — Tronçon 04 : run live (exécuté par Nico)

Prérequis : tronçons 01-03 ✅, `sudo systemctl restart aria.service`.
Messages à envoyer : `docs/sprint52/04_run_live.txt` (copiables).
Journal : `sudo journalctl -u aria -f -o cat`.

## Étapes et critères observables

1. **Bilan** : envoyer une partie récente **jamais envoyée** (PGN chess.com avec en-têtes).
   - ligne `🎯 Précision : toi X % (ton Elo) · adversaire Y % (son Elo)` ;
   - **dernière ligne** du message : `🏅 Précision X % : ta Ne meilleure partie sur M` (M ≈ nombre de fiches + 1).
   - journal : `chess_game_write OK`, `chess_progression OK`, aucun `ERROR`.
2. **`/parties`** : la partie du jour la plus récente juste au-dessus des stats ; dernière ligne
   `Aujourd'hui : … · performance NNNN [n parties]`.
3. **`/ouvertures`** puis **`/ouvertures <ouverture de la partie>`** : ouverture la plus jouée en bas ;
   dernière ligne `Performance : NNNN [n parties] · 5 dernières : NNNN`.
4. **Échiquier** (`/board`) : coller le même PGN, « Charger ».
   - ligne `Précision : blancs X % (Elo) · noirs Y % (Elo)` ;
   - sous elle : `Précision X % : ta Ne meilleure partie sur M` et la performance dans l'ouverture ;
   - journal : `board_game plies=…`, aucun `warning` de lecture des fiches.

Succès : les 4 étapes conformes. Toute valeur surprenante (performance hors 1000-2200, rang incohérent)
est notée avec la ligne de journal.
