# Sprint 51, tronçon 03 — temps et coups longs

## Objectif
Quand Nico envoie une partie **avec horloges**, c'est qu'il a peiné à trouver ses coups dans
le temps (décision de Nico). ARIA :
1. écrit une ligne **Temps** factuelle (code) ;
2. **analyse ses 3 réflexions les plus longues** (≥ 20 s) : miniature, verdict écrit par le
   code, entrée du LLM « Pour jouer vite : ».
Sans horloge, le LLM n'a plus le droit d'inventer une cause liée au temps (au run du
2026-11-06, il a conclu « gestion du temps » sans aucune donnée).

Chiffres de la partie de référence : `docs/sprint51/audit_conversion.md` §1.c.
`PlyAnalysis.clock` (= `node.clock()`, temps restant en s) est déjà rempli par
`analyze_game` quand le PGN a des `%clk`, `None` sinon.

## À faire

### 1. Nouveau module `chess_coach/clock.py` (fonctions pures)
- **Temps par coup** : pour chaque ply, temps restant du même camp avant ce coup − `clock` +
  incrément. Avant son 1er coup, un camp a la base de `TimeControl` (`"600"` ou `"600+5"` ;
  autre format → temps du 1er coup `None`). `None` si `clock` est `None`.
- **Coups longs** : coups de Nico à ≥ 20 s, les **3 plus longs**, rendus dans l'ordre
  chronologique.
- **Verdict** d'un coup long (texte), à partir de `second_gap`, `loss`, `difficulty` (Maia,
  `None` avant le coup 10) et de l'Elo de Nico (en-tête, peut manquer) :
  - faits : « plusieurs coups gardaient l'avantage » si `second_gap < 5` ; « un seul coup
    tenait » si `second_gap ≥ 15` ; « coup à ta portée (Maia ≈ 1226) » si
    difficulté ≤ Elo + 100 ; « coup difficile pour ton niveau (Maia ≈ 1850) » si
    difficulté ≥ Elo + 300 ; sinon « Maia ≈ X » ; rien si donnée absente ;
  - conclusion, dans cet ordre : `second_gap < 5` et `loss < 10` → « un coup simple
    suffisait » ; sinon `second_gap ≥ 15` ou coup difficile → « réflexion justifiée » ;
    sinon pas de conclusion.
- **Ligne Temps** (une ligne, code), format :
  `⏱️ Temps : toi 10,9 s par coup, adversaire 7,4 s. Dès le coup 9 (début de la période
  gagnante) : pendules 9:43 contre 9:31, puis toi 12,4 s par coup, adversaire 8,1 s.
  Réflexions de 20 s ou plus : 11.Bxe4 35 s, 13.Nd5 24 s, 14.Rxb4 54 s, … Perdu au temps.`
  - Partie « Dès le coup… » seulement si une période de conversion existe (fonction du
    tronçon 02, `chess_coach/conversion.py`) ; pendules = temps restant avant le 1er coup de
    Nico de la période, pour chacun des deux camps.
  - « Erreurs à moins d'une minute : N. » si `summary["errors_low_clock"]` ≥ 1.
  - « Perdu au temps. » si l'issue est `loss` et que l'en-tête `Termination` contient
    `on time` ou `au temps` (les deux formats sont observés), sans tenir compte de la casse.
  - Aucune horloge dans la partie → pas de ligne Temps.

### 2. `execution/routers/chess_router.py`
- Texte affiché : ligne Temps sous la ligne Conversion (sinon sous le déroulé).
- `_build_enriched` : `Temps (données) : …` après `Déroulé (données)` / `Conversion
  (données)`. **Sans horloge**, consigne : « aucune donnée de pendule : ne parle pas de
  gestion du temps ; si la partie est perdue au temps, dis seulement “perdu au temps, pendule
  non fournie” » (le code sait si c'est le cas via `Termination`, il peut l'écrire directement).
- **Coups longs déjà position critique** (même ply) : pas de doublon ; ajouter à leur légende
  une ligne `⏱️ réfléchi 54 s · <faits> : <conclusion>`.
- **Autres coups longs** : positions numérotées à la suite des critiques (Position n+1…).
  - Miniature : `render_position` comme une position critique ordinaire (meilleur coup vert,
    coup joué, `best_line_uci=p.pv_uci[:3]`).
  - Légende écrite par le code :
    `Position 5 — coup 14 (blancs) : joué 🔵 14.Rxb4 en 54 s, meilleur 🟢 14.Rf4, évaluation : 91 % → 86 % (−5 pts)`
    puis `Verdict : plusieurs coups gardaient l'avantage, Maia ≈ 1350 : un coup simple suffisait.`
    (pastilles via les constantes existantes ; le tronçon 04 les recolore).
  - Bloc de données : mêmes lignes qu'une position critique (joué, meilleur + ligne, faits,
    pièces, matériel, attaquées, structure, évaluation, motifs), titre
    `Position k (réflexion longue de 54 s) — coup 14 :`, plus `verdict : …`.
  - Consigne : la consigne principale passe de « chacune des {n} positions » au total
    n + coups longs ; pour une réflexion longue, l'entrée commence par « Pour jouer vite : »
    et donne en 1 à 2 phrases l'idée ou le plan qui permettait de choisir vite, d'après ses
    lignes de données ; elle ne répète pas le verdict.
  - Ces images vont après les critiques, **avant** `_split_entries` (elles reçoivent leur
    entrée LLM), donc avant la miniature Conversion et la courbe.
- Fiche (`summarize`) : clé `long_thinks` (str, ex. `"14.Rxb4 54 s, 22.Re1 43 s, 37.Kd3 35 s"`,
  sinon `None`).

## Tests (cas nominal)
`tests/chess_coach/test_clock.py` : temps par coup sur 4 plies avec base 600 ; les 3 plus
longs ≥ 20 s ; verdicts « un coup simple suffisait » et « réflexion justifiée » ; ligne Temps
avec « Perdu au temps. » sur `dusha28 a gagné au temps`. Router : partie sans horloge →
consigne présente, pas de ligne Temps ; coup long non critique → image et légende avec
« en N s ». `pytest tests/ -q` vert.

## Hors scope
- Temps tracé sur la courbe, seuil relatif à la cadence (refusés par Nico).
- Thème temps dans le profil RPG.
- Couleurs des pastilles : tronçon 04.

## Critère de fin
Tests verts. Ordre des images d'une partie : critiques, coups longs, Conversion, courbe.
