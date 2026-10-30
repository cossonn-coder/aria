# Sprint 43 — état vivant

**Sujet** : #137 mémoire des documents lus (fichiers Telegram et pages web) ; ajouté en cours :
fausse quarantaine HNSW du palace (#105, #31), qui a bloqué le premier run live.
**Phase courante** : conception quarantaine figée ; reste le tronçon 03 (`/sprint-auto sprint 43`) puis le run live 04.
**Branche** : `feat/sprint43-memoire-documents`.
**Audits** : `docs/sprint43/audit_memoire_documents.md`, `docs/sprint43/audit_quarantaine_hnsw.md`.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_fiche_document.md` | fiche `aria_episodic`/room `documents` + texte intégral `aria_documents` (`write_document`), extrait 1 500 car. + consigne de proposition de relecture | ✅ |
| 02 | `02_relecture.md` | `DOC_REREAD` : « relis… » ou « oui » après proposition → relecture depuis le palace | ✅ |
| 03 | `03_quarantaine_hnsw.md` | fork : cherry-pick `e811b6d1` + push `nicofork` ; pin `requirements.txt` ; `log.warning` sur `{"error"}` dans `retrieve_memories` | ⏳ |
| 04 | `04_run_live.md` | run live (Nico) : étape 0 réparation (`run_live/reparation.txt`), étapes 1-8, étape 9 après redémarrage | ⏳ (1er essai 2026-10-30 ❌ palace) |

## Décisions arrêtées

- Cible : #137 (choix de Nico).
- Fiche document dans `aria_episodic` via `writer.py`, écrite par `web_router._read_slice` à
  `start == 0` (précédent : fiche échecs) — retrouvable par le sens, survit à l'historique et à `/oublie`.
- Pages web lues (URL_READ) : fiche aussi (même code).
- Extrait injecté des fiches document : 1 500 car. au lieu de 400 (autres souvenirs inchangés, budget inchangé).
- Texte intégral extrait stocké dans une wing dédiée `aria_documents` (lue par source, jamais rappelée
  par le sens) : relecture sans fichier ni OCR. Palace prod touché par **ajout** seul → calibrage faible maintenu.
- Clé = `sha256(source)[:16]` : même fichier / même URL → fiche et texte remplacés.
- Relecture dans le sprint (choix de Nico) : (a) « relis / relire / rouvre » détecté sans LLM ;
  (b) ARIA propose d'elle-même « Veux-tu que je relise « X » ? » (consigne dans le bloc de contexte,
  pas dans le prompt AnalystAgent) ; « oui » → relecture.
- Rejetés : recherche par le sens dans `aria_conversation` (cf. #40), écriture épisodique malgré
  `skip_intent`, RAG du texte intégral par morceaux.

## Dettes

- Ferme (si run live OK) : #137 ; #105 et #31 (cause racine = faux `.corrupt` du fork) ; #139 partiellement (la relecture ne refait plus l'OCR ; « lis la suite » oui).
- Nouvelles à inscrire à la clôture :
  - `retrieve_memories(type_filter=…)` filtrerait tout : les hits mempalace n'ont pas de champ `type` (0 caller prod).
  - « lis la suite » après une relecture d'un texte > 100 000 car. repart du fichier / de l'URL.
  - Ménage des `.drift-*` (6) et `.corrupt-*` (1) dans `~/.mempalace/palace` (+ segment orphelin après réparation).
  - Même fichier envoyé plusieurs fois → plusieurs fiches : la source contient l'identifiant Telegram unique.
  - Synthèse à l'envoi de l'inventaire : « carton 115, grenier » au lieu de garage (à recontrôler au run live).
  - `aria_documents` absente de `/status` (`count_by_wing`) et de `docs/architecture/memory_layers.md` (à documenter en clôture).

## §REPRISE

Tronçon 01 ✅ (2026-10-30, pytest 422 verts) : `writer.write_document`, fiche écrite par
`web_router._read_slice` à `start == 0` (nouveau kwarg `name` = nom d'origine du fichier),
`REREAD_PROPOSAL` dans `cognitive_context.py`, extrait 1 500 car. + consigne dans
`context_builder._build_episodic_section`. Écart mineur : la ligne de consigne n'est pas
décomptée du budget épisodique (≈ 50 tokens hors budget).

Tronçon 02 ✅ (2026-10-30, pytest 427 verts) : `CognitiveOperation.DOC_REREAD` → `web_router`,
`detect_doc_reread` (règle 2c du classifier), `bridge.load_document_text(source)`,
`web_router._handle_doc_reread` → `_read_slice(..., page={title, content})` (nouveau kwarg `page` :
ni extraction ni réécriture de fiche). Écart : dans le router, le cas « acceptation » est choisi
quand le message ne contient pas `relis/relire/rouvre` (et non sur la seule présence de la
proposition dans le dernier tour assistant) — sinon « relis X » juste après une proposition
relirait le document proposé avec l'ancienne question.
Run live 03 (2026-10-30 15:37-15:40) : ❌ dès l'étape 3. Les fiches sont bien écrites
(3 × `document_write OK`), mais après `/oublie` ARIA dit n'avoir aucun inventaire.
Cause (audit sur une copie du palace) : **pas le code du sprint**. À 15:39:50, mempalace a mis
l'index HNSW en quarantaine (`.drift-20261030-153950`, « sqlite 2672s newer than HNSW and integrity
check failed »), la 4e fois ce jour-là (07:12, 13:31, 13:48, 15:39). L'index reconstruit ne contient
que les vecteurs écrits depuis : SQLite a 690 entrées, le HNSW environ 200 [estimation sur la taille
de `data_level0.bin`]. Toute requête vectorielle filtrée sur une wing volumineuse
(`aria_episodic`, `aria_conversation`) échoue avec `Error finding id` ; les petits filtres
(`room=documents`, `wing=aria_documents`) passent (recherche exhaustive). `mempalace_store.search`
renvoie `{"error": …}`, que `bridge.retrieve_memories` lit comme 0 hit, sans aucun log :
le rappel épisodique global est muet depuis chaque quarantaine.
Constats secondaires :
- Même fichier envoyé 3 fois → 3 fiches : la source est le chemin téléchargé, qui contient
  l'identifiant Telegram unique (`AgADoB4…`, `AgADoR4…`, `AgADoh4…`) ; « même source → remplacé » ne tient pas.
- Synthèse à l'envoi : « carton 115, grenier », alors que l'inventaire dit garage (ligne 117).
Suite : conception « quarantaine HNSW » ci-dessous.

### Conception « quarantaine HNSW » (2026-10-30, phase A)

Audit : `docs/sprint43/audit_quarantaine_hnsw.md` (lire le TL;DR). Résumé : perte réelle le
2026-10-23 11:56 (faux `.corrupt` du fork sur un pickle `dimensionality None`, format normal de
chromadb-rust) ; correctif upstream `e811b6d1` applicable au fork ; réparation par
`migrate_embedder.py` mpnet→mpnet testée sur copie (690/690) ; erreur muette dans le bridge.
L'estimation « ~200 vecteurs » ci-dessus est fausse (capacité préallouée, pas un compte).
Arbitrages tranchés par Nico (2026-10-30) :
1. Rattachement : sprint 43, même branche ; un seul run live rejoué couvre réparation + documents.
2. Correctif : cherry-pick `e811b6d1` sur le fork (+ ses tests), push `nicofork`, bump du pin
   `requirements.txt`. Rejetés : montée v3.3.6 (227 commits), contournement côté ARIA (attribut privé).
3. Réparation prod par Nico au run live (arrêt service, sauvegarde, marker déplacé,
   `migrate_embedder` mpnet→mpnet) + `log.warning` dans `retrieve_memories` sur `{"error"}`.
   Pas de ménage des `.drift-*`/`.corrupt-*` (dette).
Conception figée sur OK de Nico (2026-10-30) : kickoffs `03_quarantaine_hnsw.md` et
`04_run_live.md` (ancien `03_run_live.md`, renommé), `run_live/reparation.txt`.

**Prochaine étape** : `/sprint-auto sprint 43` → tronçon 03 seul, puis remise du run live 04 à Nico
(étape 0 = réparation du palace, à faire **après** le correctif du fork).
