# Sprint 27 — audit du run live 07 (correctif)

Date : 2026-10-19. Code audité : HEAD `9f5f8fa` (tronçons 04-06 commités).
Run live : 2026-10-19 14:43-14:48, 4 parties (kickoff `07_run_live_correctif.md`).

## 1. Résultat du run live

| Partie | journalctl `critical=` | Attendu | Verdict |
|---|---|---|---|
| 1 Morra (blancs) | `['d:8.e5']`, 23,6 s | occasion explosive 8.Nd5 | ✅ moteur |
| 2 Dame précoce indentée (noirs) | `nico=black source=header`, `['d:2...Nc6']`, 7,0 s | 2...Nf6!?, couleur lue | ✅ moteur |
| 3 Letton (noirs) | `['d:2...f5', 'c:12...Qxh5']`, 34,2 s | 12...Qxh5, pas d'erreur sur 2...f5 | ✅ moteur, réserve §3 |
| 4 Von Hennig (blancs) | `['a:4.Bc4']`, 24,6 s | 12.Nxe6 présent, pas d'erreur sur 4.Bc4 | ❌ §2 |

Premier message (14:43:16) : `chess_router PGN unreadable` — contenu non connu, à confirmer
par Nico (faux départ probable).

Texte LLM (toutes parties, réponses DeepSeek après Groq 413) : §4.

## 2. Partie 4 — le repli « pire coup » réintroduit une erreur d'ouverture

`chess_coach/analysis.py:240-286`, `select_critical` :

```python
    errors.sort(key=lambda c: c.score, reverse=True)
    uniques.sort(key=lambda c: c.score, reverse=True)
    selected = (errors + uniques)[:3]
    if explosive:
        best_d = max(explosive, key=lambda c: c.score)
        if all(c.ply.ply != best_d.ply.ply for c in selected):
            selected.append(best_d)
    if not selected:
        nico_plies = [p for p in plies if p.color == nico_color]
        if nico_plies:
            worst = max(nico_plies, key=lambda p: p.loss)
            selected = [CriticalPosition(kind="a", ply=worst, score=worst.loss)]
    return sorted(selected, key=lambda c: c.ply.ply)
```

Rejeu local de la partie 4 (blancs, `analyze_game`, 2 runs [n=2]) :

| Coup | perte | qualité | écart au 2e |
|---|---|---|---|
| 4.Bc4 | 6,3 / 7,2 | correct | 1,0 / 2,5 |
| 6.Nxf3 | 3,2 / 0,0 | best | 14,6 / 12,2 (reprise → exclu) |
| 8.Bxe6 | 1,6 / 0,0 | best | 19,1 / 20,0 |
| 12.Nxe6 | 0,0 / 0,0 | best | 18,9 / 18,1 |

Chaîne causale :
1. 12.Nxe6 : écart 18-19 [n=2] < seuil 20 du coup unique (`analysis.py:263`). Au rejeu de
   conception il sortait à 23-24 [n=2] : le coup est au bord du seuil, le bruit moteur
   (Threads=8 + limites en temps, dette acceptée) le fait passer d'un côté ou de l'autre.
2. Aucune erreur (aucune perte ≥ 20 avant le coup 10, ≥ 10 après), aucun coup unique,
   aucune occasion explosive (`found=0`) → `selected` vide.
3. Repli : pire coup de Nico = 4.Bc4 (perte 6-7), étiqueté `kind="a"` (« erreur de Nico »).
   Le repli ignore le seuil d'ouverture du tronçon 04 et étiquette « erreur » un coup qui,
   par construction (selected vide), est sous le seuil d'erreur.

Le repli date du sprint 26 (« toujours au moins une position »). Le router accepte
`analysis.critical` vide : boucle des diagrammes vide, `images=[]`, l'interface Telegram
(`interfaces/telegram_interface.py:186-191`) itère sur la liste sans condition.

## 3. Parties 2-3 — occasion explosive = meilleur coup du moteur

Légende partie 3 : « joué 2...f5, explosif 2...Nf6!? (meilleur 2...Nf6) ».

`chess_coach/explosive.py`, `_search_position` :

```python
    reference = engine.analyse(board, chess.engine.Limit(time=_ROOT_TIME), multipv=_MULTIPV)
    win_best = _win_of(reference[0])
    best = reference[0]["pv"][0]
    ...
    candidates = [
        (move, max(0.0, win_best - win)) for move, win in wins.items()
        if move != best and move.uci() != played_uci and win_best - win <= _TRAP_WINDOW
    ]
```

Le candidat est exclu s'il est le meilleur coup **de la seconde analyse** (0,5 s), alors que la
légende et le bloc affichent `p.best_san` **de la première passe** (`analyze_game`). Les deux
analyses divergent sur des coups proches (2...Nf6 / 2...Nc6 au coup 2) : le meilleur coup de
la première passe peut ressortir comme « explosif ». `find_explosive` n'a que `p.uci` (joué)
à transmettre, pas `p.best_uci`.

Corollaire : 2...Nf6 (partie 2 : coût 1 pt, partie 3 : coût 1 pt) passe `_admissible` par le
pion e5 laissé en prise (`sacrifice ≥ 1` via `offered`/ligne). Un coup de développement qui
laisse un pion défendable n'a rien d'« explosif » pour Nico ; correction proposée : exclure
aussi `p.best_uci` (le reste du filtre est inchangé, pas de nouveau seuil).

## 4. Texte LLM

### 4.1 Notation française résiduelle

Partie 2 : « 2.Dh5 », « Dxe5+ », « Fe7 » ; partie 3 : « Cxe5 ». Partie 1 propre.

