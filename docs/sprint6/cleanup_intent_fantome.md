# Cleanup intent fantôme — T-Embedder2 Tâche A

**Sprint 6 / sous-sprint embedder, tour 2.** Branche
`feat/sprint6-embedder-audit`. Action exécutée : passage du status
de l'intent fantôme `ed1bf159…` à `completed` dans
`~/.aria/intents.json`.

---

## 1. Intent traité

| Champ | Valeur |
|---|---|
| ID complet | `ed1bf159-79ad-49a9-9f8f-689d44b43743` |
| Name | `Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à` (60 caractères, tronqué brut) |
| Status avant | `active` |
| Status après | `completed` |
| Actions avant | 1 (`split_from_context:Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à découper, un couteau de cuisine, un éco`) |
| Actions après | +1 (`deactivated_T-Embedder2:2026-05-09T09:50:37`) |
| Origine du bug | Dette #23 — branche SPLIT du pipeline produit `name = message[:60]` quand `extract_intent_name` n'est pas appelé (cas C5_T4 audit sprint 5 §7) |

Snapshot conservé à `~/.aria/intents.json.bak.20260509-095037`
(40 KB, conforme à l'état pré-cleanup).

---

## 2. Méthode

**Désactivation par `status: completed` plutôt que suppression dure.**

- `IntentRecallEngine.resolve` ne sélectionne que `intents` avec
  `status == "active"` (intent_recall_engine.py:73). Mettre l'intent
  en `completed` suffit à le retirer du pool de matching, sans perdre
  l'historique.
- L'entrée reste auditable dans `intents.json` avec sa trace
  `actions_history` qui conserve à la fois la création
  (`split_from_context:...`) et la désactivation
  (`deactivated_T-Embedder2:<iso>`).
- Aucun risque de régression sur la suppression d'IDs référencés
  ailleurs (rooms ChromaDB par intent_id) : on ne touche pas au store
  vectoriel.

Le script `scripts/embedder_bench/cleanup_intent_fantome.py` :
- Liste de préfixes d'IDs **en dur** dans le code (pas en CLI) — la
  liste vit dans le diff git, pas dans une invocation manuelle.
- Snapshot timestamp avant toute modif.
- Idempotent : skip silencieux si l'intent est déjà `completed`.
- Écriture atomique (tmp + `os.replace`).

---

## 3. Étude A/B sur les 4 états

Le bench a été relancé sur 4 configurations pour isoler les
contributions :

| État | n_actifs | Lecture |
|---|---:|---|
| **A** : M0 + ghost actif | 62 | État d'origine (sprint 5) — baseline |
| **B** : M0 + cleanup | 61 | Cleanup seul, modèle inchangé |
| **C** : M2 + ghost actif | 62 | Modèle seul (= bench T-Embedder1) |
| **D** : M2 + cleanup | 61 | État cible T-Embedder3 (cleanup + modèle) |

Le bench a été modifié pour filtrer `status == "active"` (cf.
`benchmark_quality.py` `load_intents`), conformément à la sémantique
de `IntentRecallEngine`.

### 3.1 Métriques agrégées

| État | Recall@1 | Recall@3 | ATTACH-correct | Gap moyen |
|---|---:|---:|---:|---:|
| A — M0 ghost | 0.250 | 0.625 | 2/8 | −0.077 |
| B — M0 cleanup | **0.375** | 0.625 | 2/8 | −0.077 |
| C — M2 ghost | 0.625 | 0.875 | **4/8** | **+0.238** |
| **D — M2 cleanup** | 0.625 | **1.000** | 4/8 | +0.238 |

### 3.2 Détail par cas — M0 avant/après cleanup

`✓` = ATTACH oracle. `✗` = ATTACH faux. `S` = SPLIT/CREATE. Cas
modifiés en gras.

| Cas | M0 ghost top-1 | Score | Rang oracle | M0 cleanup top-1 | Score | Rang oracle |
|---|---|---:|---:|---|---:|---:|
| C1 | *carottes dans jardin* ✗ | 0.642 | 2 | *carottes dans jardin* ✗ | 0.642 | 2 |
| **C2** | ***Dans ma cuisine j'ai...*** | 0.502 | 52 | *Pourquoi elle ne germent pas* ✗ | 0.466 | 51 |
| C3 | recettes santé culinaire ✓ | 0.540 | 1 | recettes santé culinaire ✓ | 0.540 | 1 |
| C4 | *semis en intérieur* ✗ | 0.496 | 28 | *semis en intérieur* ✗ | 0.496 | 27 |
| C5_T1 | *Pourquoi elle ne germent pas* ✗ | 0.535 | 2 | *Pourquoi elle ne germent pas* ✗ | 0.535 | 2 |
| C5_T2 | *Pourquoi elle ne germent pas* ✗ | 0.507 | 6 | *Pourquoi elle ne germent pas* ✗ | 0.507 | 5 |
| C5_T3 | recettes santé culinaire ✓ | 0.575 | 1 | recettes santé culinaire ✓ | 0.575 | 1 |
| **C5_T4** | ***Dans ma cuisine j'ai...*** | 0.824 | 2 | **recettes santé culinaire** | **0.441** | **1** (S) |

**Lecture M0 :**
- C2 : le top-1 ghost à 0.502 disparaît. Le nouveau top-1 est aussi
  faux (`Pourquoi elle ne germent pas` à 0.466). L'oracle reste
  inaccessible (rang 51) — l'espace M0 est trop plat.
- **C5_T4 (basculement majeur)** : top-1 passe du ghost à 0.824 → à
  l'oracle à 0.441. Décision passe d'`ATTACH faux` à `SPLIT` (best <
  0.45). Pas un ATTACH-correct, mais l'oracle est désormais rang 1 et
  le score est à 0.009 du seuil — un signal exploitable par re-rank
  ou ajustement de seuil.
- C5_T2 : oracle progresse de rang 6 → 5 (le ghost n'est plus dans
  les top 5).
- Les autres cas ne sont pas affectés : le ghost n'apparaissait pas
  dans leur top-5 originel.

### 3.3 Détail par cas — M2 avant/après cleanup

| Cas | M2 ghost top-1 | Score | Rang oracle | M2 cleanup top-1 | Score | Rang oracle |
|---|---|---:|---:|---|---:|---:|
| C1 | *carottes dans jardin* ✗ | 0.814 | 3 | *carottes dans jardin* ✗ | 0.814 | 3 |
| C2 | réservation voyage ✓ | 0.578 | 1 | réservation voyage ✓ | 0.578 | 1 |
| C3 | recettes santé culinaire ✓ | 0.646 | 1 | recettes santé culinaire ✓ | 0.646 | 1 |
| C4 | salutation (S) | 0.362 | 1 | salutation (S) | 0.362 | 1 |
| C5_T1 | *recette houmous* ✗ | 0.599 | 2 | *recette houmous* ✗ | 0.599 | 2 |
| C5_T2 | recettes santé culinaire ✓ | 0.610 | 1 | recettes santé culinaire ✓ | 0.610 | 1 |
| C5_T3 | recettes santé culinaire ✓ | 0.680 | 1 | recettes santé culinaire ✓ | 0.680 | 1 |
| **C5_T4** | ***Dans ma cuisine j'ai...*** | 0.892 | 4 | ***méthodes de cuisson saines*** | **0.580** | **3** |

**Lecture M2 :**
- C5_T4 : top-1 ghost (0.892) → top-1 *méthodes de cuisson saines*
  (0.580). Toujours un faux ATTACH, mais l'oracle progresse de rang 4
  → 3. **C'est ce qui fait passer R@3 de 0.875 à 1.000.**
- Aucun autre cas modifié.

---

## 4. Conclusion — isolation des contributions

| Levier | Cas ATTACH-correct gagnés | Cases R@1 améliorés | Cases R@3 améliorés |
|---|---|---|---|
| **Cleanup seul** (A → B) | 0 | C5_T4 (sur M0) | aucun (déjà dans top 3) |
| **Modèle seul** (A → C) | C2, C5_T2 (= 2) | C2, C5_T2, C5_T4 | C5_T2 |
| **Cleanup + modèle** (A → D) | C2, C5_T2 (= 2) | C2, C5_T2, C5_T4 | C5_T2, C5_T4 |

**Le cleanup ne corrige aucun ATTACH** : les cas faux restent faux,
juste l'identité du faux match change (le ghost cesse d'être top-1
sur C5_T4 mais aucun nouveau ATTACH-correct n'apparaît). En revanche,
**il améliore les rangs oracle** sur C5_T4 et C5_T2, ce qui est
précieux comme entrée pour un re-ranker LLM en T-Match.

**Le modèle M2 corrige 2 cas en ATTACH supplémentaires** (C2 et
C5_T2), avec ou sans cleanup — c'est l'effet attendu du passage à un
embedder multilingue robuste.

**Combinés (état D, cible T-Embedder3) :**
- ATTACH-correct passe de 2/8 (25 %) à 4/8 (50 %).
- R@3 passe de 0.625 à **1.000** — *tous* les oracles sont désormais
  dans les 3 meilleurs candidats du modèle, condition nécessaire à
  l'efficacité d'un re-ranker LLM en T-Match.
- Les cas durs résiduels (C1, C5_T1, C5_T4) ont leur oracle aux rangs
  3 / 2 / 3 — un re-ranker à 3 candidats les corrige tous.

**Effet net du cleanup au-delà des métriques** : élimine la pollution
permanente sur tout message contenant « cuisine » / « cocotte » /
« planche » qui aurait continué à matcher le ghost — y compris hors
des 8 cas terrain testés. Bénéfice qualitatif non quantifié ici mais
non négligeable.
