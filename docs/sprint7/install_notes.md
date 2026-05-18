# Sprint 7 — État d'installation MemPalace (post-T-Mempalace-Install-ARIA)

**Date** : 2026-05-14

## Bascule venv ARIA sur le fork

Le venv ARIA (`/home/nico/projects/aria/venv/`) pointe désormais
sur le fork local **en mode editable** :

- `mempalace.__file__` = `/home/nico/Nextcloud/projects/mempalace-fork/mempalace/__init__.py`
- Fork : `https://github.com/cossonn-coder/mempalace`
- Branche : `feat/configurable-embedder`
- Commit : `b8caf3259021d27c2689928458ac02d5a0defd01`
- Basé sur tag upstream : `v3.3.5`

## Réinstallation depuis zéro

Si le venv ARIA doit être recréé :

```bash
cd ~/Nextcloud/projects/aria
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # ou équivalent (dette #10)
pip install -e ~/Nextcloud/projects/mempalace-fork
```

Le `pip install -e` doit être fait APRÈS l'install des autres
dépendances, sinon pip réinstalle mempalace 3.3.5 depuis PyPI
et écrase le lien editable.

## Vérification

```bash
./venv/bin/python -c "import mempalace; print(mempalace.__file__)"
```

Doit retourner un chemin sous `~/Nextcloud/projects/mempalace-fork/`,
PAS sous `venv/lib/python3.13/site-packages/`.

## Dépendances en cascade ajoutées

- `sentence-transformers` (déjà présent pré-T-Mempalace-Install-ARIA,
  utilisé par `scripts/migrate_embedder.py` et le bench sprint 6).
- `torch`, `transformers`, `tokenizers` (tirés par sentence-transformers).
