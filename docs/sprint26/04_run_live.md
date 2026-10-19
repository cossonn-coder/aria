# Sprint 26 — Tronçon 04 : run live (Nico)

Pré-requis : tronçons 01-03 commités sur `feat/sprint26-coach-echecs`,
`./venv/bin/pip install -r requirements.txt` fait (lib `chess`), puis
`sudo systemctl restart aria.service`.

Terminal de suivi : `sudo journalctl -u aria -f -o cat`

## Message A — partie gagnée, pseudo en en-tête (noirs)

```
[Site "Chess.com"]
[Date "2026-10-19"]
[White "King_walks_19"]
[Black "staroflexeur"]
[Result "*"]
[WhiteElo "1272"]
[BlackElo "1307"]
[TimeControl "600"]
1. d4 f5 2. Bf4 Nf6 3. Nc3 g6 4. Nf3 Bg7 5. e3 O-O 6. Bc4+ d5 7. Bd3 Nbd7 8. O-O
c5 9. dxc5 Nxc5 10. Be5 Ncd7 11. Bg3 Nh5 12. Ng5 Nxg3 13. hxg3 Nf6 14. f4 Qe8
15. Kf2 h6 16. Nf3 Be6 17. Rh1 Ng4+ 18. Ke2 a6 19. Ne5 Nxe5 20. fxe5 Kh7 21. Kd2
Bxe5 22. Qf3 Qc6 23. g4 fxg4 *
```

Attendu :
- journalctl : `chess_analysis OK … nico=black source=header critical=K` (1 ≤ K ≤ 3),
  `chess_game_write OK hash=…`, `chess_router OK critical=K images=K`,
  `memory_write OK wing=aria_episodic` (intent résolu/créé, pas de `intent SKIPPED`).
- Telegram : K diagrammes **vus côté noirs** (rangée 8 en bas), une flèche verte,
  légendes « Position i — coup n … » en notation française ; puis un texte qui
  parle de Nico comme les noirs, suit Position 1, 2, 3, notation C/F/T/D/R,
  et dont les coups cités correspondent aux légendes.

## Message B — partie perdue (noirs)

```
[Site "Chess.com"]
[Date "2026-10-19"]
[White "nojokeloco6789"]
[Black "staroflexeur"]
[Result "*"]
[WhiteElo "1364"]
[BlackElo "1296"]
[TimeControl "600"]
1. d4 f5 2. e3 Nf6 3. Nf3 e6 4. Bc4 d5 5. Bb3 c5 6. dxc5 Bxc5 7. Nc3 O-O 8. O-O
Nc6 9. Qe2 a6 10. a3 b5 11. Ba2 Qe8 12. b4 Bb6 13. Bb2 Bb7 14. Bb3 Qh5 15. Rad1
Ne4 16. Na2 Rad8 17. Qd3 a5 18. Qxb5 Rd6 19. Qxb6 Nd8 *
```

Attendu : idem A ; au moins une position de sorte (a) parmi 15…-19… ; le texte ne
prétend plus que « 18...Rd6 sacrifie la dame » (coups cités = coups des légendes).

## Message C — relance texte sur l'analyse

`pourquoi la position 1 de cette partie était critique ?`

Attendu : réponse cohérente avec la Position 1 du message B (l'analyse moteur est
dans l'historique) ; pas de nouveau calcul moteur (attendu : pas de log `chess_analysis`).

## Message D — renvoi de la même partie (dédoublonnage)

Renvoyer exactement le message B.

Attendu : `chess_game_write OK hash=…` avec **le même hash** que pour B.

## Message E — pas de pseudo, couleur précisée

```
je joue les noirs
[White "Ami"]
[Black "Moi"]
1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
```

Attendu : `source=message nico=black` ; Position sur 3...Cf6 (gaffe), échiquier côté
noirs, flèche vers le bon coup (ex. 3...g6 ou 3...De7).

## Critère de succès

A, B, D, E conformes ; C cohérent. Durée d'analyse A/B < 30 s (lire `duration=` dans
`chess_analysis OK`). Tout écart : noter message, horodatage et extrait journalctl.
