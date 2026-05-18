# ARIA — Kickoff sprint 8 (T-Migrate-Peek-Fix puis run live mpnet)

**Date** : 2026-05-17
**État sprint 7** : phase 1 close (patch fork + bascule venv
ARIA), phase 2 partiellement close (runbook livré + Preprod
exécuté avec verdict ROUGE), phase 3 (run live prod) bloquée.
**Session précédente** : clôture sprint 6, patch fork MemPalace
(b8caf32), bascule venv ARIA sur le fork, patch
migrate_embedder.py pour écrire le marker
.mempalace-embedder.json, rédaction et trois patchs successifs
du runbook docs/sprint7/runbook_t_mempalace_live.md, exécution
T-Mempalace-Preprod (échec étape B sur palace dégradé),
livraison audit docs/sprint7/audit_migrate_embedder_peek.md.

---

## Pourquoi nouvelle session

La session précédente a consommé ~65% de sa fenêtre sur la
trajectoire complète : 3 patchs runbook + 1 Preprod live + 1
audit pré-fix. Le sprint 8 doit fixer le script
migrate_embedder.py, refaire un Preprod (a priori vert cette
fois), puis le run live prod. Quatre tours minimum, dont au
moins un live avec risque de réaction temps réel — exige une
fenêtre claire. Discipline éprouvée depuis sprint 6 : run live
en session dédiée.

---

## Acquis techniques (inchangés depuis kickoff sprint 7)

### Fork MemPalace
- Repo : https://github.com/cossonn-coder/mempalace
- Branche : feat/configurable-embedder
- Commit : b8caf3259021d27c2689928458ac02d5a0defd01
- Base : tag upstream v3.3.5
- API publique pour ouverture avec marker :
  `mempalace.palace.get_collection(palace_path,
  collection_name=..., create=False)` (palace.py:59-73), qui
  délègue à ChromaBackend._resolve_embedding_function
  (chroma.py:1155-1185) consommant
  `.mempalace-embedder.json` via _read_embedder_marker.
- Comportement défensif acté : un marker cassé NE FAIT PAS
  raiser à l'ouverture, le fork retombe silencieusement sur
  l'ONNX MiniLM par défaut (chroma.py:57 et 1183 catch
  Exception). Surface à l'AssertionError dim/backend du smoke
  test, pas à l'ouverture.

### Venv ARIA
- mempalace installé en editable depuis
  ~/Nextcloud/projects/mempalace-fork/
- `pip show mempalace` retourne Location site-packages
  (trompeur, pip 25). Vérif réelle : python -c "import
  mempalace; print(mempalace.__file__)" doit pointer le fork.
- Pytest ARIA : 211 passed sous le fork (confirmé sprint 7).
- Doc de trace : docs/sprint7/install_notes.md (commit
  bd77233).

### Script migrate_embedder.py
- HEAD bd77233. Écrit les deux markers à l'étape G.
- 3 tests verts pour le marker.
- **Bug identifié sprint 7 phase 2** : appel
  `collection.peek(limit=1)` à l'étape B (ligne 244) force
  une lecture HNSW. Plante sur palace avec segments
  quarantained. Idem ligne 528 (étape F validation, mais sur
  collection nouvellement créée donc moins critique).

### Runbook T-Mempalace-Live
- docs/sprint7/runbook_t_mempalace_live.md, 11 sections + R,
  tags [GÉNÉRIQUE] vs [PROD], après 3 patchs successifs.
  Document considéré comme final hors une note de cleanup à
  ajouter pour les répertoires .drift-*/.corrupt-* orphelins
  post-migration (cf. surprise n°1 audit).
- Section 6 ouvre via API fork
  (mempalace.palace.get_collection), avec garde
  "mempalace-fork" in __file__ en tête du heredoc.

### Audit pré-fix migrate_embedder.py
- docs/sprint7/audit_migrate_embedder_peek.md, 1083 lignes.
- Inventaire : seuls deux peek HNSW-required, ligne 244 et
  528. Le 244 est cosmétique (dim source connue par
  _expected_dim(from_model)). Le 528 est sur collection
  vierge post-migration donc sain.
