# Sprint 27 — Tronçon 07 : run live du correctif (Nico)

Pré-requis : tronçons 04-06 commités, `sudo systemctl restart aria.service`.
Terminal de suivi : `sudo journalctl -u aria -f -o cat`

Envoyer chaque message seul sur Telegram, attendre la réponse avant le suivant.

## Partie 1 — Smith-Morra (Nico blancs) : 8.Nd5!? attendu

```
[White "staroflexeur"]
[Black "Test"]
1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 Nf6 6. Bc4 e6 7. O-O a6 8. e5 *
```

Attendu : une seule occasion explosive montrée, au coup 8 : légende
« … joué 8.e5, explosif 8.Nd5!? … » (texte français, coups en notation anglaise), flèche orange d5. Le texte dit
que le **cavalier** est offert, donne la suite si 8...exd5, et ne présente pas Nd5 comme
le meilleur coup.

## Partie 2 — Dame précoce, en-têtes indentés exprès (Nico noirs) : 2...Nf6!? attendu

```
[White "Test"]
  [Black "staroflexeur"]
  1. e4 e5 2. Qh5 Nc6 *
```

Attendu : journalctl `nico=black source=header` ; occasion explosive au coup 2,
« explosif 2...Nf6!? », flèche orange g8-f6 ; aucune phrase « j'ai supposé que tu joues
les blancs ».

## Partie 3 — gambit letton (Nico noirs) : le milieu de partie revient

Recoller la partie Chess.com MitenPandya – staroflexeur du 2026-10-19 (export complet).

Attendu : journalctl `critical=` contient **`c:12...Qxh5`** ; **pas** de `a:2...f5` ;
au plus une occasion explosive (`d:`). Le texte relie la partie aux idées du letton
(tempo, initiative) et ne traite pas 2...f5 comme une faute. `duration` ≤ 40 s.

## Partie 4 — Von Hennig contre la Caro-Kann (Nico blancs)

Recoller la partie staroflexeur – CANNIBALISM_22 du 2026-10-19 (export complet).

Attendu : `c:12.Nxe6` présent ; pas d'erreur sur 4.Bc4 / 5.f3 ; si une occasion explosive
sort, son sacrifice affiché est plausible (pas de « sacrifice 4 » sur 10.Qe1).

## Critère de succès

- Parties 1-2 : la bonne occasion explosive, flèche orange, matériel offert juste, suites
  présentes, couleur correcte.
- Parties 3-4 : coup unique du milieu de partie présent, ouverture non sanctionnée.
- Tout en notation anglaise ; aucun emplacement de pièce inventé dans le texte.
- `duration` ≤ 40 s partout.

Tout écart : noter partie, horodatage, extrait journalctl et phrase fautive du texte.
