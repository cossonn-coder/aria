# Étude de faisabilité : relier ARIA aux applications du smartphone

> **Reportée par Nico le 2026-11-02, rien d'implémenté, sprint non ouvert** (dette #165 et suivantes). Voir « Reprise » en fin de document.

> **Mis à jour après arbitrage de Nico : tout passe par la suite Nextcloud, mail compris.** Le §9 prime sur le tableau du §1 et le §4 pour le mail et les notes.

Date : 2026-11-02. Base : `main` à `de6fa76` (tag `sprint-46`). Aucun code modifié.
Statut des constats : **[code]** lu ou exécuté sur la VM, **[doc]** documentation officielle lue,
**[secondaire]** blogs/forums, **[connaissance]** de mémoire, non revérifié, **[à tester]** seul un essai sur le téléphone tranche.

## 1. Verdict

Faisable, mais pas sous la forme « Telegram pilote les applications ». Un bot Telegram n'a aucune prise
sur les autres applications du téléphone : l'API des bots parle à Telegram, et le champ `url` d'un bouton
n'admet que « HTTP or tg:// URL » [doc]. Donc pas de bouton `mailto:` ni d'intent Android.

La bonne voie : **ARIA agit sur le service derrière l'application** (la boîte Gmail, le serveur Nextcloud),
et l'application du téléphone affiche le résultat par sa propre synchronisation. Le téléphone n'a alors
rien à installer et peut être éteint.

| Besoin | Faisable ? | Par où | Ce qu'il faut |
|---|---|---|---|
| Envoyer un mail | Oui | SMTP Gmail (bibliothèque standard Python) | Mot de passe d'application Google, donc validation en 2 étapes active |
| Note | Oui, si l'appli est Nextcloud Notes | Fichier `.md` dans `~/Nextcloud/Notes` | Rien côté secret. Délai : timer de 5 min côté VM, plus la synchro de l'appli |
| Liste (courses…) | Oui, même chemin | Note à cases `- [ ]`, ou Nextcloud Tasks (CalDAV) | Rien pour la note ; dépendance `caldav` + mot de passe d'application pour Tasks |
| Google Keep | **Non** | API réservée à Google Workspace, comptes personnels exclus [doc] | — |
| Agenda | Oui | CalDAV Nextcloud (`calendar` présent dans les capacités du serveur [code]) | Dépendance `caldav`, mot de passe d'application |
| SMS, alarme, WhatsApp, appli quelconque | Oui mais fragile | Pilotage du téléphone (§3, voie 3) | Tasker sur le téléphone, joignable par Tailscale |
| Rappel à une heure donnée | Autre sujet | Aucun planificateur dans ARIA aujourd'hui [code] | Message Telegram programmé ; sprint à part |

## 2. Ce qui existe déjà

- **Infrastructure** [code] : VM `vdebiania` et téléphone `redmi-note-11s` (Android) sur le même tailnet
  (`100.100.116.34`). `tailscale serve` expose l'échiquier en HTTPS, tailnet seulement.
- **Nextcloud** [code] : `https://lemineur.ovh/nextcloud`, version 32.0.5, répond. Synchro VM par
  `nextcloud-sync.timer` toutes les 5 min (`nextcloudcmd`). `~/Nextcloud/Notes` existe, avec un seul
  fichier daté du 2026-04-02. Capacités visibles sans connexion : `calendar`, `cookbook`, `cospend`,
  `spreed`… Présence des applications : voir §9, établie ensuite avec une application témoin.
- **Aucune intégration mail, CalDAV ou Tasker** [code] : grep vide hors `config.py` (clé Gemini).
  `adb` et `kdeconnect-cli` absents de la VM.
- **Mini App** [code] : seul bouton existant (`/board`, `WebAppInfo`). Aucun `CallbackQueryHandler`,
  aucun bouton de réponse.

## 3. Les trois voies

