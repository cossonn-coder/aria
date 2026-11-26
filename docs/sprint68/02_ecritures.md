# Sprint 68 — tronçon 02 : écritures du bilan, mesurées puis allégées

Lire d'abord `CLAUDE.md`, `docs/sprint68/00_etat.md`, puis `audit_joueur_du_bas.md` §6.5.
**Palace prod : exception au calibrage faible.** Aucune écriture sur `/home/nico/.mempalace/palace`
pendant ce tronçon ; ce qui est écrit en prod (documents, métadonnées, ids) ne change pas.

## Objectif

Savoir combien coûte chaque écriture d'un bilan de partie, puis réduire ce qui coûte, sans
changer ce qui est écrit.

## Écritures d'un bilan (vérifiées au code le 2026-11-25)

Toutes passent par `memory/writer.py` (règle 1) :

- `write_chess_game(summary_text(...), game_hash, extra=summary, room=..., timestamp=...)` et,
  après le LLM, `update_chess_game_minis(doc_id, minis_json)` (`chess_router._execute_game`).
- `write_interaction(text=f"USER:\n{message}\n\nARIA:\n{result}", ...)` dans
  `execution/routers/llm_router.py:_run_pipeline` étape 10 : `message` est tout le prompt enrichi.
- La conversation (`write_conversation_turn`, même fonction, juste après).
- Côté Telegram, `write_sent_message` par message envoyé (`interfaces/telegram_interface.py:674`),
  appelé par message (texte, chaque image).

Journal [n=1] : diagrammes + résumé + `write_chess_game` 16 s ; `write_interaction` 4 s ;
conversation 7 s. Non ventilé : le tronçon 01 ajoute les durées par étape.

## À faire

1. **Mesure en bac à sable.** Script `docs/sprint68/mesure_ecritures.py` : copie du palace
   (`cp -a` vers un dossier temporaire du scratchpad ou `/tmp`), `config.mempalace_path` pointé
   sur la copie **avant** tout import qui ouvre le palace, puis chronométrage de chaque fonction
   ci-dessus avec des données de taille réelle (une fiche existante relue par le bridge comme
   modèle ; un prompt de ~9 000 caractères pour `write_interaction`). 3 répétitions par mesure.
   Vérifier en tête de script que le chemin effectif n'est pas le palace prod (sinon `sys.exit`).
   Résultats dans `docs/sprint68/mesure_ecritures.txt`, chaque chiffre avec sa limite
   (`[n=3]`, machine chargée…).
2. **Allègement**, seulement sur ce que la mesure désigne, sans changer documents, métadonnées
   ni ids. Pistes admises : éviter un double calcul d'embedding du même texte, une réouverture de
   collection à chaque appel, une relecture inutile avant écriture ; déplacer une écriture
   non bloquante après l'envoi de la réponse **seulement** si c'est déjà le cas d'une écriture
   voisine dans le même module (pas de nouveau thread de fond inventé).
3. **Si le seul gain possible change ce qui est écrit** (texte plus court pour
   `write_interaction`, une écriture en moins…) : ne pas le faire. Le noter dans `00_etat.md`
   (dette 68-x, chiffres à l'appui) et s'arrêter là : c'est un arbitrage de Nico.

## Tests

Si du code de prod change : un test du cas nominal (même document et mêmes métadonnées écrits
qu'avant, sur un store factice). Pas de test si seule la mesure est livrée.

## Hors scope

Rappels mémoire (tronçon 01), recherche explosive (03), échiquier (04-05). Pas de nouveau
backend, pas de changement de modèle d'embedding.

## Critère de fin

`mesure_ecritures.txt` livré ; `pytest tests/ -q` vert ; soit un allègement mesuré (avant /
après sur la copie), soit une dette chiffrée dans `00_etat.md`.
