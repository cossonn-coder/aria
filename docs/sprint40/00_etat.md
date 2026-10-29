# Sprint 40 — état de conception

**Phase** : B figée (2026-10-29, OK de Nico) — prêt pour `/sprint-auto sprint 40`.
**Branche** : `feat/sprint40-metacommandes`.
**Cible** : #131 — métacommandes Telegram, toutes celles proposées à la clôture 39 :
`/help`, `/reboot`, `/status`, `/logs`, `/errors`, `/llm`, `/board`, `/again`,
`/intents`, `/parties`, `/oublie`.

## Audit

`audit_metacommandes.md` : aucun `CommandHandler` ; aucun filtre utilisateur (ALLOWED_USER_ID
lu seulement par `submit_text`) ; `Restart=on-failure` → sortie ≠ 0 = reboot sans sudo ; PTB 22.7
confirme les updates à l'arrêt (pas de boucle) ; bridge / LLMRouter / IntentEngine locaux au
kernel ; intents lisibles dans `~/.aria/intents.json` ; journal lisible sans sudo ; writer sans
suppression.

## Décisions arrêtées

- Cible = toutes les commandes proposées (Nico, 2026-10-29), « le plus de quality of life ».
- `/oublie` = marqueur de coupure réversible, pas de suppression (reco Claude, OK Nico).
- `/update` retiré : le code arrive déjà par les commits locaux, et un pull cassé laisserait
  ARIA en crash sans recours Telegram (reco Claude, OK Nico).
- Filtre `ALLOWED_USER_ID` sur messages, photos et commandes : « mon bot ne doit pas être
  public, c'est juste pour moi » (Nico).

## Recos de conception (Claude, figées avec l'OK)

- Module `interfaces/meta_commands.py` (une fonction par commande → texte), branché par des
  `CommandHandler` filtrés sur `ALLOWED_USER_ID` ; hors kernel, rien écrit en conversation.
- `/reboot` : réponse, fichier marqueur, `stop_running()`, sortie code 1 → systemd relance ;
  au démarrage (`post_init`), marqueur présent → « de retour » + suppression du marqueur.
- `/parties`, `/status` : instance `MempalaceBridge` dédiée construite dans `bot.py` ; comptage par
  wing = nouvelle méthode du bridge.
- `/llm` et `/errors` lus dans le journal ; `/intents` lu dans `~/.aria/intents.json`.
- `/board` : URL dans la config (`BOARD_URL`, défaut `http://192.168.1.124:5002`).
- `/help` + `set_my_commands` au démarrage (auto-complétion Telegram).

## Questions ouvertes

(aucune)

## Tronçons

- 01 socle, filtre utilisateur, `/help`, `/reboot`, `/board`, `/again` (`01_socle_reboot.md`) ✅
  (385 tests verts ; `_post_init` appelle `_remember_loop` ; métacommandes livrées par `_deliver`, hors `last_reply`)
- 02 consultations `/status`, `/logs`, `/errors`, `/llm`, `/intents`, `/parties` (`02_consultations.md`) ✅
  (393 tests verts ; lecture + texte pur par commande dans `meta_commands` ; `TelegramInterface(bridge=…)` ;
  `count_by_wing` dans le bridge ; libellés couleur / issue repris de `chess_coach.summary`)
- 03 `/oublie`, marqueur de coupure — **palace prod** (`03_oublie.md`) ✅
  (396 tests verts ; `write_conversation_reset` (avec `extra` écrasé, W4) ; coupure dans
  `load_conversation_history` au marqueur le plus récent, avant les n derniers ; aucun marqueur =
  comportement inchangé ; `/status` compte les marqueurs dans `aria_conversation`)
- 04 run live, Nico (`04_run_live.md`) ⏳

## Dettes

Visée : #131. Fermée par le filtre utilisateur : exposition du bot à tout compte Telegram
(constat d'audit, sans numéro).

## §REPRISE

Tronçons 01 (ca132e1), 02 (8c0cda7) et 03 (`/oublie`, non commité à la livraison du sous-agent)
implémentés. Prochaine étape : tronçon 04, run live par Nico (`04_run_live.md`).
Lire `CLAUDE.md`, ce fichier, le kickoff du tronçon.
