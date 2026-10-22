# Sprint 29 — audit du code (2026-10-22, HEAD `d2a3150`)

Cinq sujets : motifs tactiques (#100), coup le plus piégeant, explication en légende,
erreur kernel vide, réponse perdue signalée. Code lu en entier : `chess_coach/*.py`,
`execution/routers/chess_router.py`, `interfaces/telegram_interface.py`,
`execution/execution_dispatcher.py`, `core/kernel.py` (`handle_event`, `_normalize`).

---

## 1. Motifs tactiques (#100)

### Ce qui existe

- `player_model.build_profile(games)` (pur) rejoue les fiches `chess_game` décodées
  (`plies_json`) ; il ne voit **ni FEN, ni PV, ni best_uci** : seulement par demi-coup
  `ply, move_number, color, san, uci, win_before, win_after, loss, best_san, quality,
  phase, tags, clock, kind, difficulty, second_gap` (`summary.py:655-668`).
- Épreuve = coup de Nico avec `difficulty` (après le coup 10), partie non décidée
  (10 ≤ win_before ≤ 90) et enjeu (loss ≥ 10 ou second_gap ≥ 10) (`player_model.py:155-161`).
  Trouvé = loss < 10.
- Rattachement aux thèmes : `_move_themes` (`player_model.py:140-152`) — `hanging`
  (tag `hanging` du coup **joué** ou « x » dans best_san), `punish`, `convert`,
  `endgame`. `opening` (1 épreuve/partie) et `result` à part.
- Global = moyenne arithmétique des 6 thèmes (`_mean`, `:136-137`), tenu à jour après
  chaque épreuve (seuil « Coup de maître »).
- Affichage : `chess_router._progression_block` (`:275-313`) itère `LABELS` ; un thème
  sans delta n'est pas affiché ; lignes fusionnées si même épreuve décisive.
- Seule détection « motif » existante : `explosive.py` (sacrifice de ligne, matériel
  offert `_natural_capture`, étiquettes forçantes check/capture/threat), calculée
  uniquement pour les candidats explosifs, jamais pour le meilleur coup d'une épreuve.

### Constats

1. **Détection de motif inexistante** pour le meilleur coup d'une épreuve.
2. **Données suffisantes sans changer le stockage** : `plies_json` contient tous les
   coups joués (`uci`) → la position avant chaque coup se reconstruit par rejeu depuis
   la position initiale ; `best_san` se parse sur ce board. Une détection pure
   « board + meilleur coup » couvre donc **rétroactivement** toutes les fiches saison 1.
   Limite : pas de PV stockée → motifs qui exigent la suite (sacrifice réel, combinaison
   en 2 temps) indétectables sans changer la fiche.
3. **Dilution du Global** : Global = moyenne des thèmes. Ajouter N motifs peu
   alimentés (classement resté à l'Elo de départ) tire le Global vers l'Elo de départ.
4. `hanging` est déjà un motif (« pièce en prise » = gain de matériel simple) ; il est
   mal défini (tag du coup joué, ou toute prise dans best_san).
5. Palace prod : lecture seule (fiches relues par `bridge.load_chess_games`). Aucune
   écriture nouvelle si détection par rejeu → calibrage faible applicable.

## 2. Coup le plus piégeant (sorte d, `explosive.py`)

### Ce qui existe

- Positions éligibles : coups de Nico, coup ≤ 20, 35 ≤ win_before ≤ 75, loss < 10
  (`explosive.py:282-287`). Budget global 30 s.
- Candidats : MultiPV 5 + coups « de forme » (échec, prise, case attaquée), perte
  ≤ `_TRAP_WINDOW` (15), hors meilleur coup / coup joué ; 3 approfondis max.
- `_deepen` : réponses MultiPV 3 adverses ; « réponse logique » = **prise naturelle**
  du matériel offert (`_natural_capture`), sinon 1re réponse **moteur** ; piège =
  écart de % de gain adverse entre sa meilleure réponse et la prise naturelle.
- `_admissible` (`:240-245`) : avantage clair requis + (loss ≤ 5, ou ≤ 15 si piège ≥ 10)
  + (sacrifice ≥ 1 ou piège ≥ 10). Score = sacrifice + forçant + piège/5 + volatilité/10.

### Constats

1. La difficulté de défense n'est **pas mesurée côté humain** : la « réponse logique »
   est soit une prise matérielle, soit le meilleur coup moteur. D'où #91 (la réponse
   logique est une des bonnes réponses) et l'absence de pièges « positionnels »
   (coups naturels mais perdants qui ne sont pas des prises).
2. Le frein de Nico (« quitte à être moins bien sur jeu parfait ») est la fenêtre
   5 / 15 pts **et** l'exigence sacrifice-ou-prise-naturelle.
3. **Maia-2 est déjà chargé** (sprint 28, `difficulty.py`) : sa politique donne la
   distribution des coups humains d'un Elo donné dans une position. Appliquée à la
   position après le candidat, à l'Elo adverse, elle donne l'espérance de % de gain
   de Nico face à un humain : E = Σ P_maia(réponse) × win_Nico(réponse). C'est la
   mesure directe de « coup piégeant ». `_probabilities` ne rend que P(meilleur coup) ;
   il faut une variante qui rende la distribution des k coups les plus probables.
4. Coût : 1 passe Maia par candidat (batchable) + 1 évaluation Stockfish des réponses
   Maia hors MultiPV (`root_moves`). Le budget de 30 s reste le garde-fou.
5. Maia absent (échec de chargement) → aujourd'hui la difficulté reste None et
   l'analyse continue ; le coup piégeant devra suivre la même règle (repli = règle actuelle,
   ou pas de sorte d).

