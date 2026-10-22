# Sprint 29 — audit des retours du run live (2026-10-22, HEAD `ef63d32`)

Quatre retours de Nico après le run live 06 (4 parties : kamal_qasim, Falestinhurra,
YouGotMyRook, Mu7saad — `run_live_retours_parties.txt`, une partie par ligne :
`coups|couleur de Nico|Elo adverse`).

## 1. Plus de flèche orange (occasions explosives)

Constat : rendu intact (`chess_router.py:473`, `render.py:95` : `alt_uci` si `kind == "d"`).
Le journal donne `chess_explosive … found=0` sur les 4 parties.

Cause : la règle du tronçon 04 (`explosive._admissible`) exige
`E(candidat) ≥ E(meilleur) + _GAIN_MIN (10)`, avec E = espérance humaine Maia
(`_expectation`, probabilités renormalisées sur les réponses ≤ 90 % cumulés).
Mesure (spy sur `_admissible`, mêmes 4 parties, Elo adverse du PGN) :

| Partie | Candidats approfondis | Gain max (E − E meilleur) |
|---|---|---|
| kamal_qasim | 49 | 5,9 (Bc7, evidence activity) |
| Falestinhurra | 40 | 3,5 |
| YouGotMyRook | 27 | 0,3 |
| Mu7saad | 58 | 5,5 (Ng4) |

Gain max 5,9 sur 174 candidats [n=4 parties] : le seuil 10 n'est jamais atteint.
Seuil 5 → 2 occasions sur 4 parties [n=4]. Raison structurelle : Maia met l'essentiel
de sa masse sur les réponses correctes, l'écart d'espérance avec le meilleur coup
reste faible.

Règle d'avant (tag `sprint-28`, `_admissible`) : avantage clair ET
(perte ≤ 5, ou perte ≤ 15 si piège ≥ 10) ET (sacrifice ≥ 1 pion OU piège ≥ 10),
piège = % de gain adverse après sa meilleure réponse − après la **prise naturelle**
du matériel offert (`_natural_capture`). Score = sacrifice (plafond 5) + forçant +
piège/5 + volatilité/10. C'est cette règle qui produisait les « idées risquées »
appréciées par Nico (sacrifices, pièces offertes).

Elo : Maia reçoit déjà l'**Elo adverse** (`find_explosive` → `reply_distribution(…, elo)`),
donc la probabilité des réponses s'adapte au niveau adverse. Le seuil de gain, lui,
est fixe. L'Elo de Nico n'intervient nulle part dans la recherche.

## 2. Légende : variante expliquée + idée générale

Tronçon 05 fonctionne (`chess_caption_split OK images=3` ×4). Contenu actuel d'une
entrée (consigne `chess_router.py:570-584`) : « de 1 à 3 phrases : le coup, l'idée, le
chiffre clé ». Le bloc fournit pour chaque position la ligne du meilleur coup
(`meilleur …, ligne : <pv>`), mais aucune consigne ne demande de l'expliquer pour les
sortes a/b ; la variante n'est demandée que pour c/e (tournants) et d. Pas
d'« idée générale de la position » demandée. Limite Telegram : légende ≤ 1024 car.
(`_fit_entry` coupe à la dernière phrase).

## 3. Précision gonflée

Code : `summary._accuracy` = formule Lichess par coup (sans le bonus +1), puis
**moyenne arithmétique** par phase (`summary.py:103-107`).
Lichess (`lila/modules/analyse/.../AccuracyPercent.scala`) : par couleur,
précision = (moyenne pondérée par la volatilité + moyenne harmonique) / 2 ;
poids = écart-type du % de gain sur une fenêtre glissante (taille = coups/10, bornée
2-8), borné 0,5-12 ; bonus +1 par coup ; une seule valeur pour la partie.
Chess.com (CAPS2) : propriétaire, non public ; réputé proche de Lichess, un peu plus
généreux [non mesuré].

Recalcul sur les 4 parties (partie entière, pas par phase) :

| Partie | Arithm. (actuel) | Harmonique | (Arithm.+Harm.)/2 |
|---|---|---|---|
| kamal_qasim | 92 | 89 | 91 |
| Falestinhurra (gaffes −78, −84) | 88 | 16 [plancher 1 %/coup] | 52 [idem] |
| YouGotMyRook | 91 | 87 | 89 |
| Mu7saad | 87 | 84 | 85 |

(Approximation : pondération par volatilité non appliquée.) Partie propre : écart
faible ; partie à gaffes : la moyenne arithmétique les noie.
Écart adjacent : le LLM a écrit « mal joué en finale » alors que les gaffes 38/39 sont
classées milieu de partie (dames sur l'échiquier, `analysis._phase`).

## 4. Arrêt du service (SIGTERM → 90 s → SIGKILL)

Unit : `Restart=on-failure`, pas de `TimeoutStopSec` (90 s par défaut), pas de
`KillMode` (control-group). Processus : 0 enfant, ~100 threads (65 python, 32
`tokio-runtime-w` = chromadb Rust, 3 `sqlx-sqlite`).

Test 1 (14:02, processus up 35 min, 4 parties analysées) : py-spy avant SIGTERM →
boucle au repos (`MainThread` dans `select`). 15 s après SIGTERM : vivant, py-spy
« Failed to find a python interpreter » → bloqué en finalisation. Sortie code 0
entre 15 et ~60 s [n=1, délai exact non mesuré] → pas de redémarrage auto
(`on-failure`).

Reproduction isolée (sortie après fin du script) : chromadb PersistentClient 0,75 s,
sentence-transformers 1,9 s, Maia 2,0 s [n=1 chacun] → aucune brique seule ne
bloque.

Test 2 (sonde : SIGTERM puis échantillonnage /proc toutes les 0,5 s, après une
analyse) : sortie en 8,7 s [n=1] ; thread principal alternant R et **D** (attente
disque) pendant la finalisation ; threads tokio qui disparaissent progressivement.
VM : 4,6 Go RAM, 3,8 Go de swap occupés ; systemd a relevé 672 Mo de swap pour aria.
Diagnostic : finalisation Python ralentie par la relecture des pages en swap, d'autant
plus longue que le processus a tourné longtemps (9 s / 15-60 s / > 90 s [n=3]).
Correctif : `os._exit(0)` après l'arrêt propre de PTB (tronçon 10).

Quarantaine HNSW : **non liée au SIGKILL** (correction de la première lecture).
Le segment `dba15bea` (`mempalace_drawers`) a 11 dossiers `.drift-*` depuis le 15/10,
dont un à 14:17 après un arrêt propre (code 0, 14:03). Cause probable : mempalace pose
`hnsw:sync_threshold = 50_000` → HNSW quasi jamais persisté, quarantaine au premier
accès de chaque processus. Dette #105, hors sprint.
