# ARIA — Transition session T-Embedder3 (run live prod)

**Date** : 2026-05-13
**État sprint 6** : T-Z + T-Embedder1 + T-Embedder2 (A, B, C, D + D-bis) clos.
**Phase suivante** : T-Embedder3 — exécution prod de la migration
embedder M0→M2 sur le palace MemPalace réel, bascule
`EMBEDDING_MODEL` dans `config.py`, validation Telegram live.

---

## Ce qui a été fait pendant le sprint 6 embedder

### T-Z (clos session précédente)
Nettoyage repo, renommage branche `feat/sprint2-image-pipeline` →
`main`, suppression branches mortes, tag `sprint-5` pushé, outils CLI
DeepSeek commités. HEAD main `892434d`.

### T-Embedder1 (session dédiée précédente, pushée)
Audit lecture seule + inventaire collections vectorielles + benchmark
qualité multilingue 6 modèles × 8 cas terrain. Verdict :
`paraphrase-multilingual-mpnet-base-v2` (M2, dim 768) retenu.
Choix de la session externe (`all-mpnet-base-v2-onnx`, M5) empiriquement
réfuté : R@3=0.38 vs 0.88 pour M2.

Branche `feat/sprint6-embedder-audit` pushée sur origin (commits
jusqu'à `1e78b39`).

### T-Embedder2 (session courante, NON pushée)
Préparation migration en 4 sous-tâches.

**Tâche A** — Cleanup intent fantôme `ed1bf159...` désactivé via status
`completed`, A/B mesuré : R@3 passe de 0.875 à 1.000 sur M2 (+ cleanup).
ATTACH-correct stable à 4/8 (50%). Commit `82497a8`.

**Tâche B** — Décommissionnement `chroma_db/` legacy (105 entrées
orphelines, zéro caller prod). `git rm -r chroma_db/`, retrait
`chroma_path` de `config.py`, retrait inspection dans script bench.
Pytest 175/175. Commit `d99b623`.

**Tâche C** — Audit hard-codes dim 384 par DeepSeek hors-session. Zéro
blocker, deux faux positifs neutres dans `embedding/embedding_contract.py`
(check générique sur `self.dim`). Doc : `docs/sprint6/audit_deepseek_embedder.md`.

**Tâche D** — Script `scripts/migrate_embedder.py` rédigé par Sonnet
4.6 hors-session, audité par DeepSeek hors-session, patché 5 fois
(préservation None, list comprehension dummy, swap atomique tmpdir,
os.replace, validation IDs). Tests pytest associés (33 tests sur
fonctions pures).

**Tâche D-bis** — Test sur copie locale du palace a révélé 4 bugs
runtime du script (import `tempfile` manquant, truthiness numpy dans
`etape_b_inspection` et `etape_f_validation`, ENOTEMPTY sur `os.replace`
répertoire non-vide). Fixés. Patch C-ter (swap via 2 `os.rename`
séquentiels avec suffixe `.rollback-old`) valide le rollback de bout
en bout. Pytest 208/208. Commit `d780a66`.

État working tree : propre, hors `docs/sprint7/` (untracked, hors scope).

---

## Ce qui reste à faire — T-Embedder3

**Objectif** : exécuter la migration en prod et basculer ARIA sur M2.

1. **Test final sur copie pré-prod** (filet de sécurité).
2. **Arrêt service ARIA** (`sudo systemctl stop aria`).
3. **Migration prod** (script avec snapshot, dans tmux).
4. **Bascule `EMBEDDING_MODEL`** dans `config.py` (commit séparé).
5. **Redémarrage service** + validation `journalctl`.
6. **Test fumée Telegram** sur 4 messages (cuisine, voyage,
   salutation, cas piège C2 "Planifier des vacances en Normandie").
7. **Push de la branche** une fois tout validé.
8. **Rédaction `context_sprint_7_kickoff.md`** avec dettes workflow
   consolidées (cf. doc ChatGPT déjà rédigé, à intégrer + ajouts).
9. **Tag `sprint-6`** et merge `feat/sprint6-embedder-audit` → `main`
   sur origin.

Le doc protocole complet est `docs/sprint6/plan_migration_embedder.md`.

---

## Pourquoi nouvelle session

Le contexte de la session T-Embedder2 a accumulé : analyses qualitatives
profondes (analyse des 4 propositions de DeepSeek, débats sur swap
atomique, pédagogie utilisateur), 4 livraisons IA externes, 5 patchs
sur le script, intégration et tests multiples. La fenêtre est trop
chargée pour mener proprement la phase prod. Mieux vaut session
fraîche dédiée au run live.

---

## Contexte technique de référence

- Branche : `feat/sprint6-embedder-audit`, HEAD `d780a66`, non pushé
  depuis le commit `1e78b39` (= 5 commits locaux à pusher : `82497a8`,
  `d99b623`, `71a994a`, `a4b4545`, `d780a66`).
- Palace prod : `~/.mempalace/palace/`, 689 entrées (chiffre du
  10 mai 2026 — peut avoir crû depuis si Telegram a tourné),
  collection `mempalace_drawers`, dim 384.
- Modèle source : `all-MiniLM-L6-v2`. Modèle cible :
  `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
- Durée de migration attendue : 3-5 minutes (4.1 phrases/s mesuré
  sur la copie de bench).
- Snapshot tar.gz : ~25-30 Mo, créé automatiquement par le script
  sous `~/.mempalace/`.

---

## Dettes workflow ouvertes

Consolidées dans `docs/sprint7/` (untracked) par ChatGPT pendant la
session. À reprendre lors de la rédaction du `context_sprint_7_kickoff.md`.

Mises à jour vs liste sprint 6 :
- **Dette #8** (chroma_db legacy versionné) : FERMÉE par Tâche B.
- **Dette #9** (psutil non documentée) : toujours ouverte, à régler
  avec #10.
- **Dette #11** (nouvelle) : DeprecationWarning Python 3.14 sur
  `tar.extractall` sans `filter=` dans `migrate_embedder.py`. Cosmétique.
- **Dette #12** (nouvelle) : piège `os.replace` sur répertoire
  non-vide, à documenter dans la doc tribale du projet.
- **Dette #13** (nouvelle) : envoyer une consigne CLAUDE.md pendant
  un brief Tâche dilue le focus. Discipline workflow : consignes
  hors-brief ou en début de brief uniquement.

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 6, sous-sprint T-Embedder3 (run live prod).
> Voici le contexte de transition [PIÈCE JOINTE : ce document].
>
> T-Embedder2 est clos, branche `feat/sprint6-embedder-audit` à
> `d780a66`, non poussée. Le protocole d'exécution prod est dans
> `docs/sprint6/plan_migration_embedder.md`. Le script
> `scripts/migrate_embedder.py` a été testé end-to-end (migration,
> idempotence, rollback) sur copie locale du palace.
>
> Premier objectif : rédiger le brief T-Embedder3 — exécution prod
> en 6 étapes (test pré-prod sur copie fraîche, arrêt service,
> migration, bascule config.py, redémarrage, test fumée Telegram).
> Brief doit inclure 4 messages Telegram-test précis (notamment
> "Planifier des vacances en Normandie" pour valider empiriquement
> la fin du bug #18). Push de la branche en fin de tour si validation
> OK.
>
> Optionnel selon avancement : rédiger aussi le brief T-S6-Closure
> (tag sprint-6, merge feat → main, context_sprint_7_kickoff.md).