Bloc et consigne (`chess_router.py:_build_enriched`) : tout est en anglais, consigne
« Notation anglaise : N, B, R, Q, K ». Source probable du français : l'historique de
conversation chargé avec le message (`conversation_history loaded … messages=20`), qui
contient les analyses du sprint 26 en notation française. La consigne ne suffit pas contre
cet exemple.

Correction déterministe possible côté router, sur `result["text"]` : remplacer les lettres
de pièce françaises **non ambiguës** devant une case (`C`→N, `F`→B, `T`→R, `D`→Q, regex
`\b([CFTD])(x?[a-h][1-8])` et variantes `Cbd7`, `Tae1`). `R` (roi en français, tour en
anglais) reste tel quel : ambigu. Limite : l'échange écrit en conversation garde le texte
brut du LLM (l'écriture a lieu dans `LLMExecutionRouter`, avant le retour au chess_router).

### 4.2 Suite du piège absente

Partie 1 : « Si les Noirs jouent exd5, ils perdent 14 pts », sans les coups. Le bloc contient
bien la ligne (`_explosive_lines` : « si l'adversaire prend exd5 : 8...exd5 9.… (il perd 14
pts) », émise dès que `trap_reply_san` et `round(trap)`) et une ligne par réponse. La consigne
d (`chess_router.py`, « explique l'idée du coup explosif … son coût … dans quel contexte ») ne
demande ni la suite du piège ni les réponses : le LLM résume. Correction : l'exiger dans la
consigne d.

### 4.3 Faits inventés malgré la liste des pièces

| Partie | Phrase | Réalité |
|---|---|---|
| 1 | « Ton fou en c4 attaque le pion f7 » | e6 bloque la diagonale c4-f7 |
| 1 | 8.e5 « ouvre la colonne e pour ta tour » | e5 avance, la colonne reste fermée |
| 2 | « 2...Nc6 attaque le pion e5 » | il le défend (pion noir) |
| 2 | « prépare le développement de ton fou en g7 » | sans rapport |
| 3 | « tu as un avantage matériel (tu as gagné un pion) » | noirs à −1 (3.exf5, 5...exd3 6.Bxd3) |
| 4 | 4.Bc4 « ouvre la colonne f pour ta tour » | sans rapport |

La ligne `pièces :` (tronçon 06) place les pièces mais ne dit ni qui attaque quoi, ni le
bilan matériel : le LLM les déduit, et se trompe. Deux types d'erreurs :
- **relations** (attaque / défense / colonne ouverte) : non calculables par le LLM ;
- **bilan matériel** : calculable trivialement (`_material` existe dans `explosive.py`).

Pistes, de la moins à la plus structurelle :
1. Ajouter au bloc, par position, le **bilan matériel** (« matériel : Nico −1 ») et les
   **pièces en prise / attaquées** (calcul `python-chess` : attaquants/défenseurs), plus une
   consigne « ne décris aucune attaque, défense ou colonne absente de ces lignes ».
   Réduit, n'élimine pas.
2. Ne laisser au LLM que les idées générales, et produire la partie factuelle (« ce qui se
   passe ») de façon déterministe dans le router. Refonte de la forme de la réponse.

## 5. Hors périmètre constaté

- Groq 413 sur chaque analyse (dette déjà notée) ; le bloc rallongé par le tronçon 06 ne change
  rien au constat (déjà 413 avant).
- HNSW quarantine au démarrage (`.drift-*`) : comportement connu du palace, cf.
  `docs/architecture/chromadb_palace.md`.

## 6. Partie exemple Écossaise / gambit Göring (ajoutée par Nico après le run)

Rejeu local, code HEAD `9f5f8fa`, 1 run [n=1] : `critical = [d:2.Nf3 (explosif 2.f4, offert 1)]`, rien d'autre.

Coups de la partie qui comptent (1re passe) : 7...h6 perte 18,3 ; 8...Nxe5 perte 13,6 ; Nico 8.e5 / 9.Nxe5 / 10.Nxf7 = meilleurs coups, écart au 2e < 6 ; dès le coup 10 `win_before` > 90 (décidé). Aucune sorte ne montre « erreur adverse punie » : la sorte b exige une erreur de Nico après une erreur adverse ≥ 20.

```
[White "staroflexeur"]
[Black "ghzwansl"]
[ECO "C45"]
[WhiteElo "1345"]
[BlackElo "1263"]

1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. c3 dxc3 5. Bc4 cxb2 6. Bxb2 Nf6 7. O-O h6 8.
e5 Nxe5 9. Nxe5 d6 10. Nxf7 Qd7 11. Nxh8 Qc6 12. Bf7+ Kd7 13. Ng6 b6 14. Ne5+
Kd8 15. Nxc6+ Kd7 16. Ne5+ Ke7 17. Bd5 dxe5 18. Bxa8 Kf7 19. Bxe5 Nd7 20. Bd5+
Kg6 21. Qg4+ Kh7 22. Be4+ Kh8 23. Bxc7 (23. Qg6 Nf6 24. Bxf6 gxf6 25. Bf5 (25.
Qh7#)) 23... b5 24. Qf3 a5 25. Bxa5 Nf6 26. Nc3 Bg4 27. Qf4 Be6 28. Rad1 Bc4 29.
Rfe1 Bc5 30. Rd8+ Bg8 31. Qb8 Be7 32. Rxg8+ Nxg8 33. Bd5 Kh7 34. Qxg8+ Kg6 35.
Rxe7 b4 36. Qxg7+ Kf5 37. Be4+ Kf4 38. Bc7# 1-0
```
