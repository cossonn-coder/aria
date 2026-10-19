# Sprint 27 — Tronçon 05 : moteur explosif — sacrifice réel + suites

À lire d'abord : `CLAUDE.md`, `docs/sprint27/00_etat.md` (§ Correctif),
`docs/sprint27/audit_correctif.md` (constats « sacrifice mesuré à une coupure arbitraire »
et « non-déterminisme »), puis `chess_coach/explosive.py` en entier.

## Objectif

1. **Sacrifice réel** (bug) : `_deepen` mesure le matériel au 6e demi-coup de la ligne,
   même en plein échange. Faux positifs mesurés : 1...d6 → « sacrifice 9 »
   (ligne `d6 d4 e5 dxe5 dxe5 Qxd8+`, coupée avant `Kxd8`) ; 10.Qe1 → « sacrifice 4 »
   (coupée sur `…Nxe5`, avant `dxe5`). Faux négatif : 8.Nd5 → « 1 pion » (le cavalier
   offert n'apparaît pas, l'adversaire refuse dans la PV). Le LLM recopie ces chiffres.
2. **Suites** (demande Nico) : une occasion explosive doit montrer (i) la suite gagnante
   si l'adversaire tombe dans le piège, (ii) les suites après les réponses raisonnables
   de l'adversaire, prises comprises (exemple de Nico : le fou attaqué peut prendre le
   cavalier — réponse à envisager).
3. Règle d'admission inchangée (décision Nico) : sacrifice réel ≥ 1 **ou** piège ≥ 10,
   dans la fenêtre (perte ≤ 5, ou ≤ 15 si piège ≥ 10). Avec le sacrifice corrigé et une
   seule occasion explosive montrée (tronçon 04, la meilleure au score), le bruit type
   6.b4 est relégué derrière 8.Nd5.

## Comportement attendu (intention)

- **Ligne stabilisée** : partir de la ligne actuelle (candidat + PV de la meilleure réponse).
  Point de mesure = le premier demi-coup à partir du 6e après lequel le coup suivant de la
  PV n'est **pas** une prise (on laisse finir l'échange), borne dure ~10 demi-coups ; si la
  PV s'épuise avant, sa fin. `sacrifice_line` = matériel perdu par Nico à ce point
  (`max(0, …)`, comme aujourd'hui). La ligne affichée (`pv_san`) va jusqu'à ce point.
- **Matériel offert** : après le candidat, si la pièce posée est en prise (attaquée par une
  pièce adverse de moindre valeur, ou attaquée et non défendue), `offered` = valeur de la
  pièce posée − valeur de la pièce éventuellement prise par le candidat (≥ 0) ; sinon 0.
  8.Nd5 (attaqué par e6) → 3.
- `sacrifice = max(sacrifice_line, offered)`. Exposer aussi `offered` séparément sur
  `ExplosiveMove` (le router dira « offre le cavalier » vs « sacrifie un pion sur la ligne »).
- **Suite du piège** : quand la prise naturelle existe, l'analyse `root_moves=[capture]`
  est déjà faite ; garder sa PV → nouveau champ (ex. `trap_line_san`, SAN depuis la position
  après le candidat, prise comprise, ~6-8 demi-coups).
- **Réponses raisonnables** : les 3 réponses MultiPV déjà calculées dans `_deepen`
  (`replies`). Nouveau champ (ex. `replies`) : pour chacune, SAN de la réponse, sa ligne
  (SAN, ~6 demi-coups) et le % de gain **côté Nico** après elle. Les prises adverses y sont
  naturellement si elles sont raisonnables. Aucune analyse moteur supplémentaire.
- Budget 30 s et constantes de temps inchangés. Non-déterminisme (Threads=8) accepté :
  ajouter un commentaire d'une ligne près de `ENGINE_OPTIONS` ou du budget qui le dit.

## Fichiers

- `chess_coach/explosive.py` (seul fichier de prod). `ExplosiveMove` gagne `offered`,
  `trap_line_san`, `replies` (noms indicatifs).
- `tests/chess_coach/test_chess_coach.py`.

## Tests (cas nominal)

- Morra (`MORRA_PGN` existant) : la d du coup 8 est `Nd5`, `offered == 3`, `sacrifice >= 3`,
  `trap_line_san` commence par `exd5`. (Le test actuel `trap >= 10` est au bord du seuil
  [n=3 : 10,5 / 11,5 / 12,7] : le garder, mais si instable, assouplir en `trap >= 8`.)
- Dame précoce (`QH5_PGN`) : d du coup 2 = `Nf6`, `sacrifice >= 1` (inchangé).
- Test sans Stockfish de la mesure de sacrifice : fonction pure (à extraire si besoin,
  ex. `_line_sacrifice(board, line)`) sur la ligne `d6 d4 e5 dxe5 dxe5 Qxd8+ Kxd8` depuis
  la position après 1.e4 (Nico noirs) → 0, jamais 9.

## Hors scope

- Sélection des positions, PGN : tronçon 04. Router / texte LLM / notation : tronçon 06.
- Maia, réglage des poids du score, options Stockfish.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` mis à jour (tronçon 05 ✅ + §REPRISE).
