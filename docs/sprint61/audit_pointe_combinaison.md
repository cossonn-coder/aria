# Sprint 61 — audit : explication tactique, pointe de combinaison

Date : 2026-11-19. Code lu sur `main` @ `52c0aab`.

## 1. Cas déclencheur

Partie BaguetteChaussette – miguel_tomazii (2026-11-19, 0-1), position 1 :
`r1b1k2r/1pq1bppp/p4n2/3p4/1n1P4/3B1N2/2P1QPPP/RNB1R1K1 w kq - 0 12` (après 11...Nxb4).

Vérifié Stockfish (profondeur 22) :
- 12.Qxe7+ Qxe7 13.Rxe7+ Kxe7 14.Ba3 Be6 15.Bxb4+ Kd7 … : +3,28 ;
- 12.Bb5+ (2e choix) : +1,05 ;
- après 14...a5 : +4,27, 15.Bxb4+ Kd7 16.Ne5+ (si 15...axb4, 16.Rxa8).

Maia (Elo 1711) après 14.Ba3 : 14...a5 à 93 % [n=1 position], Stockfish +3,94
(15.Bxb4+ Kd7 16.Ba3).

La combinaison, lue par Nico (juste) :
1. 12.Qxe7+ prend Be7, **le seul défenseur de Nb4** (diagonale e7-b4) ;
2. les reprises forcées **amènent le roi en e7**, sur la même diagonale ;
3. **pointe** : 14.Ba3 cloue Nb4 sur Ke7, le cavalier ne peut plus fuir ;
4. la défense naturelle 14...a5 échoue : 15.Bxb4+ axb4 16.Rxa8 (colonne a ouverte depuis
   11.axb4, Ra8 non défendue) ;
5. bilan : B + N contre R, avantage décisif.

Réponses d'ARIA :
- Pourquoi : « Be7 était cloué et prenable : Qxe7+ gagnait une pièce entière » (faux :
  Be7 est défendu par Qc7 et Ke8, le gain est en Nb4, trois coups plus tard).
- Question de suivi : « pièce clouée + échec disponible = prise gratuite » (schéma faux).

## 2. Données réellement reçues par le LLM (position 1)

Reproduit hors ligne (`analyze` + `ChessExecutionRouter._build_enriched`, sans LLM) :

```
  meilleur 12.Qxe7+, ligne : 12.Qxe7+ Qxe7 13.Rxe7+ Kxe7 14.Ba3 Be6
  faits : 12.Qxe7+ (prend Be7, échec, attaque Nb4, Qc7) 12...Qxe7 (reprend) 13.Rxe7+ (reprend, échec) 13...Kxe7 (reprend) 14.Ba3 (attaque Nb4) 14...Be6
  attaquées : blancs Bd3 (par Nb4) ; noirs Be7 (par Qe2)
  motifs : fourchette
  suite du meilleur coup, faits : 12.Qxe7+ (prend Be7, échec, attaque Nb4, Qc7) … 14.Ba3 (attaque Nb4) 14...Be6 15.Bxb4+ (prend Nb4, échec) 15...Kd7
  → matériel : Nico B, N contre R, 5 pions contre 6, 78 % de gain
  idée du coup joué, faits : 11...Nxb4 (prend pion b4) ; ton coup : développe Ba3, libère Re1 ; Maia : … 44 % … ; suite probable : 12...Be6 (décloue Be7) 13.c3 (attaque Nb4)
```

Constats :

- **C1 — aucun fait « cloue »**. `_move_fact_items` (`execution/routers/chess_router.py:265`)
  calcule « décloue » mais jamais le clouage créé. 14.Ba3 n'a que « attaque Nb4 » : le
  mécanisme de la pointe est absent des données.
- **C2 — aucun fait « élimine le défenseur » ni « attire »**. 12.Qxe7+ « prend Be7 » sans
  dire que Be7 défendait Nb4 ; 13...Kxe7 « reprend » sans dire que le roi arrive sur la
  diagonale du futur clouage.
- **C3 — le gain final n'est pas désigné**. La ligne contient 15.Bxb4+ (prend Nb4) et la fin
  matérielle, mais rien ne dit que c'est là que se fait le gain, ni quel coup le rend
  inévitable. Les seuls faits saillants (« prend Be7, échec ») sont au premier coup : le LLM
  y a placé le gain.
- **C4 — aucune défense adverse examinée**. `forcing_line` (`chess_coach/analysis.py:624`)
  suit la seule PV. La défense humaine naturelle (...a5, 93 % selon Maia) et sa réfutation
  (axb4 Rxa8) ne sont calculées nulle part pour les sortes a / b. Précédent : `explosive.py`
  calcule des réponses humaines Maia avec lignes (`_human_replies`, l. 251) et une reprise
  naturelle (`_natural_capture`, l. 199) — sorte d uniquement.
- **C5 — motif trompeur**. `assign_motifs` tague « fourchette » (Qxe7+ échec + attaque
  Nb4, Qc7) ; aucun tag clouage / élimination du défenseur. Le LLM n'en a pas tiré la pointe.
- **C6 — consigne**. La consigne « Pourquoi » (`chess_router.py:1330-1343`) demande
  (1) idée de Nico, (2) ce qu'elle a négligé, (3) « ce que fait le meilleur coup ». Rien ne
  demande où la ligne gagne ni pourquoi la défense échoue.

## 3. Question de suivi (« cette tactique… je veux trouver ce schéma »)

Chemin : message texte libre → classifieur → REASONING → `LLMExecutionRouter`, sans moteur.
Historique : tours coupés à 1 500 caractères (`HISTORY_MESSAGE_MAX_CHARS`,
`execution/routers/llm_router.py:54`), budget 6 000. Le tour `user` de l'analyse est le
message enrichi : ses 1 500 premiers caractères couvrent en-têtes, compteurs, déroulé, pas
les faits de la position 1. Le tour `assistant` est le texte LLM (avec le Pourquoi faux).
→ Le suivi n'a eu que le Pourquoi faux comme base, et a généralisé l'erreur.

Conséquence : corriger les faits et le Pourquoi (C1-C6) corrige aussi la base du suivi pour
les premières positions. Un suivi qui relance le moteur est un autre chantier.

## 4. Règles d'architecture

Tout se passe dans `chess_coach/` (calcul) et `chess_router.py` (faits + consigne) :
aucune lecture / écriture mémoire nouvelle, router inchangé dans son contrat. Pas de palace
prod touché. Coût : Maia (une passe batchée) + Stockfish par position d'erreur, comme la
sorte d.