- Dim de la collection lisible en SQLite-only via
  `SELECT dimension FROM collections WHERE name=...`,
  vérifié sur le palace prod : `mempalace_drawers|384` et
  `mempalace_closets|384`.
- Étapes D et E sont déjà SQLite-only sur leurs lectures.
- Surprises documentées : (1) répertoires .drift-* /
  .corrupt-* survivent à delete_collection (orphelins
  fichiers), (2) exit propre count==0 à préserver dans le
  fix, (3) le filet Preprod a payé.

---

## Découvertes stratégiques sprint 7 phase 2

### Le palace prod est dégradé depuis le 13 mai
- Quatre répertoires `<segment_id>.drift-20260513-180821` et
  `.corrupt-20260513-180821` dans ~/.mempalace/palace/.
- Reliques du crash sprint 6 (kickoff T-Mempalace-Live le
  mentionnait : "drift hérité du crash sprint 6").
- Le service ARIA tourne actuellement sur UN seul segment
  HNSW vivant (b28198b8-...).

### Le drift est continu, pas seulement hérité
- À l'ouverture de la copie pré-prod par le fork le 17 mai,
  drift sqlite/HNSW de 118948 s ≈ 33 h détecté.
- Interprétation : le service ARIA prod continue d'écrire
  dans SQLite pendant que les segments HNSW ne sont pas
  flushés en sortie. À chaque heure passée, l'écart se
  creuse.
- Conséquence : toute copie rsync à chaud du palace prod
  héritera de ce drift. Le stop service avant rsync
  pourrait converger les choses, à valider empiriquement.

