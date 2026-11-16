# Sprint 60 — état du sprint

**Phase** : suspendu le 2026-11-16 (Nico, insatisfait des résultats), rien de figé, aucun code.
**Sujet** : lecture fiable d'une photo d'échiquier physique, quel que soit l'angle, avec
vérification avant de faire confiance à l'analyse Stockfish.
**Branche** : à créer au moment de figer : `feat/sprint60-photo-echiquier`, depuis `main` @ `f4d9c29`
(58 et 59 mergés le 2026-11-16).
Audit : `docs/sprint60/audit_photo_echiquier.md`.

## Contexte hérité

- Sprint 59 : run live 07 fait deux fois le 2026-11-13 (17:24 et 23:54), journal conforme
  aux 5 critères (étape 5 seulement à 17:26). Rendu Telegram à confirmer par Nico.
- Mesure photo physique : 63/64 [n=1 photo, Gemini 3.5-flash], fou noir c5 lu cavalier.
  Photo : `received_images/AgACAgQAAxkBAAIRqGr3OzhB…ADPQQ.jpg`.
  Position vraie : `r1bqk2r/ppp2ppp/2p2n2/2b3B1/4P3/3P4/PPP2PPP/RN1QKB1R b KQkq - 0 1`.

## Décisions arrêtées

- Nouveau sprint (60), pas réouverture du 59 (Nico, 2026-11-14).
- Pas de double lecture (Nico, 2026-11-16). Raison : 3.8-flash indisponible, deux lectures
  3.5 peuvent se tromper ensemble (audit §3), coût en attente.
- ARIA résout toujours la lecture proposée ; Nico confirme (rien à faire) ou corrige
  (Nico, 2026-11-16).
- Correction par message « c5 fou noir », plusieurs cases séparées par des virgules
  (Nico, 2026-11-16) : nouvelle position, Stockfish relancé, diagramme corrigé.
- Corpus de mesure : 16 photos (P1/P2/P3 × face/biais/côté/plongée, P1 aussi le soir), envoyées
  par Nico sur Telegram avec la légende « corpus <nom> » (Nico, 2026-11-16). Liste :
  `docs/sprint60/corpus_photos.txt`. Collecte : `venv/bin/python docs/sprint60/collect_corpus.py`
  (lit l'épisodique `image_input`, copie dans `docs/sprint60/corpus/<nom>.jpg`). FEN vraies :
  P1 `r1bqk2r/ppp2ppp/2p2n2/2b3B1/4P3/3P4/PPP2PPP/RN1QKB1R`,
  P2 `r1bq1rk1/pp1nbppp/2p1p3/3n2B1/2BP4/2N1PN2/PP3PPP/2RQK2R`,
  P3 `8/5k1p/3n2p1/1p1P1p2/1P3P2/3BK3/6P1/8`.

- Pivot (Nico, 2026-11-16) : captures d'écran chess.com d'abord, photo physique plus tard
  (« même ça ne fonctionne pas »). Mesures photo conservées (audit §5), corpus dans
  `docs/sprint60/corpus/`. Diagnostic capture : audit §6 (secours local fautif, Gemini 64/64).

## Questions ouvertes

- Correction après une lecture impossible (aujourd'hui sans marqueur, donc non corrigeable).
- Forme exacte du message de correction (noms des pièces, « vide », trait).
- Orientation sur 4 côtés : la mesure P1 montre que ça ne suffit pas (côté 53-54/64 même
  bien tourné) → proposé : périmètre réduit à face/plongée.
- Décompte avec les pièces hors plateau (idée de Nico, 2026-11-16) : ligne HORS: + contrôle
  pièces sur le plateau + hors plateau ≤ jeu complet, dames exclues → doute nommé.
- Corpus : positions, angles et lumières (plan proposé, en attente des photos).

## Dettes ouvertes par la conception (2026-11-16)

| # | Dette | Constat | Piste |
|---|---|---|---|
| 1 | Lecteur local chess.com faux sans prévenir | 2 captures sur 2 fausses (fou noir sur case foncée effacé, dame lue tour/fou) ; audit §6 | Références ref1/ref2 (FEN audit §6) + ne plus effacer les pièces noires sur cases foncées |
| 2 | Lecture de secours non signalée | Éval Stockfish fausse présentée avec assurance | Dire « lecture de secours, vérifie la position », ou refuser si doute |
| 3 | FEN collée en texte non lue | Déjà ouverte au sprint 59 | Lire la FEN de « Partager » chess.com |
| 4 | Quota Gemini | 429 après ~25 appels sur la journée [n=1 jour, plafond non vérifié] ; 3.8-flash en 503 | Vérifier le palier ; mesures de conception économes, jamais pendant un test de Nico |
| 5 | Correction de lecture | Décidée (`c5 fou noir, d7 vide`), non faite ; lecture impossible non mémorisée | Voir décisions ci-dessus |
| 6 | Photo d'échiquier physique | Face/plongée 63/64 au mieux, biais/côté inutilisables [n=1 position, 8 photos] ; audit §5 | Décompte avec pièces hors plateau (idée de Nico) |
| 7 | Clé API Gemini en clair dans les exceptions httpx | URL `?key=` dans le message → journal ARIA | Masquer la clé dans les logs |

## §REPRISE

Sprint suspendu. Pour reprendre : lire `CLAUDE.md`, ce fichier, l'audit (§5 photo, §6 capture).
Photos du corpus : `docs/sprint60/corpus/` (locales, non commitées).
