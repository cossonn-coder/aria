# Audit sprint 28 — modèle joueur (#81) sur le code au 2026-10-19 (tag `sprint-27`)

Audit avant conception. Lecture directe du code et du palace prod (lecture seule
sqlite `mode=ro`, sans ouvrir ChromaDB).

## 1. Source de données : les fiches `chess_game`

**Écriture** — `execution/routers/chess_router.py` `execute()` :

```python
game_hash = hashlib.sha256("".join(p.uci for p in analysis.plies).encode()).hexdigest()[:16]
summary = summarize(analysis)
try:
    write_chess_game(summary_text(analysis, summary), game_hash, extra=summary)
    ...
enriched = self._build_enriched(analysis, message, _anchor(summary), summary)
result = self.llm_execution_router.execute({...})
```

La fiche est écrite **avant** l'appel LLM : une lecture des fiches à cet endroit
inclut déjà la partie courante.

`memory/writer.py` `write_chess_game(text, game_hash, extra)` : wing `aria_episodic`,
room `chess`, type `chess_game`, `timestamp = _now_iso()` (heure d'**analyse**, pas de
la partie), doc_id `chess_game_<hash des coups>` → renvoyer la même partie remplace sa
fiche (pas de doublon, mais le timestamp est rafraîchi).

**Contenu** — `chess_coach/summary.py` `summarize()` : métadonnées scalaires
(`date`, `nico_color`, `color_source`, `opponent`, `elo_nico`, `elo_opponent`, `result`,
`outcome`, `termination`, `time_control`, `eco`, `opening`, `opening_line`, `n_plies`,
`nico_<qualité>` ×5, `first_error_nico`, `first_error_opponent`, `accuracy_<phase>` ×3,
`max_win_nico`, `min_win_nico`, `unconverted`, `saved`, `opponent_errors`,
`opponent_errors_punished`, `errors_low_clock`) + `plies_json` (par demi-coup : `ply`,
`move_number`, `color`, `san`, `uci`, `win_before`, `win_after`, `loss`, `best_san`,
`quality`, `phase`, `tags`, `clock`, `kind`). Tout axe de travail se recalcule donc sans
Stockfish à partir de `plies_json` (c'était l'intention du sprint 26).

Seuils de qualité (`analysis._quality`) : best = coup moteur ; blunder ≥ 30 ; mistake ≥ 20 ;
inaccuracy ≥ 10. Étiquette `hanging` (`analysis._tags`) : après le coup, une pièce du
joueur (hors roi) est attaquée et non défendue — inclut les sacrifices volontaires.

## 2. État du palace prod (2026-10-19, lecture seule)

16 fiches `chess_game`, toutes analysées le 2026-10-19 (sprints 26-27, code en évolution) :

| Adversaire | demi-coups | résultat | remarque |
|---|---|---|---|
| King_walks_19 | 46 | `*` | partie tronquée, `unconverted=True` |
| nojokeloco6789 | 38 | `*` | tronquée |
| Ami | 7 | 1-0 | partie de démonstration |
| Test | 15 | `*` | **test** |
| Test | 4 | `*` | **test** |
| CANNIBALISM_22 | 23 | `*` | tronquée, `unconverted=True` |
| 10 autres | 28-134 | 1-0 / 0-1 / ½ | parties réelles Chess.com, Elo 1296 → 1373 |

Constats :
- **Pollution** : 2 fiches « Test » et 1 « Ami » (7 demi-coups) ne sont pas des parties réelles.
- **Bug de données** : `unconverted = max(win) ≥ 80 and outcome != "win"` est vrai pour les
  parties à résultat `*` (outcome `unknown`) → 2 faux « avantages non convertis ».
- **Pas d'horloge** : `clock` est `None` sur les 16 fiches (`errors_low_clock = None`) →
  un axe « gestion de la pendule » n'aurait aucune donnée.
- Ordre chronologique : seule l'heure d'analyse est fiable (`date` absente sur 5 fiches,
  formats `2026-10-19` et `2026.10.19` mêlés).
- `aria_semantic` : **0 document** (dette #17 confirmée).

## 3. Lecture mémoire disponible

`memory/mempalace_bridge.py` : `retrieve_memories` / `retrieve_by_intent` /
`retrieve_semantic` (vectoriels) et `load_conversation_history` (non vectoriel, via
`get_by_metadata` injecté). **Aucune méthode ne lit les fiches `chess_game` par
métadonnées.** Il faut une méthode bridge du même modèle que
`load_conversation_history` (`where = {"type": "chess_game"}`), règle 2.

`ChessExecutionRouter.__init__(self, llm_execution_router)` : pas de bridge injecté.
`core/kernel.py:102` l'instancie ; `WebExecutionRouter` reçoit déjà `mempalace_bridge`
(précédent : un router lit via le bridge, règle 2 respectée, règle 3 non concernée —
c'est un router, pas un agent).

## 4. Consolidation mémoire (#17, #54, `extract_every_n_turns`)

- `write_semantic_fact` : **0 caller prod** ; doc_id `semantic_<subject>_<uuid>` → chaque
  appel crée un nouveau document (pas d'upsert stable : un profil réécrit à chaque partie
  s'empilerait).
- `retrieve_semantic` : 1 caller, `cognition/context_builder.py` (section « [Profil
  utilisateur stable] » de toute réponse LLM, requête vectorielle sur le message).
- `LLMRole.REFLECTION` : déclaré + chaîne DeepSeek dans `llm/llm_router.py:85`, 0 caller.
- `config.extract_every_n_turns = 5` : 0 lecteur.

Conclusion : il n'existe aucun mécanisme de consolidation. Le modèle joueur peut se
calculer **entièrement** à partir des fiches (déterministe, recalculable) ; l'écrire en
`aria_semantic` serait un cache dérivé (deux sources de vérité), sauf s'il sert ailleurs
que dans l'analyse de partie (conversation générale via `context_builder`).

## 5. Rendu actuel de l'analyse

`_build_enriched` : bloc faits (ancre, compteurs, ligne `Niveau (données)` = précision par
phase, erreurs adverses punies, résultat de **la partie seule**) + consigne de format
court terminée par une ligne « Niveau : » (mal joué / passif / solide / brillant) écrite
par le LLM. Les axes de travail ont été retirés au sprint 27 en attendant ce sprint.
Le texte LLM passe par `_to_english` puis est renvoyé tel quel.

Risques connus côté LLM : faits inventés (#92), consigne de variante ignorée (#89) → un
bloc d'axes écrit par le LLM hériterait de ces défauts ; un bloc écrit par le router est
exact par construction.

## 6. Points d'entrée hors PGN

`CHESS_ANALYSIS` n'est atteint que par détection déterministe de PGN
(`cognitive_classifier.py:281`). Une question « fais-moi mon bilan » sans PGN part en
conversation générale (LLM + souvenirs épisodiques vectoriels) : hors du chemin du
chess_router.