### Le script migrate_embedder.py n'est pas tolérant aux palaces dégradés
- Plante à l'étape B sur `peek()`.
- Le fix est à portée de quelques lignes mais a deux pièges
  (surprise n°1 et n°2 de l'audit).

### Le filet Preprod a fait son travail
- Décision sprint 7 d'ajouter une phase Preprod sur copie
  AVANT prod : payante.
- Le run live aurait crashé en étape B avec service à
  l'arrêt — scénario évité.
- À documenter comme acquis méthodologique pour les
  prochains sprints touchant à la prod.

---

## État git ARIA

- Branche : feat/sprint6-embedder-audit, HEAD bd77233.
- 1 commit local non poussé : bd77233 (à pusher en fin de
  sprint 8).
- main : 07c012d (merge sprint 6, déjà poussé).
- Tag sprint-6 : c30a530 sur 254a86e, poussé.
- Working tree clean hors trois untracked dans docs/sprint7/ :
  - context_sprint_7_T-Mempalace-Live_kickoff.md
  - runbook_t_mempalace_live.md
  - audit_migrate_embedder_peek.md
  Ces trois fichiers seront commités en cours de sprint 8,
  selon l'arbitrage du commit final de clôture.

---

## État artefacts sprint 7 phase 2 (à conserver pour sprint 8)

- Copie pré-prod conservée :
  /home/nico/.mempalace/palace.preprod-20260517T215402
  Sert de palace de test pour valider le fix script (réplique
  fidèle du drift prod, dim source 384, count 710).
- Log Preprod : /tmp/migrate_preprod_20260517T215402.log
- Snapshot tar.gz script :
  /home/nico/.mempalace/mempalace_drawers_backup_20260517T195620Z.tar.gz
- État env : /tmp/preprod_state.env

Palace prod intact, service ARIA toujours actif, aucune
modification du repo ARIA suivi.

---

## Plan d'exécution sprint 8

Quatre tours minimum, ne pas tout enchaîner dans un seul
brief.

### Phase 1 : fix script migrate_embedder.py
Brief T-Migrate-Peek-Fix. Sur la base de l'audit
docs/sprint7/audit_migrate_embedder_peek.md, choix d'une
stratégie (probablement combinaison de a + d : remplacer le
peek de l'étape B par une lecture SQLite directe de la dim
via la connexion chroma.sqlite3, garder le peek de l'étape F
mais avec try/except en filet). Pièges à éviter :
- préserver exit propre count==0 (surprise n°2 audit) ;
- s'assurer que la lecture SQLite directe ne dépend pas du
  fichier chroma.sqlite3 être au chemin par défaut (chemin
  paramétré par palace-path).

Livrable : diff restreint au script + tests verts.

### Phase 2 : nouveau Preprod sur copie fraîche
Brief T-Mempalace-Preprod-2. Réexécution complète du tour
Preprod sprint 7 sur une NOUVELLE copie rsync du palace prod,
avec le script patché. Objectif : verdict VERT bout-en-bout.

Question ouverte qui devra être tranchée en début de phase 2 :
faut-il stopper le service ARIA avant le rsync de cette
nouvelle copie pour éliminer le drift sqlite/HNSW continu ?
Avantage : confirme empiriquement l'hypothèse "stop service →
drift converge". Risque : si le drift ne converge pas, on a
fait stopper la prod pour rien. Recommandation à arbitrer :
faire le rsync à froid (service stoppé), mesurer le drift au
moment du rsync, redémarrer la prod immédiatement après
(avant la migration de la copie). Donne un signal empirique
décisif pour la phase 3.

### Phase 3 : run live prod
Brief T-Mempalace-Prod. Exécution du runbook
docs/sprint7/runbook_t_mempalace_live.md sections 2 à 10,
service ARIA arrêté, migration sur le palace prod, bascule
config.py, redémarrage, fumée Telegram. Si Preprod-2 est
vert, le risque résiduel est faible mais la discipline
session dédiée s'applique.

### Phase 4 : nettoyage post-succès
Suppression des artefacts : palace.rollback-failed-*,
palace_preprod_* (dont le 20260517T215402),
palace.backup-pre-live-*,
mempalace_drawers_backup_*.tar.gz, /tmp/migrate_*.log.
PLUS les répertoires `.drift-*` et `.corrupt-*` orphelins
post-migration dans le palace prod migré (surprise n°1
audit) — à ajouter au runbook avant exécution si pas déjà
fait.

### Phase 5 : clôture sprint 8
Commits restants poussés : bd77233 (sprint 7) + commits
sprint 8 (fix script, runbook si patché, bascule config.py,
audit). Tag sprint-7 OU sprint-8 selon arbitrage Nico (faut-il
un tag sprint-7 séparé ou tout est mergé sprint-8 ?).
Probablement : tag sprint-7 sur le commit de clôture
fonctionnelle phase 1+2 sprint 7 (livraison runbook + audit),
tag sprint-8 sur le commit de clôture run live mpnet réussi.
Merge main.

---

## Dettes ouvertes héritées (cumul sprint 6 + 7)

- **#9** : psutil non documenté dans requirements.
- **#10** : pas de fichier de dépendances versionné ARIA.
- **#11** : DeprecationWarning Python 3.14 sur tar.extractall
  dans migrate_embedder.py.
- **#13** : discipline workflow consignes CLAUDE.md
  hors-brief.
- **#15** : discipline pilote sur check pré-vol échoué (stop
  + rollback léger par défaut).
- **#16** : audit de surface des packages tiers
  auto-administrants.
- **#17** : couche sémantique ARIA non câblée par le
  pipeline normal (les wings aria_episodic / aria_semantic /
  aria_classifier sont des champs metadata sur la collection
  unique `mempalace_drawers`, cf. memory/writer.py).
- **PR upstream MemPalace** : optionnelle. Le patch fork est
  propre, à proposer si capacité. Acquis sprint 7 à inclure
  dans la PR si on la fait : mode strict opt-in pour
  get_embedding_function (paramètre `strict=True` qui
  raiserait au lieu de fallback ONNX silencieux quand le
  marker pointe un modèle introuvable). C'est défensif côté
  upstream MemPalace mais c'est un fail-silent côté ARIA.
- **#18** : robustesse de la garde fork dans la Section 6 du
  runbook (check par path `"mempalace-fork" in __file__`
  fragile si le répertoire est renommé). Suggestion : check
  par signature distinctive du fork (présence de
  `_resolve_embedding_function` sur ChromaBackend). Marginal.
- **#19** : Section 6 du runbook ne discrimine pas une EF
  SentenceTransformer mpnet d'une autre EF
  SentenceTransformer-based. Marginal — trois autres filets
  (Section 5, 7, 9) couvrent.
