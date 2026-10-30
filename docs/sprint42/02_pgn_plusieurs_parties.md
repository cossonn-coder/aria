# Sprint 42 — tronçon 02 : PGN de plusieurs parties, bilan groupé

À lire avant : `CLAUDE.md`, `docs/sprint42/00_etat.md`. Branche : `feat/sprint42-fichiers-telegram`.
Prérequis : tronçon 01 fait (un `.pgn` envoyé en fichier arrive comme un texte au kernel).

## Objectif

Un PGN contenant plusieurs parties (fichier `.pgn` ou collé) → **toutes** les parties sont
analysées, sans plafond (arbitrage Nico), et rendues en **une seule réponse groupée à la fin**
(arbitrage Nico) : les diagrammes de toutes les parties, puis le texte de chaque partie sous un
titre « Partie k — Blancs – Noirs (résultat) ». Une partie unique : comportement inchangé, à
l'octet près.

Durée constatée : 1,5 à 3 min par partie [n=2, `chess_analysis OK … duration=91.6s / 177.0s`,
parties de 92 demi-coups] ; ARIA est bloquée pendant ce temps (dette #112, acceptée).

## Constat au code (vérifié le 2026-10-30)

- `chess_coach/analysis.py:107` `parse_pgn(text)` lit **une** partie (`chess.pgn.read_game`
  une fois, à partir de la première ligne commençant par « [ »). `analyze(text, message, …)`
  (l. 433) s'appuie dessus.
- `execution/routers/chess_router.py:560` `ChessExecutionRouter.execute` : une partie →
  `analyze` → diagrammes → fiche `write_chess_game` (hash des coups) → progression →
  `llm_execution_router.execute` (REASONING, `forced_intent_name`, `skip_history`) →
  `_split_entries` (entrée « Position N » du LLM → légende du diagramme N) → `moves_line`,
  bloc progression → `{"text", "images"}`.
- `interfaces/telegram_interface.py` `send` : `images_text` = une `send_photo` par image,
  puis le texte (découpé à 4096).

## Comportement attendu

- Découpage du PGN en parties : nouvelle fonction (p. ex. `split_pgn(text) -> list[str]` dans
  `chess_coach/analysis.py`), même nettoyage que `parse_pgn` (lignes dépouillées), une chaîne
  par partie (`read_game` en boucle, ou découpe sur les lignes `[Event `). Le texte libre
  avant le premier en-tête (légende) est conservé comme `message` de chaque partie
  (détection de la couleur de Nico, `detect_color`).
- `execute` : 1 partie → chemin actuel inchangé. Plusieurs → le pipeline actuel tourne pour
  chaque partie (extraire le corps actuel dans une méthode par partie, sans en changer la
  logique), chaque partie ayant sa fiche et son appel LLM ; puis fusion :
  - images : concaténées dans l'ordre, légende préfixée « Partie k — » ;
  - texte : pour chaque partie, titre « Partie k — <White> – <Black> (<Result>) » puis son
    texte (lignes coups / progression comprises), parties séparées par une ligne vide ;
  - partie illisible : une ligne « Partie k — PGN illisible » à sa place, les autres continuent ;
  - log `chess_router multi games=N ok=M`.
- Annonce : dans `_handle_document` (tronçon 01), pour un `.pgn` de N ≥ 2 parties (compte des
  lignes commençant par `[White `), envoi immédiat de « ♟ N parties trouvées : je les analyse
  toutes et je t'envoie le bilan groupé à la fin (≈ 2 min par partie). » avant le kernel.

## Tests à ajouter (cas nominal)

- `split_pgn` : un texte de 2 parties → 2 chaînes, chacune lisible par `parse_pgn`.
- `tests/execution/test_chess_router.py` : PGN de 2 parties, `analyze` et LLM simulés comme dans
  les tests existants du fichier → une réponse, images des deux parties préfixées « Partie 1 — »
  / « Partie 2 — », texte avec les deux titres ; 2 fiches écrites. Un test existant à une partie
  reste vert sans modification.

## Hors scope

- Bilan transversal des parties (tendances, comparaison) : pas demandé.
- Plafond du nombre de parties, parallélisme, envoi au fil de l'eau.
- Concurrence des updates Telegram (#112).

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests verts ; tests existants de `test_chess_router.py`
inchangés et verts.