1. **Côté serveur** (recommandée) : voir tableau. Pour mail, notes et listes, aucune dépendance au téléphone.
2. **Brouillon à un geste** : ARIA envoie un lien `https://mail.google.com/mail/?view=cm&to=…&su=…&body=…`
   que tu touches pour ouvrir le mail prérempli. Aucun secret. Mais lien `http(s)` seulement, ouverture
   probable dans le navigateur plutôt que dans l'appli, longueur limitée [à tester]. `openLink` d'une
   Mini App ouvre un navigateur externe, et la doc ne dit rien de `mailto:` [doc].
   Variante [connaissance] : déposer le brouillon dans le dossier Brouillons de Gmail via IMAP, avec le même
   mot de passe d'application ; tu le retrouves dans l'appli Gmail et tu l'envoies toi-même.
3. **Pilotage du téléphone** : l'événement « HTTP Request » de Tasker fait du téléphone un petit serveur
   [doc], joignable par Tailscale. Ouvre la porte à tout (SMS, alarme, n'importe quelle appli). Coût : Tasker
   à configurer sur le téléphone, panne dès qu'il est éteint ou que MIUI tue l'appli en arrière-plan
   [connaissance, à tester sur ce Redmi]. À réserver à ce que les voies 1 et 2 ne couvrent pas.

## 4. Mail : points d'attention

- **Authentification.** SMTP + mot de passe d'application : encore accepté par `smtp.gmail.com` en mai 2026
  [secondaire, pas de page Google lue]. Ce mot de passe donne accès à toute la boîte [connaissance].
  L'alternative OAuth (scope limité à l'envoi) demande un projet Google Cloud, et le jeton expire après
  7 jours tant que l'application reste en mode test [connaissance, la recherche n'a rien confirmé].
  Pour un outil mono-utilisateur, le mot de passe d'application est le moins exigeant.
- **Destinataire.** « Envoie à Paul » suppose un carnet d'adresses, qui n'existe pas. Le moins cher : adresse
  écrite dans le message, ou petite table d'alias en configuration. La lecture des contacts Google est hors sujet.
- **Irréversible.** Un mail parti ne revient pas : confirmation obligatoire, brouillon affiché en entier.

## 5. Écarts entre le sujet et le code

1. **« Génère une note » part en génération d'image** [code, exécuté]. `_TEXT_GENERATION_KEYWORDS` contient
   `génère` en sous-chaîne : `génère une note avec mes courses` et `génère une liste de courses` donnent
   `detect_image_generation_intent = True`. La formulation même du sujet déclencherait une image.
2. **Un mail contenant un lien part en lecture de page** [code, exécuté]. `envoie un mail à Paul avec ce lien
   https://example.org` donne `detect_url` vrai, et la règle URL passe avant tout sauf le PGN.
   → La détection des actions doit se placer **juste après le PGN (règle 1b), avant la règle URL**.
3. **L'échiquier est une porte ouverte sur « message de Nico »** [code]. `POST /send` sur `0.0.0.0:5002`, sans
   authentification ni contrôle que le contenu est un PGN, remet n'importe quel texte à `submit_text`, traité
   comme un message de toi. Aujourd'hui sans gravité. Avec les actions, deux requêtes (`envoie un mail…` puis
   `oui`) depuis le réseau local ou le tailnet enverraient un mail en ton nom.
   → **Prérequis du sprint** : n'accepter sur `/send` que ce que `detect_pgn` reconnaît.
4. **Le contrat de sortie ne connaît pas les boutons** [code]. Les routers rendent texte ou images (règle 4),
   `_normalize` ne transmet pas de `reply_markup`, aucun `CallbackQueryHandler`. Un bouton « Envoyer » toucherait
   la règle 4, le kernel et l'interface. Le patron déjà en place suffit : ARIA pose une phrase-marqueur et
   `detect_doc_reread` reconnaît le « oui » dans le dernier tour (`REREAD_PROPOSAL`, `_URL_RESUME_EXACT`).