- **#20** : palace prod tourne sur un seul segment HNSW
  vivant depuis le 13 mai, avec drift sqlite/HNSW continu.
  Indépendamment de la migration mpnet, à comprendre :
  pourquoi le flush HNSW ne se fait pas pendant que le
  service tourne ? Comportement attendu de ChromaDB ou bug
  ARIA / fork ? Investigation hors-scope sprint 8 (la
  migration produit un palace neuf), mais à ouvrir comme
  ticket d'investigation pour un sprint dédié — si le bug
  est dans ChromaDB ou le fork, il se reproduira sur le
  palace migré dans quelques semaines.
- **#21** : la collection `mempalace_closets` (legacy sprint
  4, 32 entrées, dim 384) reste dans le palace prod. La
  migration sprint 8 ne la touche pas (le script ne traite
  que `mempalace_drawers`). Post-migration, le palace
  contiendra une collection en dim 768 (mempalace_drawers)
  et une en dim 384 (mempalace_closets). Pas de risque
  fonctionnel (ARIA ne lit que drawers), mais incohérence à
  acter et possiblement à nettoyer dans un sprint ultérieur.
- **#22** : surfaces orphelines des répertoires `.drift-*`
  et `.corrupt-*` post-delete_collection (surprise n°1
  audit). À inclure dans la phase 4 nettoyage.
- **#23** : bascule shells de `_resolve_embedding_function`
  legacy côté MemPalace (mcp_server.py et autres callers
  identifiés au tour T-Mempalace-Patch sprint 7) restent sur
  le default MiniLM. Hors-scope ARIA, à corriger dans une PR
  upstream future.

---

## Acquis méthodologiques sprint 7

Ces points sont à conserver comme discipline pour les futurs
sprints touchant à la prod.

- Le filet Preprod sur copie isolée AVANT toute touche prod
  est devenu une discipline acquise. Ajout net vs sprint 6
  qui était parti direct en prod.
- L'audit pré-fix systématique sur les sujets non triviaux
  (sprint 7 : audit fork avant patch, audit script avant
  fix) protège contre les fixes qui révèlent un autre bug
  en aval. Coût : un tour de plus. Gain : grand.
- Run live en session dédiée pour préserver une fenêtre de
  raisonnement claire en cas de réaction temps réel.

---

## Premier message à envoyer dans la nouvelle session

> Démarrage sprint 8 : fix script migrate_embedder.py puis
> retry run live mpnet. Voici le contexte de transition
> [PIÈCE JOINTE : ce document].
>
> Le sprint 7 a fait livrer runbook + audit pré-fix script.
> Bug bloquant identifié : peek() étape B plante sur
> palaces avec segments HNSW quarantained, ce qui est l'état
> du palace prod depuis le 13 mai (drift continu vs
> SQLite). Preprod sprint 7 verdict ROUGE — bug évité avant
> prod.
>
> Premier objectif : brief T-Migrate-Peek-Fix. Lecture
> docs/sprint7/audit_migrate_embedder_peek.md (sections 1,
> 4, 5 prioritaires), choix d'une stratégie (audit
> recommande implicitement combinaison a + d), patch du
> script avec tests, diff restreint. Pièges à intégrer :
> préserver exit count==0, chemin SQLite paramétré par
> palace-path.
>
> Objectif suivant : brief T-Mempalace-Preprod-2. Nouveau
> rsync du palace prod sur une copie fraîche, à froid
> (service ARIA stoppé le temps du rsync) pour mesurer si
> le stop converge le drift sqlite/HNSW. Si oui, signal fort
> pour la phase 3. Si non, on tient quand même avec le fix.
> Migration de la copie via le script patché, smoke complet,
> retrieval test bug #18 "Planifier des vacances en
> Normandie".
>
> Objectif après : brief T-Mempalace-Prod. Run live
> sections 2-10 du runbook.
>
> Lis aussi le runbook docs/sprint7/runbook_t_mempalace_live.md
> et l'audit docs/sprint7/audit_migrate_embedder_peek.md
> dans la VM Claude Code — pas besoin de me les re-citer.