# Sprint 21 — tronçon 02 : run live (Nico)

Prérequis : tronçon 01 commité, `pytest tests/ -q` vert.

La coupure réseau se simule en bloquant l'IPv4 de `api.telegram.org`
(149.154.166.110 ; IPv6 déjà injoignable depuis la VM). `DROP` produit des
`ConnectTimeout`, comme les incidents réels du 2026-10-15.

Commandes (une ligne chacune) :

- couper : `sudo iptables -I OUTPUT -d 149.154.166.110 -j DROP`
- rétablir : `sudo iptables -D OUTPUT -d 149.154.166.110 -j DROP`
- logs (2e terminal) : `sudo journalctl -u aria -f -o cat`
- PID : `systemctl show -p MainPID aria`

## Scénario A — démarrage sans réseau (#62 crash)

1. `sudo systemctl stop aria` puis **couper**.
2. `sudo systemctl start aria` ; noter le PID.
3. Attendre ~40 s (au-delà de l'ancien crash à ~5 s + `RestartSec=10`).
4. **Rétablir**.
5. Envoyer « test démarrage ».

Attendu : pas de `Aborting.` ni de relance systemd ; même PID qu'en 2 ;
lignes de retry PTB pendant la coupure ; `telegram_update update_id=…
type=text` puis réponse reçue sur Telegram.

## Scénario B — envoi pendant une coupure (#62 réponse perdue)

1. Envoyer « il fait beau aujourd'hui » et **couper** immédiatement.
2. Attendre `pipeline done` dans les logs, puis la 1re ligne WARNING
   d'échec d'envoi (tentative 1/3).
3. **Rétablir** dans les ~5 s qui suivent.

Attendu : réponse reçue sur Telegram (éventuellement en double, accepté) ;
WARNING d'une ligne, aucune trace complète, aucune ligne
`No error handlers are registered`. Pendant la coupure, les erreurs de
polling apparaissent en `telegram error: …` sur une ligne.

## Scénario C — log de réception (#63)

Envoyer une photo sans légende. Attendu : une seule ligne
`telegram_update update_id=… message_id=… type=photo`, une seule ligne
`[VISION] … a répondu.`

## Critère de succès

- A, B, C conformes → #62 fermée ; #63 reste ouverte « instrumentée, à
  confirmer » (ne se reproduit pas sur commande) ; clôture du sprint.
- Si B échoue par retries épuisés (rétablissement trop tardif) : rejouer
  B, ce n'est pas un échec du code tant que les 3 WARNING sont propres.
- Toute trace complète restante ou un crash en A → `/conception`.

Ne pas oublier de **rétablir** en fin de session : `sudo iptables -L OUTPUT -n | grep 149.154.166.110` doit être vide.
