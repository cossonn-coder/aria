# Sprint 23 — Tronçon 02 : « lis la suite »

Branche : `feat/sprint23-lecture-url`. Prérequis : tronçon 01 commité
(`URL_READ`, `URL_PARTIAL_MARKER`, handler de lecture d'une tranche
paramétré par `start`). Lire `CLAUDE.md`, `docs/sprint23/00_etat.md`, puis
le code livré au tronçon 01 dans `execution/routers/web_router.py`.

## Objectif

Après une lecture partielle, ARIA a proposé de lire la suite. Si Nico
répond « oui », « vas-y » ou « lis la suite », ARIA lit la tranche suivante
de la même page et en donne la synthèse (avec, si la page continue encore,
une nouvelle proposition de lire la suite).

## Mécanique (aucun état nouveau)

Le message enrichi du tour de lecture partielle contient le marqueur
`[Lecture partielle : <url> caractères <start>-<end> sur <total>]` et a été
écrit dans `aria_conversation` par `LLMExecutionRouter` (tour `user`). C'est
lui qui sert de mémoire. Lecture de l'historique uniquement via
`bridge.load_conversation_history(conversation_key, n=2)` (règle 2),
`conversation_key = str(metadata.get("chat_id", "default"))` comme dans
`web_router._build_query`.

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `cognition/cognitive_classifier.py` | détection de la demande de suite |
| `execution/routers/web_router.py` | branche « suite » dans le handler `URL_READ` |

### Classifier

Ensemble de réponses de reprise (message en minuscules, ponctuation finale
et espaces retirés) : `oui`, `ouais`, `vas-y`, `vas y`, `ok`, `continue`,
`la suite`, `lis la suite`, `oui lis la suite`, ou tout message contenant
`lis la suite` / `lire la suite`. **Seulement si** le message en fait partie
(pas de lecture d'historique pour les autres messages) : charger les 2
derniers messages via le `bridge` déjà reçu par `classify_operation`
(`cognitive_engine.py:113-118` passe `bridge` et `metadata` avec `chat_id`)
et vérifier que le dernier tour `user` contient `URL_PARTIAL_MARKER`. Si oui
→ `URL_READ`. Sinon, comportement inchangé (un « oui » ordinaire reste
`CONFIRMATION`). Placement : avec les heuristiques, **avant** la règle
« court → CONFIRMATION ». `bridge is None` → pas de reprise.

### Router

Dans le handler `URL_READ` : si `detect_url(message)` ne trouve pas d'URL,
c'est une reprise. Relire les 2 derniers messages (bridge), extraire du
dernier tour `user` l'URL et `end` du marqueur (regex sur le format exact
du tronçon 01), puis appeler la lecture de tranche avec `start = end`. La
consigne de synthèse ne s'appuie pas sur « oui » : résumé général de la
tranche. Marqueur introuvable → même consigne d'échec que le tronçon 01.

Logs : la ligne `url_read OK … start=… end=…` du tronçon 01 suffit (`start`
> 0 identifie une reprise).

## Tests à ajouter (cas nominal, fakes)

- Classifier : bridge fake dont le dernier tour `user` contient le marqueur
  → « oui » donne `URL_READ` ; sans marqueur → « oui » donne `CONFIRMATION`.
- Router : message « oui », historique fake avec marqueur `… caractères
  0-99000 sur 250000` → `extract` appelé avec l'URL du marqueur, la tranche
  synthétisée commence au caractère 99000 (vérifiable via le prompt passé à
  `complete`), nouveau marqueur `99000-…` dans `content`.

## Hors scope

- Retour en arrière, saut à une position, « lis tout ».
- Cache de la page entre deux tours (Tavily est rappelé, 1 crédit).
- Toute écriture mémoire nouvelle, toute modification de `LLMExecutionRouter`.

## Critère de fin

`pytest tests/ -q` vert ; tests ci-dessus présents et verts.
