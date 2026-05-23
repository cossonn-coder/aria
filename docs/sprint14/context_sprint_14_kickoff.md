─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 14 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-20
**Branche de travail prévue** : à décider en ouverture de sprint
  selon l'item sélectionné en premier
**Tag de référence sortie sprint 13** : `sprint-13`
**État sprint 13** : CLOS. #28 livré (pin `mempalace` via URL
  git @SHA `b8caf32` sur fork `cossonn-coder/mempalace`,
  remplace `mempalace==3.3.0` cassé par construction ; commit
  `c3426b8`, mergé via `7dc11a5`). Validation install fresh
  dans venv jetable + smoke runbook §6 (exit 0, count=753,
  dim=768, backend ST `_MempalaceST`, isinstance ST passé).
  Dette #30 close formellement (validation runtime fix #25
  confirmée). Dette #25 close. Trois dettes nouvelles ouvertes
  (#31 drift HNSW, #32 digression Belgique, #33 garde runbook
  §6 path-based). Dette #29 déclassée (Nextcloud explique le
  path, à documenter en bordure d'un sprint touchant doc install).

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 13 (rappel synthétique)

- **#28 résolu via piste C (pin URL git @SHA).** Diagnostic
  structurel clé de l'audit `docs/sprint13/audit_pin_mempalace.md`
  §1.6 : le désalignement n'est pas `3.3.0` vs `3.3.5` PyPI,
  c'est `d0163a7` (v3.3.5 upstream sans configurable embedder)
  vs `b8caf32` (= v3.3.5 + 1 commit fork qui introduit le marker
  `.mempalace-embedder.json`). La 3.3.5 PyPI existe mais ne
  contient PAS le patch fork — pin A (numéro) aurait été un
  faux fix qui casse le palace prod silencieusement (mismatch
  dim 768/384 entre embeddings persistés et EF résolue).
  Piste C choisie : `mempalace @ git+https://github.com/cossonn-
  coder/mempalace.git@<SHA>` dans `requirements.txt`, avec
  commentaire de traçabilité du même style que pin
  `chroma-hnswlib==0.7.6` sprint 12. Workflow dev documenté
  dans `docs/architecture/install_mempalace.md` (override
  editable `pip install -e ../mempalace-fork` post-install,
  règle de bump SHA délibéré + tracé).
