# Sprint 28 — tronçon 04 : run live (Nico)

Exécuté par Nico (Telegram + journalctl). Pas de sous-agent.

## Préparation

1. Vérifier dans le venv ARIA : `venv/bin/pip list | grep -E "^(chess|maia2) "` →
   `chess 1.11.2`, `maia2 0.10.0` ; poids présents dans `/home/nico/.cache/aria-maia/`.
2. `sudo systemctl restart aria.service`
3. Dans un autre terminal : `sudo journalctl -u aria -f -o cat | grep -E "maia_difficulty|chess_progression|chess_game_write|chess_analysis"`

## Messages à envoyer

Les 4 PGN sont dans `docs/sprint28/run_live_parties.txt` (copier un bloc par message,
dans l'ordre, attendre la réponse entre deux). Ce sont 4 parties déjà analysées : même
hash → leur fiche est **remplacée** par une fiche saison 1 (avec difficulté).

| # | Partie | Attendu |
|---|---|---|
| 1 | Falestinhurra (blancs, défaite 1307 vs 1352) | `saison 1 lancée`, ligne Global, 📖 Scotch Game |
| 2 | YouGotMyRook (blancs, victoire) | lignes de thèmes avec coup + difficulté ; Global monte |
| 3 | Mu7saad (noirs, défaite 1354 vs 1332) | Global baisse (défaite contre plus faible) |
| 4 | Dragonzee1952 (blancs, victoire) | 📖 Caro Kann Defense ; badge(s) possibles |

## Critères de succès (observables)

- journalctl : `maia_difficulty OK n=… duration=…` à chaque partie, durée ≤ 10 s ;
  `chess_progression OK games=<1,2,3,4>` ; aucun `chess_progression ERROR`.
- Telegram : le bloc 🎮 apparaît sous la réponse ; les coups cités existent dans la
  partie ; une défaite fait baisser Global ; les difficultés vont de ~900 (reprises) à ~2000.
- Ressenti RPG (jugement de Nico) : lisible, motivant, pas de chiffre absurde.
- Mémoire du service après la 1re partie : `systemctl show aria.service -p MemoryCurrent`
  (à relever, la VM a 4 Go).

## En cas d'échec

Noter l'horodatage, la partie, la ligne fautive ; ouvrir une dette ou un correctif
(conception).
