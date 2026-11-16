# Sprint 60 — état du sprint

**Phase** : A (audit + arbitrages), rien de figé.
**Sujet** : lecture fiable d'une photo d'échiquier physique, quel que soit l'angle, avec
vérification avant de faire confiance à l'analyse Stockfish.
**Branche** : à proposer (`feat/sprint60-photo-echiquier`, partie de
`feat/sprint59-position-image`, ou après merge de 58/59).
Audit : `docs/sprint60/audit_photo_echiquier.md`.

## Contexte hérité

- Sprint 59 : run live 07 fait deux fois le 2026-11-13 (17:24 et 23:54), journal conforme
  aux 5 critères (étape 5 seulement à 17:26). Rendu Telegram à confirmer par Nico.
- Mesure photo physique : 63/64 [n=1 photo, Gemini 3.5-flash], fou noir c5 lu cavalier.
  Photo : `received_images/AgACAgQAAxkBAAIRqGr3OzhB…ADPQQ.jpg`.
  Position vraie : `r1bqk2r/ppp2ppp/2p2n2/2b3B1/4P3/3P4/PPP2PPP/RN1QKB1R b KQkq - 0 1`.

## Décisions arrêtées

- Nouveau sprint (60), pas réouverture du 59 (Nico, 2026-11-14).

## Questions ouvertes

(voir arbitrages en cours dans la conversation ; reportés ici une fois tranchés)

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `docs/sprint60/audit_photo_echiquier.md`.
Prochaine étape : arbitrages de Nico (vérification, détection du doute, corpus de mesure).