5. **Le « oui » dépend de l'historique, que le router doit écrire lui-même** [code]. `write_conversation_turn`
   n'est appelé que par `llm_router` et `image_router`. Un router d'actions qui ne délègue pas au pipeline texte
   doit l'appeler (via `memory/writer.py`, règle 1), sinon le marqueur n'existe pas au tour suivant.
6. **Aujourd'hui, ARIA ne sait pas qu'elle ne sait pas envoyer de mail** [code] : ni le classifier ni `soul.md`
   n'en parlent, la demande part au LLM. Une réponse « c'est envoyé » est possible ; non observée.

## 6. Architecture proposée (si le sprint est lancé)

```
message → règle « action explicite » (après PGN, avant URL) → opération APP_ACTION
        → actions_router : extraction des champs par LLM → note/liste écrite, ou brouillon de mail + « oui »
```

- **Règles inviolables tenues** : une ligne dans `_ROUTING_TABLE` + un router (le kernel ne décide rien),
  sortie `{"text": …}`, historique via `memory/writer.py`. Fichier de note et SMTP ne sont pas de la mémoire
  ARIA : ils ne passent ni par le writer ni par le bridge. **Palace prod non touché** (hors tours de conversation
  habituels) : calibrage faible.
- **Déclenchement sur phrases explicites uniquement**, comme `WEB_RESEARCH` au sprint 45 : ni classifier LLM,
  ni cache (`_search_cache` rejoue une opération à similarité ≥ 0,92 : « mail à Paul » et « mail à Pierre » sont
  voisins). Seul le texte brut de ton message déclenche ; une page web ou un document lu ne peut pas provoquer
  d'action, même s'il contient des instructions.
- **Le LLM n'extrait que les champs** (destinataire, objet, corps) de ton propre message, et le résultat passe
  sous tes yeux avant envoi. Le texte du mail transite chez les fournisseurs LLM, comme tout message aujourd'hui.

## 7. Ce que le run live devra démontrer

- `note : acheter du lait` → réponse « noté » sur Telegram ; la note visible dans l'appli du téléphone après synchro.
- `ajoute du lait à ma liste de courses` → case ajoutée à la bonne note, visible sur le téléphone.
- `envoie un mail à <adresse> pour dire…` → brouillon affiché, rien ne part ; `oui` → mail reçu, présent dans
  « Envoyés » de Gmail ; `journalctl` montre l'opération et l'envoi.
- Un autre mot que `oui` → rien ne part.
- `POST /send` avec un texte non PGN → refusé, ARIA ne réagit pas.

## 8. Dettes adjacentes (à arbitrer, hors sprint)

- Mot de passe Nextcloud **en clair** dans `~/.config/systemd/user/nextcloud-sync.service`.
- `génère` trop large : `génère un plan` part aussi en image, indépendamment de ce sujet (même sous-chaîne).
- Risque de conflit de synchro si une note est modifiée sur le téléphone et par ARIA dans la fenêtre de 5 min
  (fichier de conflit Nextcloud, [connaissance]). Acceptable au départ, à observer.

## 9. Suite Nextcloud : ce que change l'arbitrage

Sondage sans identifiants [code], comparé à une application témoin inexistante (page 404, OCS 404) :

