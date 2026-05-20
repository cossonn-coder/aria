# Audit pin mempalace — sprint 13, dette #28

Tour audit pré-fix pour qualifier les trois pistes de résolution
du désalignement entre `requirements.txt` (pin `mempalace==3.3.0`)
et le venv editable actuel (mempalace 3.3.5 depuis fork
`feat/configurable-embedder`). Aucun fix dans ce tour — Nico
arbitre à partir du tableau §3.

Méthodo : lecture seule. Pas de `pip install`/`pip uninstall`,
pas de modification de `requirements.txt`. Observations
factuelles depuis le venv courant et le repo fork local.

---

## 1. État actuel constaté

### 1.1 Extrait `requirements.txt`

```text
5: chromadb>=1.5.0
6: mempalace==3.3.0
7: # pin explicite : couche HNSW C++ critique pour le palace, cf. dette #27 sprint 9
8: chroma-hnswlib==0.7.6
```

Le pin `mempalace==3.3.0` (ligne 6) est l'objet de la dette #28.

### 1.2 `pip show mempalace` (venv courant)

```text
Name: mempalace
Version: 3.3.5
Summary: Give your AI a memory — mine projects and conversations into a searchable palace. No API key required.
Home-page: https://github.com/MemPalace/mempalace
Author: milla-jovovich
License-Expression: MIT
Location: /home/nico/projects/aria/venv/lib/python3.13/site-packages
Editable project location: /home/nico/Nextcloud/projects/mempalace-fork
Requires: chromadb, pyyaml
```

Installation **editable** (PEP 660), pointant vers le repo fork
local. Le `Location` `/home/nico/projects/aria/venv/...` versus
le repo `/home/nico/Nextcloud/projects/aria/` est la dette #29
(probable symlink filesystem, hors-scope ici).

### 1.3 Origine git du repo mempalace local

Repo : `/home/nico/Nextcloud/projects/mempalace-fork`

```text
Remotes :
  nicofork  https://github.com/cossonn-coder/mempalace.git   (fork personnel Nico)
  origin    https://github.com/Mempalace/mempalace.git       (upstream officiel)

Branche checked out : feat/configurable-embedder
HEAD : b8caf3259021d27c2689928458ac02d5a0defd01 (b8caf32)
Sujet : feat(embedding): configurable embedder via model_name parameter
Date : 2026-05-13 18:41:26 +0200

Working tree clean (pas de modification non commitée vérifiée
au moment de l'audit).
```

### 1.4 Position de `b8caf32` vs tag `v3.3.5` upstream

```text
v3.3.5 → d0163a7 (Merge PR #1434 chore/release-3.3.5-prep, 2026-05-10)

git merge-base b8caf32 v3.3.5 → d0163a7
git log v3.3.5..b8caf32 → b8caf32 (1 seul commit)
git log b8caf32..v3.3.5 → (vide)
```

**Diagnostic structurel : `b8caf32` = `v3.3.5` upstream + 1 commit
divergent.** Le commit `b8caf32` ajoute la feature `model_name`
configurable et le mécanisme `.mempalace-embedder.json`. Il
touche 4 fichiers (`backends/chroma.py`, `embedding.py`,
`pyproject.toml`, `tests/test_embedding_configurable.py`,
+329/-25).

### 1.5 Présence de `mempalace==3.3.5` sur PyPI

```text
$ pip index versions mempalace
mempalace (3.3.5)
Available versions: 3.3.5, 3.3.4, 3.3.3, 3.3.2, 3.3.1, 3.3.0, ...
  LATEST: 3.3.5
```

**`mempalace==3.3.5` existe sur PyPI** — mais correspond à
`d0163a7` (release upstream), **pas à** `b8caf32` (fork local).
La 3.3.5 PyPI **ne contient pas** la feature configurable
embedder ni le marker `.mempalace-embedder.json`.

### 1.6 Implication critique — piège silencieux confirmé et étendu

