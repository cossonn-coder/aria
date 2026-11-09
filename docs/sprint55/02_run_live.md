# Sprint 55 — Tronçon 02 : run live (Nico)

## Préparation
`sudo systemctl restart aria.service`, puis `sudo journalctl -u aria -f -o cat`.

## À envoyer
Le PGN d'une partie jouée **aujourd'hui**, dans une ouverture déjà jouée avec la même couleur.
L'idéal est un jour où au moins une autre partie est déjà envoyée.

## Critères de succès (dernier message du bilan)
1. Dernière ligne : `🏅 Précision X % : Ne sur T · Ne sur J aujourd'hui · Ne sur O en <ouverture> (<couleur>)`.
   - T est cohérent avec l'ancien total (≈ 207).
   - J est égal au nombre de parties du jour que donne `/parties`.
   - O est égal au total V + N + D de la ligne 📖 juste au-dessus.
2. La légende se termine par `🟢 meilleur coup du moteur`, sans « (toi / adversaire) ».
3. journalctl : `chess_router OK` et `chess_progression OK`, sans ERROR.

Avec la 1re partie du jour, le segment « aujourd'hui » est absent : c'est le comportement voulu.
