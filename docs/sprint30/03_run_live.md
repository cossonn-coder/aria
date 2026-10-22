# Tronçon 03 — run live (Nico)

## Préparation (une ligne par commande)

1. `sudo systemctl stop aria.service`
2. `cd ~/Nextcloud/projects/aria && ./venv/bin/python scripts/mempalace_sync_threshold.py`
   → attendu : sauvegarde créée, pickle présent, N dossiers `.drift-*` supprimés.
3. `sudo systemctl start aria.service`
4. Dans un autre terminal : `sudo journalctl -u aria -f -o cat`

## Messages Telegram

1. Envoyer une partie (PGN de `docs/sprint29/run_live_11_parties.txt`, la 1re).
   - « ARIA écrit… » visible en haut de la conversation pendant l'analyse ;
   - après ~10 s, **un seul** message « ⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes. » ;
   - puis images + texte comme au sprint 29.
2. Pendant l'analyse d'une 2e partie, envoyer `salut`.
   - journalctl : la ligne `telegram_update … type=text` du `salut` apparaît **tout de suite**,
     pas à la fin de l'analyse ;
   - la réponse au `salut` arrive après celle de l'analyse.
3. Envoyer `salut` seul (hors analyse) : réponse sans message ⏳.

## Quarantaine (#105)

Au moins 5 min après le dernier message : `sudo systemctl restart aria.service`, puis envoyer
`salut`. journalctl : **aucune** ligne `Quarantined corrupt HNSW segment`.
`ls ~/.mempalace/palace | grep -c drift` → 0.

## Critère de succès

Les 4 points ci-dessus OK. #104 (photo en échec) n'est pas provocable en live : couvert par
les tests seuls.
