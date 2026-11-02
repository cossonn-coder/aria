# Sprint 46 — tronçon 05 : run live (exécuté par Nico)

Les PGN sont dans `docs/sprint46/run_live_parties.txt`. Ces parties viennent de tes fiches : les parties 1 et 2 remplacent
leur fiche (elles passent en dernier dans la chronologie, #97). La partie 3 recrée au bon camp une fiche supprimée.

## 1. Migration du palace (irréversible hors sauvegarde)

```
sudo systemctl stop aria
cd ~/Nextcloud/projects/aria && venv/bin/python scripts/migrate_chess_rooms.py
```
Vérifier : 9 suppressions contre `La_Bagouze` ou `TardoScoped`, aucune non reconnue, puis :
```
venv/bin/python scripts/migrate_chess_rooms.py --apply
sudo systemctl start aria
```
**Succès :** le script finit sans écart et affiche le chemin de la sauvegarde. Retour arrière : service arrêté,
remettre cette sauvegarde à la place de `~/.mempalace/palace`.

## 2. Parties

Surveiller : `sudo journalctl -u aria -f -o cat | grep -E "chess_analysis|chess_game_write|chess_progression"`

| Envoi | Attendu au journal | Attendu sur Telegram |
|---|---|---|
| Partie 1 | `source=header nico=white`, `critical` : ≤ 4, que des `a:` / `b:`, aucun coup < 4 | 4 miniatures de tes erreurs, flèche bleue sur ton coup, verte sur le meilleur |
| Partie 2 | `source=header nico=white`, l'erreur `a:` ou `b:`, puis `d:`, puis `e:` / `c:`, ≤ 4 | Complétées avec explosifs puis beaux coups, flèche bleue seule si ton coup est le meilleur |
| Partie 3 | `source=header nico=black` | Échiquier côté noirs, défaite, adversaire « Adversaire » |

Pour chacune, sur Telegram :
- chaque légende porte un « Plan : » concret, avec des colonnes, pions et rois vrais dans la position ;
- le bloc Progression montre `Ouverture … · Milieu de jeu … · Finale …` ;
- la ligne `📖` donne le nom de l'ouverture et un total V / N / D, sauf pour la toute première partie de saison.

## 3. Statistiques

`/ouvertures` : une ligne par ouverture et par couleur, tes ouvertures sous leur libellé (Göring Gambit, Dutch Defense…),
puis le nombre de fiches à issue inconnue. Puis `/parties` : noms complets, sans « ouverture inconnue ».

## Succès

Tout ce qui précède, plus ton avis sur la qualité des plans : c'est le seul point que les tests ne jugent pas.
Si le plan invente des faits, note la position : ça part en correctif ou en dette, selon ton choix.
