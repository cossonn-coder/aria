# Sprint 67 — tronçon 02 : rapport des retours, alerte au démarrage, skill `/amelioration`

À lire avant : `CLAUDE.md`, `docs/sprint67/00_etat.md` (décisions 3, 4, 5),
`docs/sprint67/01_reactions.md` (format des fiches `aria_feedback`, `bridge.load_feedback`).

## Objectif

Exploiter les retours en conception : un script lit le palace (lecture seule), un hook
affiche une ligne d'alerte au démarrage de Claude Code dans aria, un skill
`/amelioration` transforme le rapport en axes de travail pour `/conception`.

## 1. `scripts/feedback_report.py` (commité)

- Lecture via `MempalaceBridge(store=mempalace_search, get_by_metadata=mempalace_get_by_metadata)`
  puis `bridge.load_feedback(since)` — même construction que `core/kernel.py`. **Aucune
  écriture** dans le palace (décision 5 : deux process qui écrivent = risque de corruption).
- `since` = horodatage lu sur la **première ligne** du rapport le plus récent
  `docs/amelioration/*.md` (tri par nom), de forme `Jusqu'au : <ISO>` ; aucun filtre s'il
  n'y a pas de rapport. Option `--since AAAA-MM-JJ` pour forcer. (Pas la date du nom de
  fichier : après un `/amelioration` le matin, les retours de la veille au soir et du
  matin même déclencheraient encore l'alerte.)
- Le mode rapport imprime en **première ligne** `Jusqu'au : <ISO de maintenant, UTC>`.
- Mode par défaut (rapport, sortie texte sur stdout, en français) :
  - en-tête : période, nb messages notés, nb 👍, nb 😢, nb autres réactions, nb sans
    réaction ;
  - puis chaque message **réagi**, 😢 d'abord : date, réaction, commentaire, demande,
    texte du message (tronqué à ~600 car.).
- `--alerte` : une seule ligne s'il y a au moins une réaction nouvelle :
  `ARIA : N nouveaux retours dont K 😢 depuis le AAAA-MM-JJ → lance /amelioration`.
  Rien du tout sinon. Toute exception en mode alerte : rien affiché, code 0 (le démarrage
  de Claude ne doit jamais être gêné). C'est le seul `try/except` justifié.
- Sortie par `print` : c'est un script CLI hors prod (comme
  `scripts/count_memory_by_wing.py`), pas du code du service.
- Logique de comptage / formatage dans une fonction pure testable
  (`build_report(entries, since) -> str`, `alert_line(entries, since) -> str`).

## 2. Hook SessionStart (local, `.claude/` est gitignoré)

Créer `.claude/settings.json` à la racine du projet (n'existe pas ; ne pas toucher
`settings.local.json`) :

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command",
                  "command": "cd /home/nico/Nextcloud/projects/aria && ./venv/bin/python scripts/feedback_report.py --alerte"}]}
    ]
  }
}
```

La sortie d'un hook SessionStart est injectée dans le contexte de la session : Claude
voit la ligne et la signale à Nico. Vérifier le format exact du hook auprès de la doc
Claude Code si besoin (agent `claude-code-guide`).

## 3. Skill `.claude/skills/amelioration/SKILL.md` (local, gitignoré)

Frontmatter `name: amelioration`, description en français (déclencheurs : « retours »,
« 👍 😢 », « qu'est-ce que Nico n'a pas aimé », « /amelioration »). Contenu, sur le
modèle de `.claude/skills/conception/SKILL.md` (le lire pour le ton) :

1. Lancer `./venv/bin/python scripts/feedback_report.py` (option `--since` si Nico la
   donne).
2. Rien de réagi → le dire en une ligne, ne pas écrire de rapport, s'arrêter.
3. Regrouper les 😢 par thème (texte trop long, erreur d'échecs, ton, mauvaise
   compréhension…), en s'appuyant sur les commentaires. Pour chaque thème, retrouver au
   grep le prompt ou le code qui a produit le message (lecture seule). Les 👍 disent ce
   qu'il faut garder.
4. Proposer des **axes de travail** classés (impact × fréquence), chacun avec : messages
   concernés, cause probable (fichier:ligne), piste, et la commande
   `/conception <axe>` à lancer. Un axe qui recoupe une dette existante (tableau du
   dernier `docs/sprintN/00_etat.md`) le dit.
5. Écrire `docs/amelioration/AAAA-MM-JJ.md` (date du jour ; suffixe `-2`, `-3` si le
   fichier existe déjà) : **première ligne = la ligne `Jusqu'au : …` du rapport, recopiée
   telle quelle**, puis période couverte, compteurs, axes proposés. Ce fichier sert de marque « déjà traité » au passage suivant. Le
   commiter seul (`docs(amelioration): …`), sans push.
6. Ne JAMAIS : modifier du code, des prompts, `soul.md` ; écrire dans le palace ;
   lancer `/conception` soi-même. Il propose, Nico choisit.

## Tests à ajouter (cas nominal)

`tests/scripts/test_feedback_report.py` (créer le dossier avec `__init__.py` si absent ;
regarder comment les tests existants importent un script de `scripts/`) :
`build_report` / `alert_line` sur 3 entrées fabriquées (une 👍, une 😢 commentée, une
sans réaction) → compteurs justes, 😢 listé avant 👍 ; `alert_line` vide quand aucune
réaction.

## Hors scope (ne PAS faire)

- Pas d'écriture palace, pas de marquage « traité » dans le palace.
- Pas de commande Telegram `/retours`.
- Pas d'auto-modification d'ARIA.
- Pas de modification des skills `/conception` ni `/sprint-auto`.

## Critère de fin

`pytest tests/ -q` vert ; `./venv/bin/python scripts/feedback_report.py --alerte` sort
sans erreur (vide tant qu'aucune réaction n'existe) ; `.claude/settings.json` et
`.claude/skills/amelioration/SKILL.md` présents (non commités : `.claude/` gitignoré, le
signaler dans le compte rendu).
