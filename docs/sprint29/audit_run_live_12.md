# Sprint 29 — audit de la légende après le run live 12 (phase A''')

HEAD `bc7551b`, 2026-10-22. Reproduction hors service (scripts dans le scratchpad, non commités) :
`analyze` + `summarize` + `ChessExecutionRouter._build_enriched` sur la partie 1 de
`run_live_11_parties.txt`, puis 2 appels LLM réels (même rôle REASONING, même system prompt
soul + profil + `PROMPT` AnalystAgent, contexte cognitif vide) **sans historique**.

## Symptôme (run live 12)

22 entrées sur 4 parties, toutes du moule « Position <éval>, <attaquées>. Le meilleur est X, qui
<1 fait> et maintient N % de gain. » Aucune variante racontée. « aucune pièce attaquée » 6 fois
[sur 22 entrées]. « maintient N % » n'a jamais figuré dans `chess_router.py` (`git log -S"maintient"` vide) :
tournure inventée par le LLM puis reconduite d'une réponse à l'autre.

## Chemin des données

`chess_router.execute` (`execution/routers/chess_router.py:532`) → `_build_enriched` → payload
`content = enriched` → `LLMExecutionRouter._run_pipeline` (`execution/routers/llm_router.py:100`) :
1. `retrieve_memories(message)` + `retrieve_by_intent` → `build_context_block` (épisodique,
   extraits de 400 car. des interactions « USER: … ARIA: … » passées) ;
2. `load_conversation_history(chat_id, n=config.max_history_turns * 2)` = **20 messages** ;
3. `AnalystAgent.run` (`agents/analyst_agent.py:31`) : `messages = [system] + history + [user]` ;
4. fin de pipeline : `write_conversation_turn(user, message)` où `message` = **le message enrichi
   complet** (≈ 9 000 car. [partie 1]), puis `write_conversation_turn(assistant, result)`.

## Piste 1 — imitation de l'historique : CONFIRMÉE

- Les 20 messages d'historique d'une analyse = les 10 tours précédents. Pendant un run live, ce
  sont tous des analyses d'échecs : 10 messages enrichis (avec les **anciennes** consignes des
  tronçons 05/09) + 10 réponses au moule « Position équilibrée … Le meilleur est … ». Soit
  ≈ 110 000 car. d'exemples [estimé : 10 × (9 000 + 2 000)] qui pèsent plus que la consigne.
- Mesure : même message enrichi, **sans historique**, 2 appels → le moule disparaît totalement
  (0 « Position équilibrée », 0 « maintient », 0 « aucune pièce attaquée ») [n=2].
- Le moule s'auto-entretient : chaque réponse écrite en historique devient l'exemple suivant.

## Piste 2 — ordre de la consigne : RÉFUTÉE comme cause principale

Sans historique, le LLM suit l'ordre (idée générale puis variante). Mais il **liste** la variante
au lieu de la raconter : « Variante : 6.cxd4 Bb4+ 7.Nc3 d6 8.Bc4 dxe5. » [n=2]. Les faits fournis
(« Bb4+ (échec) », « dxe5 (prend pion e5) ») ne sont pas repris. Le LLM ne raconte pas de
lui-même, même sans influence d'historique.

Nouveau défaut révélé : **positions omises**. Appel 1 : Positions 1-3 seulement (sur 6) ; appel 2 :
Position 4 sautée [n=2]. La consigne écrit « dans l'ordre Position 1, 2, 3 » : lue comme une
liste fermée. En prod, une entrée manquante → `chess_caption_split FALLBACK` (repli complet).
Le run live 12 n'en a pas souffert (`OK` 4/4) parce que l'historique imposait 6 entrées.

## Piste 3 — contenu réel du message : VÉRIFIÉ, présent mais maigre

Extraits réels (partie 1, reproduction) :

```
meilleur 3.d4, ligne : 3.d4 exd4
faits : 3.d4 3...exd4 (prend pion d4)
...
meilleur 14.Bg3, ligne : 14.Bg3 Nf5
faits : 14.Bg3 14...Nf5
...
meilleur 21.Rhe1, ligne : 21.Rhe1 Bxf3 22.Rxe7+ Bxe7 23.Qc7 Kf7
faits : 21.Rhe1 (attaque Qe7) 21...Bxf3 (prend Nf3) 22.Rxe7+ (prend Qe7, échec) 22...Bxe7 (reprend) 23.Qc7 (attaque pion c6) 23...Kf7
```

- Lignes `faits :` et `évaluation :` présentes dans toutes les positions ✅.
- Lignes souvent courtes (2 demi-coups) et coups calmes sans fait (Bg3, Nf5, d6, O-O hors
  « roque ») → rien à raconter hors moments tactiques.
- Les lignes `matériel : égal` / `attaquées : aucune` restent dans le bloc : la source de la
  paraphrase interdite est toujours fournie.
- Les analyses ne sont pas déterministes : la reproduction trouve des occasions explosives aux
  coups 3 / 6 / 14 contre 2 / 6 / 18 en prod (même code). Hors sujet, noté.

## Conclusion

Deux causes cumulées :
1. **L'historique** (20 messages d'analyses passées) impose le moule ; le retirer pour l'analyse
   de partie suffit à le faire disparaître [n=2].
2. **Le LLM ne raconte pas la variante** même sans historique : il la recopie. Les faits sont
   calculés par le code (tronçon 13) ; le récit coup par coup peut l'être aussi.
Défaut induit à traiter avec : consigne « Position 1, 2, 3 » → positions omises sans historique.

## Hors scope (dettes)

- `context_block` épisodique : extraits d'analyses passées (400 car., surtout l'en-tête du message
  enrichi) ; influence non mesurée.
- Le message enrichi complet (≈ 9 000 car.) est écrit en historique et en épisodique à chaque partie.
- Non-déterminisme de l'analyse (occasions explosives différentes d'un passage à l'autre).
