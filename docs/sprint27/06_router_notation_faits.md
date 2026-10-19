# Sprint 27 — Tronçon 06 : router — notation anglaise, faits fiables, idées d'ouverture

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md` (§ Correctif, retours de Nico sur
le texte), `docs/sprint27/audit_correctif.md` (constat « qualité du texte LLM »), puis
`execution/routers/chess_router.py` en entier. Le tronçon 05 a ajouté à `ExplosiveMove`
`offered`, une ligne de piège et les réponses raisonnables (vérifier les noms réels dans
`chess_coach/explosive.py`).

## Objectif

Le LLM invente (« fou en e6 », « d6 attaque le Bg5 », « sacrifie trois pions ») : il ne voit
pas l'échiquier et reçoit des chiffres trompeurs. Nico veut en outre la notation anglaise
et le lien avec les idées classiques de l'ouverture.

1. **Notation anglaise partout** (décision Nico, revient sur le choix français du
   sprint 26) : légendes des diagrammes, bloc de faits, consigne (« Notation anglaise :
   N, B, R, Q, K »). `_move_label` / `_format_line` / ligne du piège n'appellent plus
   `to_french`. `to_french` devient orphelin → supprimer `chess_coach/notation.py` et
   `test_to_french` (orphelins créés par ce changement) ; mettre à jour les commentaires
   d'en-tête qui parlent de notation française (`chess_router.py`, `chess_coach/__init__.py`).
2. **Pièces par camp** pour chaque position, tirées de `fen_before`, une ligne courte
   (ex. `pièces : blancs Kg1 Qd1 Ra1 Rf1 Bc1 Nc3 Nf3, pions a2 b2 e5 f2 g2 h2 ; noirs …`).
   But : le LLM ne peut plus placer une pièce inexistante.
3. **Occasion explosive** (bloc `_explosive_lines`) :
   - matériel : « offre le cavalier (3) » si `offered` > 0, sinon « sacrifie N pion(s) sur la
     ligne » ; rien si 0 ;
   - **suite du piège** : « si l'adversaire prend {prise} : {ligne numérotée} (il perd X pts) » ;
   - **réponses raisonnables** : une ligne par réponse (« si {réponse} : {ligne}, W % pour
     Nico »).
4. **Idées d'ouverture + gambit assumé** : nom de l'ouverture = `summary["opening"]`
   (déjà calculé dans `execute`, en-tête `Opening` ou slug de `ECOUrl`) + `ECO` (déjà dans
   `_header_lines`). Ajouter une consigne : relier chaque position aux **idées classiques
   de cette ouverture** (plans typiques, structures, pourquoi le coup s'inscrit ou non dans
   ces idées) ; un gambit d'ouverture choisi par Nico est un **choix assumé** (tempo,
   développement, sortir l'adversaire de sa théorie), pas une faute à corriger. Pas de
   consigne si l'ouverture est inconnue.
5. La consigne générale garde « Utilise uniquement les coups et lignes fournis ; n'invente
   aucun coup ni évaluation » et y ajoute « ni emplacement de pièce : fie-toi à la liste des
   pièces ».

## Fichiers

- `execution/routers/chess_router.py` (bloc enrichi, légendes, consignes).
- `chess_coach/notation.py` (suppression), `chess_coach/__init__.py` (commentaire).
- `tests/execution/test_chess_router.py`, `tests/chess_coach/test_chess_coach.py`.

Interdits : prompt AnalystAgent, `soul.md`, `memory/` (aucune écriture nouvelle).
La fiche `chess_game` (`summary.py`) n'est pas touchée.

## Tests (cas nominal)

- Le test router existant de l'occasion explosive : légende et bloc en notation anglaise
  (`Nd5`, pas `Cd5`), présence de la ligne de pièces, de la suite du piège et d'au moins une
  réponse raisonnable (adapter le faux `ExplosiveMove` / monkeypatch du test).
- Consigne d'ouverture présente quand `Opening`/`ECOUrl` est fourni, absente sinon.

## Hors scope

- Axes de travail façon RPG, appréciation du style de jeu : sprint 28 (« modèle joueur »).
- Erreur Groq 413 (message trop long → repli DeepSeek) : dette, ne pas raccourcir
  l'historique ici.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` mis à jour (tronçon 06 ✅ + §REPRISE).
