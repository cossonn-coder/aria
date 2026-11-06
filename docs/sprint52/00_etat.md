# Sprint 52 — Niveau joué : état de conception

**Phase** : B terminée — conception **figée** le 2026-11-06 (OK de Nico).
**Branche** : `feat/sprint52-niveau`.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---------|-------|------|
| 01 | `01_niveau_bilan.md` | `chess_coach/level.py` (performance, rang) + bilan Telegram (Elo sur 🎯, ligne 🏅 en bas) | ✅ |
| 02 | `02_parties_ouvertures.md` | `/parties`, `/ouvertures` : performance Elo, infos générales en bas | ✅ |
| 03 | `03_echiquier.md` | Échiquier : Elo sur la précision, rang + performance d'ouverture sur PGN chargé | ⏳ |
| 04 | `04_run_live.md` | Run live (Nico) | ⏳ |

## Cible d'origine (kickoff `context_kickoff_sprint_52.md`)

Niveau joué estimé par Maia-2 par camp + tendance : **abandonné après mesure** (voir ci-dessous).

## Décisions arrêtées

- 2026-11-06 — Cible : **mesurer d'abord** la variante calibrée sur toutes les fiches prod
  (copie du palace) avant de trancher Maia vs réorientation.
- 2026-11-06 — Si réorientation : performance Elo dans `/ouvertures <nom>` = total + 5 dernières.
- 2026-11-06 — Bilan : Elo officiels sur la ligne précision, « 🎯 Précision : toi 84 % (1354) ·
  adversaire 79 % (1332) ».
- 2026-11-06 — **Échiquier ARIA aussi** (demande de Nico), les trois volets :
  (a) Elo des champs sur la ligne précision (`index.html:622`) ;
  (b) niveau Maia par camp, **seulement si la mesure le valide** ;
  (c) tendance / performance Elo sur l'échiquier (lecture des fiches côté serveur, via
  `mempalace_bridge` : règle 2 ; le serveur de l'échiquier ne lit aucune fiche aujourd'hui, à auditer).

- 2026-11-06 — **Maia abandonné** pour le niveau (mesure complète : Spearman 0,31 brut / 0,21
  calibré [n=251 camps, 166 fiches]). Nico : « trouve comment calculer l'Elo estimé de la partie
  jouée une fois qu'elle est terminée ». Volet (b) échiquier : remplacé par le rang de précision (décision suivante).
- 2026-11-06 — **Les informations générales vont en bas du message** (Telegram défile en bas, c'est
  ce que Nico voit en premier) : `/parties` et `/ouvertures`, ligne du jour / bilan + performance Elo
  en bas ; règle générale pour les nouvelles lignes du sprint.

- 2026-11-06 — Par partie : **rang de la précision dans tes parties** (« ta 12e meilleure partie sur 140 »),
  depuis les fiches (140/166 ont `accuracy`). Pas d'Elo estimé.
- 2026-11-06 — Échiquier, tendance : **ouverture chargée** (performance dans cette ouverture et cette
  couleur, total + 5 dernières) + rang de la partie ; lecture seule des fiches injectée par `bot.py`.

## Piste « Elo estimé par la précision » : NON exploitable (audit §7.b)

Calibration Lichess, 17 044 camps en 10 min : erreur médiane 128 = constante (128). Proposition :
précision rapportée à l'habitude (rang dans tes parties / percentile à Elo égal), audit §8.

### Historique de la piste

Nos fiches ne peuvent pas calibrer précision → Elo (adversaires appariés : |ΔElo| médian 32 ;
précision de Nico ±10 pts d'une partie à l'autre ; Spearman 0,16 [n=270 camps]). Calibration
externe sur la base Lichess (parties avec `%eval` + Elo des deux camps, 400-2800) : téléchargement
`lichess_db_standard_rated_2014-01`, prototype fait : non exploitable (audit §7.b).

## Constat d'audit (bloquant, historique)

Piste du kickoff mesurée (`audit_niveau_maia.md` §2) : vraisemblance Maia par tranche biaisée
vers `>=2000` (11 camps sur 16), fourchette sur toute la plage ; variante calibrée : erreur
médiane ≈ 460 [n=16 camps]. Coût 6-17 s par partie [n=8].

## Verdict de la mesure (audit §6)

Maia-2 non exploitable comme estimateur de niveau : Spearman ≈ 0,35, erreur par partie 340-420
[n=140 camps, 70 fiches] ; en fenêtres de 10 parties, sauts de ≈ 900 points sans suivre l'officiel.

## Questions ouvertes, lot 1 (répondues)

1. Que faire de la cible « niveau Maia » : réorienter vers des mesures solides (recommandé),
   mesurer d'abord la variante calibrée sur toutes les fiches prod, ou changer de sujet ?
2. Si réorientation : Elo officiels dans le bilan + performance Elo dans `/ouvertures`/`/parties` ?
3. Tendance : sur quelles parties (toutes, 5 dernières, par ouverture) ?

## Dettes

- Ouverte par le sprint : #203 rang de précision sur l'échiquier : une partie collée qui n'est pas une
  fiche n'est pas comptée dans le total (« sur 140 » au lieu de 141) ; cosmétique, à observer.
- Touchées sans fermeture : #166 (l'échiquier lit désormais les fiches, toujours sans authentification).

## §REPRISE

Conception figée. Tronçon 01 fait : `chess_coach/level.py` (`performance`, `accuracy_rank`),
bilan avec Elo sur 🎯 et ligne 🏅 en dernier. Tronçon 02 fait (552 tests verts) : `/parties` (parties de la
plus ancienne à la plus récente, bilan du jour + performance en dernier), `/ouvertures` (moins jouée → plus
jouée, ligne Performance globale en dernier), `/ouvertures <nom>` (détail puis bilan + Performance en bas de
chaque section, section la plus jouée en bas). Dans `/parties`, les stats d'ouvertures gardent l'ordre plus
jouée → moins jouée (kickoff muet). Prochaine étape : tronçon 03 (`03_echiquier.md`), puis run live 04 par Nico.
Mesures (Maia, Lichess) : `audit_niveau_maia.md` ; scripts de prototype hors repo (scratchpad), non nécessaires.
