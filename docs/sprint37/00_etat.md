# Sprint 37 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-26), prêt pour `/sprint-auto sprint 37`.
**Branche** : `feat/sprint37-retournement`.
**Cible** : échiquier — chercher comment retourner une position perdante (coups humains
de stratégie, flèche rose ; de tactique, flèche cyan) + mode sombre de la page.

Hors sprint, déjà sur main le 2026-10-26 : liste des coups explosifs en marge + mini
échiquier au survol (`a4ef525`), meilleur coup dans la liste (`23126ae`), flèche bleue
du meilleur coup (`a67cb89`).

## Audit

`audit_retournement.md` : fenêtre 35–85 % du camp au trait (≈ −1,7 / +4,7 pions) ;
`_admissible` fermé en position perdante (avantage clair requis) ; tête de valeur
Maia-2 disponible et inutilisée.

## Décisions arrêtées

Lot 1 (Nico, 2026-10-26) :
- **Tactique (cyan) = piège de retournement** : une réponse humaine probable (Maia, Elo
  adverse, seuil ~20 % à caler) remet le camp perdant au-dessus de 35 % ; le coup n'a pas à
  tenir contre la défense parfaite. Affiché avec la chance que l'adversaire tombe dedans.
- **Stratégie (rose) = pronostic humain Maia** (tête de valeur Maia-2) : coup après lequel
  Maia prédit le meilleur résultat pour le camp perdant, nettement au-dessus du meilleur coup
  Stockfish. Fiabilité à mesurer avant de figer.
- **Portée : échiquier seul.** Telegram = dette pour plus tard ; Nico tient à un code couleur
  par type de coup (orange explosif, vert seul coup, bleu meilleur, cyan, rose).
Lot 2 (Nico, 2026-10-26) :
- **Cyan = piège relatif** : une réponse humaine probable (≥ 20 %, Maia) rapporte au camp
  au trait ≥ meilleur coup + 15 pts (% de gain).
- **Cyan et rose valables dans toutes les positions** (égales et gagnantes aussi), pas
  seulement perdantes. Remplace la décision « recherche quand < 35 % » du lot 1 pour cyan/rose ;
  l'orange garde sa fenêtre 35–85 %.
- **Rose toujours affiché** (idée stratégique principale = pronostic Maia max), sauf s'il
  est le même coup que le meilleur coup ou le seul coup : alors seule la flèche bleue/verte.
- **Liste en marge** : cyan et rose sauvegardés comme l'orange (bloc, suite, mini échiquier),
  **une colonne par couleur**, page sur toute la largeur de l'écran.

Lot 3 (Nico, 2026-10-26) :
- **Une flèche par coup**, priorité seul coup (vert) > explosif (orange) > piège (cyan) >
  meilleur (bleu) > stratégie (rose). Le bloc de la liste dit quand le coup est aussi le
  meilleur coup.
- **Garde-fou du rose** : choisi parmi les coups à ≤ 15 pts (≈ 1,7 pion) du meilleur coup
  Stockfish (même tolérance que l'explosif).
- **Mode sombre permanent** (fond et échiquier sombres), sans bouton ni suivi du système.

Lot 4 (Nico, 2026-10-26, en cours de sprint, avant le tronçon 02) :
- **Flèche bleue rationnée, en dernier recours** : dessinée seulement si aucune autre flèche
  cochée (vert, orange, cyan, rose) n'est dessinée ; même coup qu'une autre flèche → l'autre
  couleur, bleu non décompté. Et seulement à partir du coup n°10, au plus 3 par camp, jamais
  si le même camp l'a eue à son coup précédent. Remplace « rose masqué s'il est le meilleur
  coup » (lots 2-3). Détail : `02_page_couleurs_sombre.md` point 4.

Mesure demandée par Nico (crainte orange = rose souvent) : orange = rose dans 1/12
positions à orange [1 exécution, n=12] ; rose = meilleur coup (masqué) 15/30
[1 exécution, n=30] (`audit_retournement.md` §5.b). Les deux calques restent distincts.

Recos de conception (Claude, à veto de Nico) :
- Cyan : même tolérance de 15 pts sur la perte Stockfish du coup lui-même (pas de pari
  perdant contre la bonne défense) ; au plus 6 candidats approfondis par passe (latence).
- Cyan/rose calculés dans toutes les positions non terminales, y compris « décidées ».

- Recos posées sans objection (lot 1) (veto possible) : recherche quand le camp au trait est < 35 %
  (≈ −1,7 pion), sans borne basse ; rien au-dessus de 85 % ; mode sombre automatique
  (thème du système), sans bouton.

## Questions ouvertes

Mesure faite (`audit_retournement.md` §5) : rose ≠ meilleur coup avec écart ≥ 3 pts dans
4/16 positions [2 exécutions, n=16] ; piège absolu 1/16, piège relatif +15 pts 3/16
[1 exécution, n=16].

(aucune ; découpage en attente d'OK)

## Tronçons

- 01 piège (cyan) et stratégie (rose) dans l'analyse live (`01_analyse_piege_strategie.md`) ✅
  — `live._human_moves`, `difficulty.position_values`, clés `trap`/`strategy` de l'état.
  Passe réelle ×1 : 18,1 s et 12,7 s [2 positions, pytest en parallèle, orange compris].
- 02 page : couleurs cyan/rose, colonnes, mode sombre (`02_page_couleurs_sombre.md`) ✅
  — `interfaces/board/index.html` : flèches vert > orange > cyan > rose puis bleu en dernier
  recours rationné (`blueAllowed`, `blueDrawn`), trois colonnes `saved-*`, `color-scheme: dark`,
  cases `#7d8796`, brosses verte/bleue éclaircies. Rendu à valider au run live.
- 03 run live (`03_run_live.md`) ⏳

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳ (03, run live par Nico). Exécution :
`/sprint-auto sprint 37`.