- **#30 validation runtime du fix smoke pattern ST (#25) faite
  en conditions réelles** sur palace prod 19 mai. Le heredoc
  section 6 du runbook a passé l'assert `isinstance(ef,
  SentenceTransformerEmbeddingFunction)` sur le subclass
  tactique `_MempalaceST`, confirmant le fix `0ebb00f` sprint
  12. Effet de bord majeur : une quarantine HNSW sur le segment
  VECTOR de `mempalace_drawers` s'est déclenchée pendant le
  smoke, audit complet `docs/sprint13/audit_drift_segment_2026
  -05-19.md` produit en réponse, verdict architecte no-pivot
  (le mécanisme du fork a contenu l'incident, sqlite est source
  de vérité, rien perdu).
- **Convention `docs/architecture/` étendue.** Premier ajout
  sprint 14-ready : `install_mempalace.md` qui documente la
  procédure d'install pinned-by-SHA, l'override editable pour
  dev, et la règle de bump. Cohérent avec le critère
  d'admission (sujet structurel stable, non lié à un sprint
  particulier).
- **Calibrage no-pivot tenu sous pression.** Le tour micro-audit
  drift a remonté une recommandation "pivoter" en §4. Refusée
  côté architecte (drift contained, dette à part, sprint reste
  sur #28). Discipline du calibrage explicite : quand on hésite,
  on prend le moins exigeant ; si le bug réapparaît, on le
  traite. Discipline équivalente à sprint 11 tour 2 (verdict C
  émergent documenté en §5 sans dérouler).

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-20 (post sprint 13)

| #  | Sujet                                                  | Statut                          |
|----|--------------------------------------------------------|---------------------------------|
| 9  | (legacy sprint < 6)                                    | ouvert                          |
| 10 | (legacy)                                               | ouvert                          |
| 11 | (legacy)                                               | ouvert                          |
| 13 | (legacy)                                               | ouvert                          |
| 15 | (legacy)                                               | ouvert                          |
| 16 | (legacy)                                               | ouvert                          |
| 17 | Semantic wings non câblées                             | ouvert, sujet architectural     |
| 18 | Palace MiniLM anglais sur contenu français             | RÉSOLUE sprint 8                |
| 19 | (legacy)                                               | ouvert                          |
| 20 | Drift sqlite/HNSW non flushé                           | REQUALIFIÉE sprint 9, voir #31  |
| 21 | Doc structurelle chromadb palace closets               | RÉSOLUE sprint 11               |
| 22 | Orphelins `.drift-*` / `.corrupt-*` dans palace prod   | RÉSOLUE sprint 10               |
| 23 | (legacy)                                               | ouvert                          |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | **RÉSOLUE sprint 12, validation sprint 13** |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 (backlog "à confirmer" à reprendre) |
| 27 | `chroma-hnswlib` non pinné, traçabilité venv manquante | RÉSOLUE sprint 12               |
| 28 | Pin `mempalace==3.3.0` désaligné du venv editable      | **RÉSOLUE sprint 13**           |
| 29 | Path venv `/home/nico/projects/aria/` versus repo Nextcloud | **DÉCLASSÉE sprint 13** (Nextcloud explique, à documenter en bordure d'un sprint doc install) |
| 30 | Validation runtime du fix smoke pattern ST (#25)       | **RÉSOLUE sprint 13**           |
| 31 | Drift HNSW mécanique récurrent sur `mempalace_drawers` | **ouvert sprint 13, candidat sprint 14** |
| 32 | Digression conversationnelle aria (vacances Normandie → fête nationale belge) | **ouvert sprint 13**, comportemental |
| 33 | Garde runbook §6 `"mempalace-fork" in __file__` path-based | **ouvert sprint 13**, doc |

─────────────────────────────────────────────────────────────────────────

## Détail des dettes nouvelles

### #31 — Drift HNSW mécanique récurrent sur `mempalace_drawers`

**Observation source** : audit `docs/sprint13/audit_drift_segment_2026-05-19.md`.

**Mécanique** : `aria.service` écrit en sqlite à chaque
interaction (753 entries au moment du smoke), mais le flush
HNSW chromadb-rust ne suit pas synchroniquement (dernier flush
HNSW à 09:03 UTC, écart de 6h12 ≈ 22 129 s au moment du smoke,
seuil de quarantine du fork franchi). À chaque ouverture du
palace (smoke, redémarrage service, reload après crash), si
l'écart sqlite/HNSW dépasse le seuil, le fork quarantaine le
segment HNSW (`.drift-<timestamp>`) et le reconstruit depuis
sqlite — source de vérité, aucune donnée perdue. Le palace
continue de fonctionner normalement post-reconstruction.

**Impact réel** : pollution `.drift-*` à long terme dans
`~/.mempalace/palace/` (un seul aujourd'hui, rien n'empêche
l'accumulation à terme), pas de perte de données effective
sur les évènements observés. Profil similaire à #22 traité
sprint 10 en bordure.

**Sujets à instruire** :
- Cartographier le mécanisme de flush HNSW côté chromadb-rust
  / wrapper fork (où, quand, sous quelle condition se déclenche
  un flush).
- Vérifier s'il existe une API `flush()` / `persist()`
  exposable, et l'invoquer à minima dans le shutdown handler
  d'`aria.service` et avant chaque smoke (réduit la fenêtre
  de drift sans toucher au mécanisme interne).
- Définir une retention policy pour les `.drift-*` (aujourd'hui :
  aucune, ils restent en place indéfiniment).
- Confirmer le seuil de quarantine du fork côté
  `ChromaBackend._read_embedder_marker` / integrity check.

**Effort estimé** : moyen-élevé selon profondeur. Un sprint
exploratoire suffit pour la cartographie ; le fix peut être
un sprint séparé.

### #32 — Digression conversationnelle aria (Normandie → Belgique)

**Observation source** : trace conversationnelle Telegram du
19 mai pendant la session de smoke. Échange littéral :
Nico:    Planifier mes vacances en Normandie.
Aria:    Tu veux partir quand ?
Nico:    15 août
Aria:    15 août, c'est la date de la fête nationale en
Belgique. Tu veux marquer le coup ou tu cherches
autre chose ?

La réponse part en digression hors-sujet (la fête nationale
belge n'a aucun rapport avec un projet vacances Normandie).
L'intent classifié au log était `réservation voyage` à 17:11:40,
suivi de `contraintes` à 17:12:02. Le routing cognitif a
correctement opéré, le problème est dans le LLM de génération
(Anthropic Haiku 4.5 utilisé en fallback ce soir-là, cf.
`17:11:28 [INFO] llm.llm_router — [LLM] Anthropic (claude-haiku
-4-5) a répondu`).

**Hypothèses non vérifiées** :
- Hallucination de fait (le 15 août n'est PAS la fête nationale
  belge — celle-ci est le 21 juillet ; le 15 août est l'Assomption
  catholique, jour férié dans plusieurs pays dont la Belgique
  mais pas une fête nationale). Donc double erreur : digression
  hors-sujet ET fait incorrect.
- Effet de fallback : Haiku est moins fiable que les modèles
  de tête sur ce type de prompt structuré planning. Le routing
  fallback (cerebras 429 → openrouter 404 → anthropic OK) a
  livré une réponse mais sur un modèle dégradé.
- Effet du prompt système / contraintes soul.md ("ne pas faire
  de longs préambules"). À vérifier que la consigne du planning
  est passée correctement.

**Sujets à instruire** :
- Cartographier le flow exact entre classification intent →
  prompt assembly → appel LLM pour l'opération `planning` /
  `réservation voyage`.
- Reproduire la digression (rejouer le prompt sur les différents
  providers — Haiku, Cerebras, Gemini, Groq) pour identifier
  si le bug est lié au modèle ou au prompt.
- Évaluer l'ajout d'une consigne explicite "reste sur le sujet
  demandé, pas de digression culturelle non sollicitée" dans
  le prompt système des opérations planning.

**Effort estimé** : moyen. Tour d'audit (cartographie flow +
reproduction) puis fix sur prompt si la cause est identifiée.
Sujet comportemental, pas systémique — risque scope creep
modéré (peut révéler d'autres digressions sur d'autres flows).

### #33 — Garde runbook §6 `"mempalace-fork" in __file__` path-based

**Observation source** : tour fix #28 sprint 13. Le smoke
runbook §6 contient une garde de provenance :

```python
assert "mempalace-fork" in mempalace.__file__
```

Cette garde a du sens en mode editable (le `__file__` pointe
vers le repo local, qui contient bien `mempalace-fork` dans
son path). Mais en mode build non-editable (install depuis
URL git @SHA, profil post-#28), le `__file__` pointe vers
`site-packages/mempalace/` qui ne contient pas `mempalace-fork`.
Claude Code a substitué la garde dans son smoke jetable par
un check sémantique (présence du paramètre `model_name` dans
la signature de `get_embedding_function`, qui est la signature
exacte du commit `b8caf32`). C'est plus robuste — mais le
runbook lui-même n'a pas été mis à jour.

**Conséquence** : prochain run du smoke depuis venv non-editable
(par exemple si Nico ré-install son venv principal en mode
build pour aligner sur la spec, ou en CI), la garde path-based
échouera alors que le code est correctement installé.

**Sujets à instruire** : harmoniser la garde du runbook §6
pour qu'elle fonctionne dans les deux modes (editable + build).
Substitution proposée : check signature `model_name` (déjà
validée par Claude Code au tour fix #28), ou check croisé
(path OU signature).

**Effort estimé** : très bas. Modification d'un heredoc dans
un seul fichier. Peut s'agréger à un tour de polish ou en
bordure d'un sprint qui touche au runbook.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 14 : indéterminée à l'ouverture

### Candidats opérationnels (impact direct, effort bas/moyen)

- **#33 — garde runbook §6 path-based**
  Effort très bas, fix trivial, profil "polish doc". À traiter
  en bordure d'un autre sprint ou en sprint flash.

- **#26 backlog résiduel — purge backups validés**
  Itérer sur la liste avec arbitrage Nico item par item.
  Gain attendu : ~12-15 Mo récupérables sans risque + arbitrage
  des snapshots de backup. Inchangé depuis sprint 12.

- **#29 — documentation Nextcloud path**
  Déclassée mais à documenter en bordure d'un sprint touchant
  la doc install. `docs/architecture/install_mempalace.md`
  serait l'endroit naturel pour mentionner le path Nextcloud.
  Effort 5 minutes.

### Candidats opérationnels (impact direct, effort moyen)

- **#32 — digression aria Normandie/Belgique**
  Cartographie flow planning + reproduction sur providers +
  arbitrage prompt. Effort moyen. Risque modéré de scope
  creep si d'autres digressions émergent en cours d'audit.
  Sujet comportemental qui touche au cœur expérience utilisateur,
  donc visible immédiatement à chaque interaction.

### Candidats structurels (impact fort, effort élevé)

- **#31 — drift HNSW mécanique récurrent**
  Sujet potentiellement multi-sprints. Cartographie flush
  HNSW d'abord (sprint exploratoire), fix (API flush exposable
  + shutdown handler + retention policy `.drift-*`) ensuite
  dans un ou deux sprints séparés. Mécanique récurrente mais
  contenue, pas urgent — le palace continue de fonctionner.

- **#17 — semantic wings non câblées**
  Sujet architectural, plusieurs sprints potentiels. Nécessite
  cadrage préalable du contour. Pas adapté à un sprint
  exploratoire seul.

- **Doc additionnelle `docs/architecture/`** maintenant que la
  convention est confirmée par `install_mempalace.md`. Candidats :
  couches mémoire logiques (wings/rooms), dispatcher, contrats
  memory/writer.py. Aucun n'est pressé.

### Candidats legacy (sans diagnostic préalable, effort inconnu)

- **#9, #10, #11, #13, #15, #16, #19, #23, #24** : dettes ouvertes
  héritées d'avant le sprint 6. Aucune n'a été touchée depuis.
  Possibilité de faire un tour de triage rapide pour requalifier
  ou fermer plusieurs en lot. Toujours pas adressé.

### Recommandation de premier message

> "Démarrage sprint 14 : choix de l'item prioritaire. Candidat
> évident #32 (digression aria Normandie/Belgique, sujet
> comportemental visible à chaque interaction). #31 (drift HNSW)
> est le candidat structurel le plus solide mais multi-sprints.
> #33 (garde runbook path-based) en polish trivial agrégeable.
> Tu me donnes ta préférence ?"

─────────────────────────────────────────────────────────────────────────

## Backlog résiduel #26 (toujours en attente d'arbitrage Nico)

Inchangé par rapport aux kickoffs sprint 12 et 13 — items "à
confirmer" non actionnés. Liste depuis
`docs/sprint10/audit_mempalace_artefacts.md` § 5 colonne "à
confirmer avec Nico" :

- 3 tar.gz top niveau dans `~/.mempalace/` (~13 Mo cumul).
- `palace_backup_2026-04-22/` (15 Mo) — état pré-sprint 8.
- `palace_preprod_20260513T124229/` (9,2 Mo) — préprod #1 mpnet.
- `palace.backup-pre-live-20260518T100943/` (9,1 Mo) — snapshot
  avant bascule mpnet final.
- `palace.rollback-failed-20260513T131824/` (9,2 Mo) — rollback
  raté 14 mai.
- `~/.mempalace/config.json` legacy MemPalace 3.x non lu par ARIA.
- 36 locks dans `~/.mempalace/locks/` (30 vides + 6 stale).
- Snapshots pré-tours sprint 10 : `palace_backup_pre_sprint10_*.tar.gz`
  (~9 Mo cumul).

À reprendre en bordure d'un sprint qui touche au palace.

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Inchangé depuis sprint 8 : **fix qui marche + 1 test de
non-régression sur le cas nominal, rien de plus**. Pas de
filets spéculatifs, économies de soin par défaut.

Exception réactivée si l'item sélectionné touche au palace prod
avec contenu réel à préserver. À ce moment-là Nico le signale.

Validation supplémentaire sprint 13 : la discipline a permis de
**refuser un pivot** sous pression d'une découverte adjacente
(quarantine HNSW), en gardant le sprint sur sa cible #28 et en
documentant le drift en dette propre. À reproduire.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Cinq leçons préservées des sprints 10-13 :

1. **Test discriminant before/after avec preuve causale** —
   pour tout fix qui touche un comportement systémique. Cf.
   sprint 10 tour 2b (preuve causale orphelin → drift).
2. **Refus du mélange de scope malgré découverte adjacente** —
   sprint 11 tour 2 : verdict C émergent documenté en §5 sans
   dérouler l'investigation. Sprint 13 tour micro-audit : refus
   du pivot recommandé par l'audit lui-même, ouverture d'une
   dette propre. À reproduire.
3. **Reconnaître l'outil structurellement inadéquat** — `lsof`
   sur chromadb-rust = vide-par-construction, pas verdict
   d'inactivité. Cf. `docs/architecture/chromadb_palace.md`
   § Propriété observable.
4. **Brief atomique = un objectif, un livrable.** Le tour pin
   #27 sprint 12 avait dérivé sur la chaîne « merge + clôture
   + tag » sans validation préalable. Sprint 13 : trois tours
   atomiques séparés (audit drift / audit pin / fix pin),
   chaque livrable validé avant le suivant, clôture en tour
   distinct. À reproduire systématiquement.
5. **Diagnostic structurel avant fix** — sprint 13 #28 :
   l'audit a révélé que le problème n'était pas
   `3.3.0 vs 3.3.5` mais SHA fork vs PyPI. Sans cet audit, la
   piste A "évidente" aurait été un faux fix qui casse le palace
   silencieusement. À reproduire : ne jamais accepter un fix
   sur une dette dont le périmètre n'a pas été cartographié.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-13` (fait en clôture sprint 13 —
  commit de merge `7dc11a5`, tag `sprint-13` sur ce commit,
  pushé sur origin).
- `feat/sprint13-mempalace-pin-coherent` conservée localement
  et sur origin (non supprimée, conformément à convention).
- Décider de la branche de travail en fonction de l'item retenu :
  - `feat/sprint14-aria-digression-fix` si #32
  - `feat/sprint14-drift-hnsw-cartography` si #31
  - `feat/sprint14-runbook-guard-fix` si #33
  - `feat/sprint14-mempalace-backup-cleanup` si purge backups #26
  - `feat/sprint14-legacy-triage` si triage legacy
  - `feat/sprint14-semantic-wings` si #17 (cadrage)

─────────────────────────────────────────────────────────────────────────