# Sprint 27 — Tronçon 03 : run live (Nico)

Pré-requis : tronçons 01-02 commités, `sudo systemctl restart aria.service`.
Terminal de suivi : `sudo journalctl -u aria -f -o cat`

## Message M1 — Smith-Morra, Nico blancs (8.e5 joué, 8.Cd5!? attendu)

```
[White "staroflexeur"]
[Black "Test"]
[Date "2026.10.19"]
1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 Nf6 6. Bc4 e6 7. O-O a6 8. e5 *
```

Attendu :
- journalctl : `chess_explosive positions=…/… found=≥1 …`, puis
  `chess_analysis OK … critical=[… d:8.e5 …] duration=` ≤ 40 s.
- Telegram : un diagramme « Position k — coup 8 (blancs) : joué 8.e5, explosif 8.Cd5!?
  (meilleur …) » avec flèche orange d5 ; la réponse explique le sacrifice et le piège
  8…exd5, sans présenter Cd5 comme le meilleur coup.

## Message M2 — Dame précoce, Nico noirs (2…Cc6 joué, 2…Cf6!? attendu)

```
[White "Test"]
[Black "staroflexeur"]
[Date "2026.10.19"]
1. e4 e5 2. Qh5 Nc6 *
```

Attendu : critique `d:2...Nc6`, légende « explosif 2...Cf6!? », flèche orange g8-f6,
explication du gambit (3.Dxe5+ Fe7, avance de développement).

## Message M3 — une vraie partie Chess.com (facultatif, non-régression)

Coller une partie complète exportée. Attendu : `duration` ≤ 40 s ; positions a/b/c
toujours présentes ; une d seulement si une occasion existe.

## Critère de succès

M1 et M2 : sorte d affichée avec le bon coup explosif, flèche orange, explication
honnête ; durée ≤ 40 s. Tout écart : noter message, horodatage et extrait journalctl.
