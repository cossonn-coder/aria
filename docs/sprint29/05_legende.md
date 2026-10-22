# Sprint 29 — Tronçon 05 : explication en légende sous chaque image

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_sprint29.md` §3.

## Objectif

L'explication LLM de chaque position part en légende de son diagramme ; le texte
final ne garde que l'ancre de la partie, la ligne « Niveau : » et le bloc Progression.

## Fichiers à toucher

### `execution/routers/chess_router.py`
- Après l'appel LLM (`result["text"]`, passé par `_to_english`) : découper le texte
  par entrées « Position N » (N = 1…len(images)). Le format est déjà imposé par la
  consigne (`_build_enriched`) : rendre le marqueur explicite et facile à couper, ex.
  « chaque entrée commence par “Position N —” en début de ligne ». Ajuster la consigne
  en conséquence (le LLM ne doit pas répéter la ligne factuelle de la légende).
- Légende d'une image = ligne factuelle actuelle (`_caption`) + saut de ligne + entrée N.
  Si > 1024 caractères : couper l'entrée à la dernière phrase complète qui tient, puis
  « … ».
- Texte final = ce qui reste hors entrées (ancre, « Niveau : ») + bloc Progression.
- Repli : si une entrée N est introuvable, **tout** reste comme aujourd'hui (légendes
  factuelles, texte complet) — pas de découpage partiel. `log.info` d'une ligne
  indiquant découpage OK / repli.
- La mémoire épisodique n'est pas concernée : `LLMExecutionRouter` écrit déjà le texte
  LLM complet avant ce découpage.

## Tests à ajouter (cas nominal) — `tests/execution/test_chess_router.py`

- LLM factice rendant ancre + « Position 1 — … » + « Position 2 — … » + « Niveau : … » :
  chaque image a sa légende factuelle + son entrée ; le texte final ne contient ni
  « Position 1 — » ni « Position 2 — » et finit par le bloc Progression.
- Entrée manquante → légendes et texte identiques au comportement actuel.
- Entrée de 1500 caractères → légende ≤ 1024, finit par « … ».

## Hors-scope (NE PAS faire)

- Pas de second appel LLM, pas de changement de l'interface Telegram (elle tronque déjà
  à 1024 en garde-fou).
- Ne pas toucher aux consignes hors format (contenu des explications inchangé).

## Critère de fin

`pytest tests/ -q` vert.