| Application | Page | Conclusion |
|---|---|---|
| Notes | 401 | installée |
| Calendar | 401 | installée |
| Contacts | 401 | installée |
| Deck | 401 | installée |
| **Mail** | 404 (route d'envoi OCS 404) | **absente** |
| **Tasks** | 404 | **absente** |

**Mail.**
- Nextcloud Mail n'est pas installé : à installer par Nico. C'est un client : **il lui faut une vraie boîte derrière**
  (Gmail, OVH…). Passer par Nextcloud ne supprime donc pas le besoin d'une boîte ni, pour Gmail, du mot de passe
  d'application Google. Celui-ci est alors confié à Nextcloud : ARIA ne détient qu'un mot de passe d'application Nextcloud.
- Envoi : `MessageApiController::send`, `POST /message/send` (`accountId`, `fromEmail`, `subject`, `body`, `isHtml`, `to`)
  [code source de `nextcloud/mail`, branche `main`]. URL complète supposée `/ocs/v2.php/apps/mail/message/send`, et
  compatibilité avec Nextcloud 32.0.5 **non vérifiées** [à tester après installation]. Réponse 202 possible : envoyé mais
  pas copié dans « Envoyés ». Limite : 5 requêtes par période de 100 [unité non lue], sans effet pour un usage perso.
- Cette route n'envoie que : pas de dépôt de brouillon confirmé. Le « oui » dans Telegram reste le garde-fou.
- Domaine : `lemineur.ovh` a ses MX chez OVH et un SPF qui n'autorise que `mx.ovh.com` [code, dig]. Envoyer depuis
  le serveur YunoHost (`192.168.1.69:587` ouvert) avec cette adresse risque le spam.
- Lecture sur le téléphone : pas d'appli Android Nextcloud Mail officielle à ma connaissance [connaissance], donc navigateur
  ou client mail classique branché sur la même boîte.

**Notes et listes.** Notes installée : deux chemins possibles, dépôt de fichier (pas de secret, délai du timer de 5 min) ou
API Notes v1 `/index.php/apps/notes/api/v1/notes` (immédiat, mot de passe d'application) [doc]. Le mail exige déjà ce mot de
passe, donc l'API ne coûte aucun secret de plus et évite le timer. Tasks absente : une liste = une note à cases `- [ ]`.

**Agenda.** Calendar déjà installée, et même mot de passe : il devient peu coûteux pour un sprint suivant.

## Sources

- [Telegram Bot API](https://core.telegram.org/bots/api), [Telegram Mini Apps](https://core.telegram.org/bots/webapps)
- [Google Keep API, annonce Workspace](https://workspaceupdates.googleblog.com/2021/05/keep-audit-logs-and-api.html), [Google Keep API, développeurs](https://developers.google.com/workspace/keep)
- [Nextcloud Mail, MessageApiController](https://raw.githubusercontent.com/nextcloud/mail/main/lib/Controller/MessageApiController.php), [API Notes](https://github.com/nextcloud/notes/blob/main/docs/api/README.md)
- [Tasker, HTTP Request Event](https://tasker.joaoapps.com/userguide/en/help/eh_http_request.html)
- [Nodemailer, Using Gmail](https://nodemailer.com/usage/using-gmail), [Gmail SMTP 2026 (secondaire)](https://prospeo.io/s/setup-smtp-gmail)

## Reprise

**Arbitrages déjà rendus par Nico** : suite Nextcloud (pas Keep, pas Gmail en direct) ; Gmail branché derrière Nextcloud Mail ;
notes et listes écrites en direct par l'API Notes v1 ; une liste = une note à cases `- [ ]` ; périmètre mails + notes + listes,
agenda et SMS plus tard. Mail envoyé après « oui » dans Telegram : défaut annoncé, non contesté.

**Préalables à la charge de Nico** : installer Nextcloud Mail, y brancher le Gmail (mot de passe d'application Google) ;
créer un mot de passe d'application Nextcloud « ARIA », le mettre dans `/home/nico/groq/.env` sous `NEXTCLOUD_APP_PASSWORD`.

**Ensuite** : tester l'API Notes et la route d'envoi (note de test, mail à Nico lui-même), puis valider le découpage avec Nico
(non validé à ce jour) : 1) `/send` limité au PGN + notes et listes ; 2) mail sur « oui » ; 3) run live.
Branche proposée : `feat/sprintN-nextcloud-actions`. Revérifier les constats de code sur le `main` du moment.
