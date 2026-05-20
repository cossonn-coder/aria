# Installation et workflow dev — `mempalace`

`mempalace` n'est pas installé depuis PyPI mais depuis un fork
épinglé par SHA dans `requirements.txt`. Cette page documente
la procédure standard, l'override editable pour le dev, et la
règle de bump du SHA.

Contexte de la décision : sprint 13, dette #28. Voir
`docs/sprint13/audit_pin_mempalace.md` pour le diagnostic
(piste C retenue : pin URL git @SHA) et `requirements.txt`
ligne `mempalace @ git+...@b8caf32...` pour la spec actuelle.

---

## 1. Install standard

Procédure nominale, pour une machine neuve ou une CI :

```bash
cd ~/Nextcloud/projects/aria
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

pip clone le fork (`https://github.com/cossonn-coder/mempalace.git`),
checkout le SHA pinné, build un wheel et l'installe. Le mode
d'installation est **non-editable** (build pur) — toute
modification du fork local **n'est pas reflétée** dans ce venv.

Pour vérifier ce qui est effectivement installé :

```bash
./venv/bin/pip show mempalace
# Version: 3.3.5
# Location: .../venv/lib/python3.13/site-packages
# (PAS de ligne "Editable project location" en mode build)
```

Cette procédure suffit pour faire tourner ARIA en prod. Le
mode build est volontaire : il garantit que le venv est
reproductible à partir du seul `requirements.txt`.

---

## 2. Override editable pour le dev sur le fork

Workflow dev attendu : itérer localement sur le fork
`cossonn-coder/mempalace` puis tester depuis ARIA sans
rebuild systématique. Pour cela, après l'install standard,
remplacer la copie pinnée par un install editable du repo
local :

```bash
# Pré-requis : fork cloné en local
# ../mempalace-fork = /home/nico/Nextcloud/projects/mempalace-fork
# (chemin de référence — adapter si le fork est cloné ailleurs)

./venv/bin/pip install -e ../mempalace-fork
```

Après cette commande, `pip show mempalace` affiche une ligne
`Editable project location: /home/nico/Nextcloud/projects/mempalace-fork`
et toute modification du fork est immédiatement visible côté
ARIA (pas de réinstall nécessaire). C'est l'état attendu de
la machine de Nico.

Conséquence assumée : un `pip install -r requirements.txt`
ultérieur (par ex. au moment d'ajouter une nouvelle dépendance
au repo aria) **écrasera** l'install editable et reviendra
au SHA pinné. Il faut alors re-jouer la commande
`pip install -e ../mempalace-fork`.

---

## 3. Règle de bump SHA

Toute évolution volontaire du fork (commit ajouté sur la
branche `feat/configurable-embedder` ou autre) qu'ARIA doit
prendre en compte **doit** être reflétée par un bump du SHA
dans `requirements.txt`, et committée côté repo aria.

Procédure :

1. Pousser le nouveau commit sur le fork
   (`cossonn-coder/mempalace`).
2. Vérifier le SHA exact : `git rev-parse HEAD` dans le repo
   fork.
3. Mettre à jour la ligne `mempalace @ git+...@<SHA>` dans
   `requirements.txt` du repo aria.
4. Valider par une install fresh dans un venv jetable +
   smoke runbook `docs/sprint7/runbook_t_mempalace_live.md`
   § 6.
5. Committer côté aria avec un message qui référence le
   commit fork (sujet du commit fork, SHA court).

**Interdit** : laisser le venv editable diverger silencieusement
du SHA pinné. Si la machine de Nico tourne sur un fork plus
récent que celui pinné, toute nouvelle install (CI, autre
machine, réinstall venv) se retrouvera désynchronisée — c'est
exactement le piège que la dette #28 a corrigé.

**Optionnel** : pousser un tag annoté sur le fork
(ex. `v3.3.5+aria.1`) pour ne plus dépendre du SHA brut.
Non requis tant que le fork reste mono-mainteneur.