Le palace prod actuel (`~/.mempalace/palace/`) contient le
marker `.mempalace-embedder.json` qui résout au modèle
`paraphrase-multilingual-mpnet-base-v2` (mpnet-768, cf. audit
drift §1 et CLAUDE.md). **Ce marker est lu par le code du
commit `b8caf32` uniquement.** Sans `b8caf32`, le palace
re-tomberait sur le fallback MiniLM-L6 (dim 384), ce qui
casserait :

- l'integrity check d'ouverture du palace (mismatch de dim
  768 vs 384 entre embeddings persistés et EF résolue) ;
- toute requête vectorielle (incohérence d'espace) ;
- les futures écritures (encodées en 384 dans une collection
  HNSW pré-allouée 768).

Conclusion : **toute install qui résout autre chose que
`b8caf32` casse le palace prod**. Ce n'est pas un piège qui
naît du désalignement entre 3.3.0 pin et 3.3.5 installée —
c'est un piège qui naît du désalignement entre toute
version PyPI tagguée et le SHA du fork. Le passage d'une
3.3.5 PyPI au fork n'est pas un simple upgrade de version.

---

## 2. Analyse des trois pistes

### 2.1 Piste A — Pin `mempalace==3.3.5` dans `requirements.txt`

**Changement concret** : remplacer ligne 6 par
`mempalace==3.3.5` (la version existe sur PyPI, vérifié §1.5).

**Comportement d'un `pip install -r requirements.txt` from
scratch** : pip télécharge la 3.3.5 PyPI (= `d0163a7`),
**sans** le commit `b8caf32`. Pas de marker handling, pas de
`model_name` parameter. À la première ouverture du palace
prod existant : crash sur mismatch dim 768/384 OU silencieux
sur fallback MiniLM = corruption d'espace vectoriel.

**Reproductibilité** : excellente (résolution PyPI standard,
SHA implicite à `d0163a7`).

**Traçabilité** : on sait qu'on a la 3.3.5 PyPI, mais **on
ignore** qu'il manque le patch fork — c'est une asymétrie
d'information identique au bug du smoke pattern ST sprint 12.

**Sensibilité fork** : aucune (le fork peut bouger, on
reste sur la 3.3.5 PyPI). Mais c'est précisément le
problème : la prod **dépend** du fork.

**Effort / maintenance** : nul à poser, mais **inadéquat
par construction** — laisse le palace prod cassé sur toute
réinstall.

**Verdict A** : ❌ rejet de fond. Faux fix. Aligne le pin
sur la version installée par numéro, sans aligner le SHA
réellement nécessaire. Le désalignement est plus profond
qu'un simple numéro de version.

---

### 2.2 Piste B — Retrait de mempalace de `requirements.txt` + étape install séparée

**Changement concret** :

- Supprimer la ligne `mempalace==3.3.0` de `requirements.txt`.
- Documenter dans `README.md` (ou un `INSTALL.md` dédié) une
  étape :

  ```bash
  git clone https://github.com/cossonn-coder/mempalace.git ../mempalace-fork
  cd ../mempalace-fork && git checkout feat/configurable-embedder
  cd /path/to/aria && ./venv/bin/pip install -e ../mempalace-fork
  ```

**Comportement d'un `pip install -r requirements.txt` from
scratch** : aucune mempalace installée à la fin. L'install
échoue dès le premier `import mempalace` (au démarrage
d'`aria.service`). **Échec bruyant et immédiat** au lieu
d'un piège silencieux. La doc d'install rend le sujet
explicite : « tu dois installer mempalace à part, depuis ce
fork, sur cette branche ».

**Reproductibilité** : moyenne. Dépend du respect de la
procédure manuelle. Sur une CI, il faudrait scripter la
clone + checkout + install — surface d'erreur supplémentaire.

**Traçabilité** : faible par défaut (la doc dit « branche
`feat/configurable-embedder` », pas un SHA précis ; la
branche peut avancer). Améliorable en mentionnant le SHA
attendu dans la doc, mais c'est une discipline humaine, pas
une garantie machine.

**Sensibilité fork** : élevée. Si la branche fork bouge
(ce qu'elle peut, c'est ton fork personnel Nico), une
réinstall ramène un état différent sans alerte.

**Effort / maintenance** : moyen à poser (doc à rédiger,
README à mettre à jour, validation manuelle de la procédure).
Maintenance : à chaque évolution du fork, la doc doit suivre.

**Sécurité / accès** : aucune dépendance à un secret ; le
fork est public sur cossonn-coder/mempalace.

**Verdict B** : ⚠ acceptable. Échec bruyant = bon. Mais
laisse la traçabilité SHA hors de `requirements.txt`, donc
hors du périmètre versionné côté ARIA. Le repo aria ne
connaît plus précisément quelle version de mempalace il
tourne avec — c'est un recul par rapport au pin actuel,
même cassé.

---

### 2.3 Piste C — Pin via URL git directe dans `requirements.txt`

**Changement concret** : remplacer ligne 6 par une URL git
de la forme :

```text
mempalace @ git+https://github.com/cossonn-coder/mempalace.git@b8caf3259021d27c2689928458ac02d5a0defd01
```

(SHA complet, le format `git+https://...@<sha>` est PEP 440
compatible et géré nativement par pip.)

Variante moins stricte : `@feat/configurable-embedder`
(branche au lieu de SHA), mais cela perd la garantie SHA et
réintroduit le défaut traçabilité de B.

**Comportement d'un `pip install -r requirements.txt` from
scratch** : pip clone le repo `cossonn-coder/mempalace`,
checkout le SHA `b8caf32`, installe (mode non-editable,
build wheel localement). **Le venv obtient exactement le
même code que la prod actuelle.** Pas de marker à ré-
auto-résoudre.

**Reproductibilité** : excellente. Le SHA est immuable
(garantie git). Toute machine qui réinstall avec ce
`requirements.txt` obtient le même octet.

**Traçabilité** : excellente. `requirements.txt` versionné
côté aria documente précisément le SHA mempalace utilisé. Un
audit ultérieur du couple `aria@X / mempalace@Y` est trivial
(`git log`, `git blame`).

**Sensibilité fork** : nulle au sens du déplacement de la
branche (le SHA est figé) — mais sensible à la **disponibilité
du remote**. Si `cossonn-coder/mempalace` disparaît / est
rendu privé / change de nom, l'install casse. Mitigation
possible (cache pypi local, ou tag annoté `v3.3.5+aria.1`
poussé sur le fork) hors-scope de cet audit.

**Effort / maintenance** :
- Pose : 1 ligne à éditer dans `requirements.txt`. Validation
  via `pip install --dry-run` ou une réinstall dans un venv
  jetable.
- Maintenance : chaque évolution volontaire de la feature
  `configurable-embedder` (commit ajouté au fork) implique
  un **bump du SHA** dans `requirements.txt`. C'est une
  charge **explicite et tracée** — symétrique du pin
  `chroma-hnswlib==0.7.6` posé sprint 12, qui exige aussi un
  bump manuel à chaque upgrade.

**Perte du mode editable** : avec un pin URL git, pip
installe en mode build (non-editable). Une modification
locale du fork ne sera **plus reflétée** dans le venv sans
réinstall. C'est un changement de workflow significatif si
le fork est encore en développement actif. Mitigation :
garder localement un `pip install -e ../mempalace-fork` en
override post-install pour le dev, et documenter que la
reproductibilité PyPI/CI passe par le pin URL. Possible mais
ajoute du soin.

**Sécurité** : pin via HTTPS public, pas de credentials
requis. Pas de signed commits sur le fork actuellement —
threat model identique à PyPI (on fait confiance à la
plateforme d'hébergement).

**Verdict C** : ✅ adéquat sur le fond. Reproductibilité et
traçabilité maximales. Compromis : perte du mode editable
(workflow dev impacté) et dépendance à la persistance du
remote.

---

## 3. Tableau comparatif synthétique

| Critère                                | A : pin 3.3.5 PyPI | B : retrait + install séparé | C : pin URL git @SHA |
|----------------------------------------|--------------------|------------------------------|----------------------|
| Install from scratch fonctionne        | ❌ palace cassé silencieusement (mismatch dim) | ⚠ échoue bruyamment, doc requise | ✅ install correcte, palace ouvre |
| Reproductibilité bit-à-bit             | ✅ via PyPI         | ❌ branche peut bouger         | ✅ SHA immuable        |
| Traçabilité versionnée côté aria       | ⚠ trompe (numéro ok, SHA ≠) | ❌ hors `requirements.txt` | ✅ SHA dans le pin     |
| Sensibilité aux mouvements du fork     | ✅ insensible (mauvais ici) | ❌ très sensible (branche live) | ✅ insensible (SHA figé) |
| Effort de pose                         | ✅ trivial          | ⚠ doc à écrire                | ✅ 1 ligne             |
| Maintenance évolutions fork            | n/a (cassé)        | ⚠ doc à maintenir             | ⚠ bump SHA manuel     |
| Préserve mode editable pour dev        | n/a                | ✅ oui                         | ❌ non (workaround possible) |
| Dépendance à un remote hors PyPI       | ✅ aucune           | ⚠ doc référence fork          | ⚠ remote fork requis  |
| Échec install = bruyant ?              | ❌ silencieux       | ✅ bruyant                     | ✅ bruyant si SHA absent |
| Adéquat au problème de fond            | ❌                  | ⚠                              | ✅                    |

---

## 4. Recommandation

**Préférence motivée : Piste C (pin URL git @SHA)**, avec
override manuel `pip install -e ../mempalace-fork` post-
install pour préserver le mode editable en dev.

Trois raisons :

1. **C est la seule piste qui résout le vrai problème.** Le
   désalignement n'est pas entre `3.3.0` et `3.3.5` — c'est
   entre `d0163a7` (v3.3.5 upstream) et `b8caf32` (fork
   feature). Aucun numéro de version PyPI ne discrimine
   ces deux SHA. Seul un pin SHA le fait.

2. **C aligne `requirements.txt` sur le rôle qu'il doit
   jouer** : être la spec versionnée et exécutable de
   l'environnement prod. B externalise cette spec dans une
   doc humaine, ce qui dégrade le contrat d'install et
   reproduirait à terme une asymétrie d'information du
   même type que celle de #25 (pattern smoke ST).

3. **C est symétrique du pin `chroma-hnswlib==0.7.6`
   sprint 12** (#27). Même philosophie : épingler ce qui ne
   doit pas bouger silencieusement, accepter la charge de
   bump manuelle quand on décide délibérément de monter.

**Points d'attention pour le tour de fix qui suivra**
(à cadrer ailleurs, hors livrable ici) :

- Vérifier que `pip install` depuis URL git ne ramène pas
  d'écart par rapport au venv editable actuel (test :
  install dans un venv jetable, comparer `pip show` et
  exécuter le smoke runbook §6).
- Écrire un commentaire de traçabilité au-dessus du pin,
  identique en style au pin `chroma-hnswlib` (cf.
  `requirements.txt:7`).
- Documenter dans CLAUDE.md ou un `INSTALL.md` la procédure
  dev (override `pip install -e ../mempalace-fork`) si on
  veut conserver le mode editable pour itérations sur le
  fork.
- Statuer sur l'opportunité de pousser un tag annoté
  `v3.3.5+aria.1` (ou nommage équivalent) sur le fork pour
  ne pas dépendre uniquement du SHA brut. Optionnel —
  marginal en valeur ajoutée, à arbitrer.

Nico tranche. Aucun fix n'est appliqué dans ce tour.

---

## Annexe — commandes utilisées (reproductibilité)

```bash
# Extrait requirements.txt avec contexte
grep -n -B1 -A2 -i 'mempalace\b' requirements.txt

# Venv courant
./venv/bin/pip show mempalace
./venv/bin/pip index versions mempalace

# État du repo fork
cd /home/nico/Nextcloud/projects/mempalace-fork
git remote -v
git branch --show-current
git log -1 --format='%H%n%h%n%s%n%ci'

# Position de HEAD vs tag v3.3.5
git log -1 --format='%H%n%h%n%s%n%ci' v3.3.5
git merge-base b8caf32 v3.3.5
git log --oneline v3.3.5..b8caf32
git log --oneline b8caf32..v3.3.5

# Contenu du commit divergent
git show --stat b8caf32
```

Lecture seule, état du venv et du fork inchangés après audit.
