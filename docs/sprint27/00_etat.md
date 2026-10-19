# Sprint 27 — état de conception

**Phase** : B correctif 2 figée (2026-10-19) — prêt pour `/sprint-auto sprint 27` (tronçons 08-09, puis run live 10)
**Cible** : #87 coups conseillés « explosifs »
**Branche** : `feat/sprint27-coups-explosifs`
**Audit** : `docs/sprint27/audit_coups_explosifs.md`
**Palace prod touché** : NON (seule nouveauté : valeur `kind="d"` dans `plies_json`, structure inchangée) → calibrage faible

## Décisions arrêtées

- 2026-10-19 — Nico : cible = #87 (kickoff sprint 27).
- Q1 — Nouvelle sorte de position critique « d — occasion explosive » (Nico a joué un coup
  calme alors qu'un coup explosif tenait la fenêtre), dans le budget ≤ 3 après a/b ;
  2e flèche (orange) sur le diagramme.
- Q2 — Score v1 = les 4 composantes : sacrifice/déséquilibre, forçant, piège, volatilité.
- Q3 (réponse Nico = exemple) : Smith-Morra 1.e4 c5 2.d4 cxd4 3.c3 dxc3 4.Cxc3 Cc6 5.Cf3 Cf6
  6.Fc4 e6 7.O-O a6 8.Cd5!? doit être détecté. Mesures (audit §2 bis) : 8.Cd5 perd
  ≈ 12 pts (54,7 → 42,7, d22) et n'est PAS dans le MultiPV 6 → fenêtre fixe ≤ 5 et
  candidats MultiPV insuffisants.

- Q4 — #81 et rangement wing/room hors sprint (pas d'objection de Nico).
- Q5 — Fenêtre à deux niveaux : perte ≤ 5 pts de % de gain ; ≤ 15 si piège
  (la réponse naturelle fait perdre ≥ 10 pts à l'adversaire).
- Q6 — Réponse naturelle v1 = prise du matériel offert (sur la case d'arrivée) ;
  échec sans sacrifice → meilleure réponse. Maia en v2.
- Q7 — Budget ≤ 30 s d'analyse explosive ; Stockfish 8 threads ; recherche limitée aux
  positions de Nico non décidées (35-75 %) des 20 premiers coups ; arrêt au budget, log
  de couverture.
- Ordre de sélection : a/b, puis d, puis c (choix Claude, dans l'esprit de Q1).
- Synthèse validée par Nico (« ok », 2026-10-19) : candidats = MultiPV 5 ∪ coups par forme
  (échec, prise, pièce sur case attaquée), évalués à ≈ 0,5 s ; sacrifice mesuré sur la
  ligne (capte 2…Cf6) ; score = sacrifice + forçant + piège/5 + volatilité/10 ;
  Stockfish Threads=8 Hash=256 pour toute l'analyse ; branche créée.

### Correctif (post-run live 03)

- A1 — Nico : d en **bonus** — a/b/c gardent le budget ≤ 3 (comportement sprint 26),
  la meilleure d s'ajoute en 4e, n'évince jamais rien (12...Dxh5 en M3 revient).
- A2 — Nico : ouverture assumée — avant le coup 10, a/b seulement si perte ≥ 20 (au lieu de 10).
  (Portée sur d : voir question A2-bis.)
- A3 — Nico : **garder** d même quand le coup joué est le meilleur (cas 8.e5 de M1).
- A4 — Nico : corriger C6 (sacrifice sur ligne stabilisée + matériel offert même refusé)
  + exiger sacrifice réel ≥ 1 ou piège ≥ 10 ; non-déterminisme C5 accepté et documenté.
- A5 — retours Nico (exemple 9...Dg6!? d'une autre partie) :
  - d doit montrer la **suite gagnante** si l'adversaire tombe dans le piège, et la suite
    après les **prises raisonnables** (ex. Fxc6 en réponse) ;
  - faits fiables : le LLM invente (« d6 attaque le Fg5 », « sacrifie 3 pions ») ;
  - **notation anglaise partout** (N, B, R, Q, K) — revient sur le choix français du sprint 26 ;
  - lier les **idées classiques de l'ouverture** à la position montrée ;
  - axes de travail « façon RPG » (acquis après 3 validations, maîtrisé si jamais raté,
    priorité qui remonte en cas d'échec) et appréciation du niveau/style (mal joué, passif,
    solide, brillant) sur l'historique → proposition : hors correctif (cf. question scope).
- Scope — Nico (« ok pour le découpage ») : correctif = C1, A1-A4, A5 (faits + suites +
  notation anglaise + idées d'ouverture) ; **sprint 28 = modèle joueur** (axes RPG +
  appréciation de style, fusion #81).
- Rejeu Von Hennig (Nico blancs, 12 coups, [n=2]) : aucune d en ouverture ; 4.Fc4 / 5.f3
  (gambit) pertes 6-8 → jamais a, même sans A2 ; c:12.Nxe6 (écart 23-24) ; d:10.Nf3 = bruit
  C6 (10.Qe1 « sac 4 », ligne coupée sur …Nxe5) ou Nxd7 (piège 14) selon le run.
- Portée de « ouverture assumée » — Nico (« ok ») : seuil ≥ 20 avant le coup 10 pour
  erreurs / occasions manquées seulement ; occasions explosives cherchées dès le coup 1.
- Plan correctif validé par Nico (« ok », 2026-10-19) : tronçons 04-07 ci-dessous.
- Nico : libellés clairs dans les échanges (plus de codes A1/C6/M2 seuls).

### Correctif 2 (post-run live 07, audit `audit_run_live_07.md`)

- Nico (« on va suivre tes recommandations », 2026-10-19) :
  - repli « pire coup » **supprimé** (aucune position retenue → texte sans diagramme) ;
  - seuil du coup unique **20 → 15** (bruit 18-24 sur 12.Nxe6) ;
  - faits : **lignes calculées** par position (bilan matériel, pièces attaquées / en prise)
    + consigne « aucune attaque, défense ou colonne absente de ces lignes » ;
  - sans question : exclure le meilleur coup de la 1re passe des occasions explosives ;
    conversion C/F/T/D → N/B/R/Q dans le texte LLM (R laissé) ; consigne d : exiger suite
    du piège et réponses.
- Nico : réponse **moins verbeuse** — idéalement seulement moments critiques, coups au
  potentiel explosif, appréciation du niveau de jeu (format : question ouverte).
- Nico : « PGN unreadable » de 14:43:16 = mauvais format de son côté, ignoré.
- Nouvelle partie exemple (Écossaise / gambit Göring, Nico blancs, gagnée) : PGN dans
  `docs/sprint27/audit_run_live_07.md` §6. Moteur actuel (1 run) : seule position retenue
  `d:2.Nf3` (explosif 2.f4) ; le tournant 7...h6 (−18) / 8...Nxe5 (−14) puni par 8.e5 / 9.Nxe5
  n'est montré par aucune sorte.
- Format — Nico (« ok ») : réponse courte (ancre, 1 à 3 phrases par position, ligne
  « Niveau : » de 2 phrases) ; **axes de travail retirés**, ils reviennent après le sprint 28
  (modèle joueur façon RPG).
- Tournant — Nico (« ok ») : nouvelle sorte **e** (erreur adverse ≥ 15 punie, coup de Nico
  perte < 10, partie non décidée avant l'erreur), dans le budget ≤ 3 ; ordre a/b, e, c
  (choix Claude) ; Nico exige que **la variante de la punition** soit montrée.
- Niveau par partie — Nico (« ok ») : données de `summarize` (compteurs, précision par phase,
  erreurs adverses punies) → 2 phrases ; appréciation sur l'historique = sprint 28.
- Scope sprint 28 — Nico (« ok ») : modèle joueur (axes RPG + style sur l'historique, #81),
  pensé comme premier usage de la consolidation mémoire (#17 `aria_semantic`, #54
  REFLECTION, `extract_every_n_turns`).
- Plan correctif 2 : tronçons 08 (sélection), 09 (router), 10 (run live).

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_moteur_explosif.md` — `chess_coach/explosive.py`, sorte d, Threads=8, tests Morra / Dh5 | ✅ |
| 02 | `02_router_rendu.md` — flèche orange, légende, bloc enrichi, consigne | ✅ |
| 03 | `03_run_live.md` — run live (Nico) : Morra ✅ (8.Cd5, bruit 6.b4), Dame précoce ✗ (en-têtes indentés), letton ✗ (tout en ouverture) | ❌ |
| 04 | `04_selection_pgn.md` — en-têtes indentés, occasion explosive en bonus, ouverture assumée | ✅ |
| 05 | `05_moteur_sacrifice_suites.md` — sacrifice réel (ligne stabilisée + matériel offert), suites piège / réponses | ✅ |
| 06 | `06_router_notation_faits.md` — notation anglaise, pièces par camp, suites, idées d'ouverture | ✅ |
| 07 | `07_run_live_correctif.md` — run live (Nico) : moteur ✅ Morra / Dame précoce / letton ; ❌ Von Hennig (repli « pire coup » → erreur 4.Bc4) ; texte ❌ (notation française résiduelle, suite du piège omise, faits inventés) | ❌ |
| 08 | `08_selection_tournant.md` — fin du repli « pire coup », seuil coup unique 15, sorte e tournant, explosif ≠ meilleur de la 1re passe | ⏳ |
| 09 | `09_router_format_concis.md` — format court + Niveau, faits calculés (matériel, attaquées), bloc tournant + variante, consigne d, conversion C/F/T/D → N/B/R/Q | ⏳ |
| 10 | `10_run_live_correctif2.md` — run live (Nico) : Morra, Dame précoce, letton, Von Hennig, Écossaise Göring | ⏳ |

## Dettes

- Visée : #87 (fermée si run live 03 OK).
- Hors sprint (décision Q4) : #81 bilan joueur, rangement wing `echecs` / room par ouverture.
- Maia (lc0) = v2 de #87.
- **Sprint 28 pressenti — modèle joueur** (fusion #81) : axes de travail façon RPG (acquis
  après 3 validations, maîtrisé si jamais raté, priorité qui remonte en cas d'échec) +
  appréciation du style (mal joué / passif / solide / brillant) sur l'historique. Touche le palace prod.
  Retour des axes de travail dans la réponse d'analyse. À concevoir avec la consolidation
  mémoire (#17, #54, `extract_every_n_turns`).
- #84 (récit inventé) : traité partiellement par le tronçon 09 (faits calculés) ; résidu
  attendu, rédaction déterministe écartée.
- Nouvelle : échiquier d'analyse rejouable (chessground) avec flèches meilleur / explosif ;
  calque Chess.com limité à l'écran d'analyse post-partie (fair-play).
- Nouvelle : Groq 413 (limite 7000 tokens/min en entrée) sur chaque analyse d'échecs →
  repli DeepSeek systématique.
- Nouvelle : non-déterminisme moteur (Threads=8 + limites en temps), accepté au sprint 27.

## Questions ouvertes

Aucune.

## §REPRISE

Correctif 2 figé. Exécution : `/sprint-auto sprint 27` → tronçons 08, 09 (01-06 commités ;
03 et 07 = runs live KO). Puis run live 10 par Nico.
Lire `CLAUDE.md`, ce fichier, `audit_run_live_07.md`, puis le kickoff du tronçon.
