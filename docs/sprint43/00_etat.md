# Sprint 43 — état vivant

**Sujet** : #137 mémoire des documents lus (fichiers Telegram et pages web).
**Phase courante** : implémentation (`/sprint-auto sprint 43`), tronçons 01-02 faits ; reste le run live 03.
**Branche** : `feat/sprint43-memoire-documents`.
**Audit** : `docs/sprint43/audit_memoire_documents.md`.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_fiche_document.md` | fiche `aria_episodic`/room `documents` + texte intégral `aria_documents` (`write_document`), extrait 1 500 car. + consigne de proposition de relecture | ✅ |
| 02 | `02_relecture.md` | `DOC_REREAD` : « relis… » ou « oui » après proposition → relecture depuis le palace | ✅ |
| 03 | `03_run_live.md` | run live (Nico), `run_live/inventaire.txt` + `messages.txt` | ⏳ |

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

- Ferme (si run live OK) : #137 ; #139 partiellement (la relecture ne refait plus l'OCR ; « lis la suite » oui).
- Nouvelles à inscrire à la clôture :
  - `retrieve_memories(type_filter=…)` filtrerait tout : les hits mempalace n'ont pas de champ `type` (0 caller prod).
  - « lis la suite » après une relecture d'un texte > 100 000 car. repart du fichier / de l'URL.
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
Prochaine étape : run live 03 par Nico.
