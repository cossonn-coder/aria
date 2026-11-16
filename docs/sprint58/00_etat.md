# Sprint 58 — état du sprint

**Phase** : clos le 2026-11-16 (tag `sprint-58`), mergé dans `main` avec le sprint 59.
Run live 02 non fait : clôture décidée par Nico sans run dédié.
**Branche** : `feat/sprint58-detection-echecs` (depuis `main` @ `1ce1e94`).
**Sujet** : #211, contexte échecs trop lourd → resserrer la détection des questions d'échecs.
Audit : `docs/sprint58/audit_contexte_echecs.md`.

## Carte des tronçons

| # | Tronçon | Kickoff | État |
|---|---|---|---|
| 01 | Détection resserrée des questions d'échecs | `01_detection_echecs.md` | ✅ (598 tests verts) |
| 02 | Run live (Nico) | `02_run_live.txt` | ⏭ non fait (clôture Nico) |

## Décisions arrêtées

- Cible : #211 (choix de Nico, 2026-11-12).
- Taille : on accepte que les questions d'échecs sautent groq (deepseek-flash, 1-2 s) ; ni la liste
  ni les stats ne sont allégées. Raison : la liste n'est pas la cause principale (audit §3.1), le
  saut coûte peu.
- Détection resserrée : `partie`, `victoire`, `défaite`, `nulle` ne déclenchent plus qu'après
  ma/mes/cette/ces ou un nombre ; `adversaire` et `games` retirés ; pseudos de Nico
  (`config.chess_usernames`) ajoutés. Raison : faux positifs reproduits (foot, Napoléon, adversaire
  politique). Prix accepté : « préviens-moi quand l'adversaire… », « combien de victoires cette
  semaine ? » ne déclenchent plus.
- « toutes » : pas de plafond (Nico).

## Run live (tronçon 02, Nico)

Messages dans `02_run_live.txt`. Succès : message 1 → `chess_games_context` au journal ;
messages 2 et 3 → aucune ligne `chess_games_context`, et la réponse ne parle pas d'échecs.

## Dettes

- Touchée : #211 (détection ; saut groq accepté ; taille non réduite).
- Ouvertes, non touchées : `load_chess_games` relu à chaque message (0,3 s à chaud), liste
  « toutes » ≈ 35 000 car. [313 fiches].

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳.
Tronçon 01 fait : `_CHESS_WORDS` resserré + pseudos `config.chess_usernames` dans
`mentions_chess_games` (`execution/routers/llm_router.py`), parametrize 8 cas dans
`tests/execution/test_llm_execution_router.py`, ligne #211 du kickoff mise à jour.
Sprint clos. Suite : sprint 59 (même branche de merge).