## 3. Explication en légende

### Ce qui existe

- Router : une image par position critique, légende = `_caption()` (une ligne factuelle,
  `chess_router.py:373-391`). Texte LLM unique : 1re ligne ancre, une entrée par
  position « Position 1, 2, 3 », puis « Niveau : » (consigne `:521-533`), puis bloc
  Progression ajouté par le router.
- Interface : `send()` envoie les photos (légende tronquée **en silence** à 1024 car.,
  `telegram_interface.py:200`) puis le texte.
- Écriture épisodique : faite par `LLMExecutionRouter` avec le texte LLM complet —
  indépendante du découpage d'affichage.

### Constats

1. Le format imposé « Position N » rend un **découpage par le router** possible sans
   second appel LLM : chaque entrée est rattachée à l'image de même numéro.
2. Le LLM ne respecte pas toujours le format (#89 : variante non montrée) → il faut un
   repli : entrée introuvable → légende factuelle seule, texte complet inchangé.
3. Longueur : légende factuelle (~100 car.) + entrée (1-3 phrases, plus pour la sorte d)
   tient sous 1024 en général ; au-delà, la troncature actuelle coupe en plein mot.

## 4. Erreur kernel vide

- `ExecutionDispatcher.dispatch` (`execution_dispatcher.py:40-45`) attrape `Exception`
  et ne garde que `str(e)` : **aucun log, aucune trace, pas le type**. `str(TimeoutError())`
  = "" → `[KERNEL] execution error: ` vide (21/10 10:14).
- `AriaKernel._normalize` (`core/kernel.py:233-234`) : `print()` (dette #71) ; le module
  kernel n'a **pas de logger**.
- Correctif évident : `log.exception` dans le dispatcher (type + trace + router), `log.error`
  dans le kernel. Pas d'arbitrage de fond.

## 5. Réponse perdue signalée

- `_send_with_retry` : 3 tentatives (attentes 2 s, 4 s) puis l'exception remonte au
  handler PTB `_on_error` → une ligne WARNING (`telegram_interface.py:71-74`). La réponse
  est perdue, Nico n'en sait rien.
- Cas `images_text` : un échec de photo interrompt aussi le texte qui suit.
- La coupure du 20/10 a duré ~15 min (3 TimedOut 14:28-14:42) : allonger les réessais
  de quelques secondes n'aurait pas suffi.
- Piste la plus robuste : garder la réponse non livrée en RAM (par chat_id) et la
  livrer **au message suivant de Nico** (le réseau marche forcément puisqu'il est reçu),
  précédée d'un avertissement. Perdue au redémarrage (accepté ?).
