# Sprint 43 — tronçon 01 : fiche document et texte intégral en mémoire

Lire d'abord : `CLAUDE.md`, `docs/sprint43/00_etat.md`, `docs/sprint43/audit_memoire_documents.md`.

## Objectif

Chaque document lu (fichier Telegram `FILE_READ` ou page web `URL_READ`) laisse
en mémoire :
1. une **fiche** retrouvable par le sens (`aria_episodic`, room `documents`) ;
2. son **texte intégral extrait** (wing `aria_documents`, jamais rappelée par le sens,
   relue par la source au tronçon 02).

Quand une fiche remonte dans le contexte, elle est injectée sur 1 500 car. et le
LLM est invité à **proposer une relecture** s'il lui manque un détail.

## Format de la fiche (transversal : parsé au tronçon 02, ne pas changer)

Texte du document de la fiche, trois lignes puis la synthèse :

```
Document « <nom> » lu le <AAAA-MM-JJ>
Source : <chemin local ou URL>
Synthèse : <synthèse>
```

- `<nom>` : pour un fichier, le nom d'origine (`content["file_name"]` de l'Event FILE,
  aujourd'hui non transmis à `_read_slice` : à faire passer) ; pour une page, `page["title"]`.
- `<source>` : exactement la valeur `url` reçue par `_read_slice` (chemin ou URL, sans espace).
- Nom et source en tête : l'embedder (`paraphrase-multilingual-mpnet-base-v2`) ne lit que
  ≈ 128 tokens.

## Fichiers à toucher

### `memory/writer.py`
Nouvelle fonction `write_document(fiche: str, text: str, source: str, title: str)` — un seul
appel, un seul `col.upsert` de deux documents :

| doc | id | wing | room | type | métadonnées en plus |
|---|---|---|---|---|---|
| fiche | `document_<key>` | `aria_episodic` | `documents` | `document` | `source`, `title`, `timestamp`, `doc_key` |
| texte intégral | `document_text_<key>` | `aria_documents` | `<key>` | `document_text` | `source`, `title`, `timestamp` |

`key = sha256(source)[:16]` : renvoyer le même fichier (même `file_unique_id` → même chemin)
ou relire la même URL **remplace** fiche et texte. wing/room/type posés de façon non
surchargeable (invariant W4, comme `write_chess_game`).

### `execution/routers/web_router.py`
Dans `_read_slice`, branche succès, **seulement si `start == 0`** : appeler
`write_document(fiche, text, url, nom)` avec `text` = texte intégral extrait (`page["content"]`
entier, pas la tranche) et la synthèse de la tranche. Écriture non bloquante, même idiome que
`chess_router.py:628-632` (`try` / `log.exception`) ; log `document_write OK key=… source=… chars=…`.
Mettre à jour le commentaire d'en-tête (« Ce router n'écrit RIEN en mémoire » devient faux :
il écrit la fiche document via `writer.py`, l'échange reste écrit par `LLMExecutionRouter`).

### `cognition/cognitive_context.py`
Constante partagée avec le classifier du tronçon 02, à côté de `URL_PARTIAL_MARKER` :
`REREAD_PROPOSAL = "Veux-tu que je relise « "`.

### `cognition/context_builder.py`
`_build_episodic_section` : pour un hit dont `room == "documents"`, extrait `text[:1500]`
au lieu de `[:400]` (autres hits inchangés, budget global inchangé). Si au moins une fiche
document est retenue dans la section, ajouter en fin de section une ligne :

```
[Consigne : si la réponse demande un détail absent des synthèses de documents ci-dessus, dis-le et termine par la phrase exacte : Veux-tu que je relise « <nom du document> » ?]
```

(construite avec `REREAD_PROPOSAL`). Les hits du bridge portent `room` (champ mempalace) ;
ils ne portent **pas** `type` (cf. audit §8) : discriminer par `room`.

## Tests à ajouter (cas nominal)

- `tests/memory/test_writer.py` : `write_document` upserte deux docs avec les wing/room/type
  attendus et des ids stables pour une même source.
- `tests/execution/test_web_router.py` : un `FILE_READ` réussi appelle `write_document`
  (patché) avec la source, le nom d'origine et le texte intégral ; un `_read_slice` à
  `start > 0` ne l'appelle pas.
- `tests/cognition/test_context_builder.py` : une fiche room `documents` est injectée
  au-delà de 400 car. et la consigne `REREAD_PROPOSAL` apparaît ; sans fiche, pas de consigne.

## Hors scope (ne PAS faire)

- Relecture, classifier, nouvelle opération : tronçon 02.
- Toucher au prompt AnalystAgent, à `llm_router.py`, à `skip_intent`.
- Ajouter `aria_documents` à `/status` (`count_by_wing`) ou aux docs d'architecture (clôture).
- Fiche par tranche pour « lis la suite » (une seule fiche, écrite à `start == 0`).
- Corriger `retrieve_memories(type_filter=…)` (dette).

## Critère de fin

`pytest tests/ -q` vert ; les trois tests ci-dessus passent.
