# Sprint 53 — audit : récits d'échecs du LLM (dettes #187, #92)

Date : 2026-11-09. Code lu : `execution/routers/chess_router.py` (`_build_enriched`,
`_move_fact_items`, `_move_facts`, `_told_moves`, `_compared_lines`, `_variant_line`,
`_explosive_lines`, `_caption`), `chess_coach/analysis.py` (`CriticalPosition`,
`select_critical`, `_evidence`, `forcing_line`, `assign_forcing_lines`),
`chess_coach/summary.py` (`story_line`).

## 1. Les deux dettes

- **#187** (sprint 50, run live 3 ou 4) : le LLM écrit « Qxf1+ échange ta dame contre un
  cavalier » alors que le coup gagne le cavalier. Diagnostic de l'époque : « il ne reçoit
  pas ce que le coup joué capture » [n=1]. Le texte d'origine n'est conservé ni dans les docs ni
  dans le journal accessible (grep `Qxf1` vide) : on ne sait pas de quelle sorte de position
  il s'agissait.
- **#92** (sprints 27-29) : faits inventés résiduels, « 8.e5 meilleur coup », « Na6 sacrifie un
  pion », « trois pièces de plus » à +3 points, « Rd1# imparable » alors que 39.Qc2 pare,
  « tu prends tout sur la colonne d » hors variante [3 entrées sur 21].
  **Exemples antérieurs au sprint 50**, qui a depuis : écrit le matériel en toutes lettres
  (« trois pièces de plus » corrigé à la source), demandé de dire si un mat dépend d'une réponse
  adverse, fait écrire la variante et le piège par le code. Aucune nouvelle observation
  de #92 depuis : son état actuel est **inconnu**.

## 2. Ce que le LLM reçoit (bloc enrichi, `_build_enriched`, chess_router.py:1003)

Pour chaque position critique :

```
Position i (<sorte>) — coup N :
  joué <coup>, perte X pts de % de gain (a % → b %)        ← AUCUN fait sur le coup joué
  meilleur <coup>, ligne : <PV>
  faits : <faits de la PV du meilleur coup>               ← _move_facts(fen_before, pv_san)
  étiquettes, pièces (fen_before), matériel (fen_before), attaquées (fen_before),
  structure, évaluation, motifs
  [e]   erreur adverse <coup> : perte, meilleur             ← AUCUN fait sur ce coup adverse
  [a/b] suite du meilleur coup, faits + fin
        suite du coup joué, faits + fin                     ← seuls cas où le coup joué a ses faits
  [c/e] variante : <ligne d'avantage clair = PV du meilleur coup>, faits
  [d hors piège] lignes explosives (_explosive_lines)
```

Puis la consigne, puis **le message original de Nico, PGN complet compris**
(`return "\n".join(parts) + f"\n\n{message}"`, chess_router.py:1190).

Les faits d'un coup (`_move_fact_items`, chess_router.py:259) : roque, `prend <pièce>` /
`reprend`, promotion, mat / échec, `attaque <pièces>`, `décloue <pièces>`. Calcul pur
(python-chess), sans moteur.

### Couverture du coup joué, par sorte

| Sorte | Coup joué = meilleur ? | Faits du coup joué reçus ? |
|-------|------------------------|-----------------------------|
| a / b (erreur) | non | **oui** (`suite du coup joué`, `forcing_line` depuis `p.uci`) |
| c (coup unique trouvé) | oui (`quality == "best"`) | oui, indirectement (la PV du meilleur coup commence par lui) |
| d (occasion explosive) | pas forcément (perte < 10) | **non** |
| e (tournant) | pas forcément (perte < 10) ; `line_san` = PV du **meilleur** coup (`_evidence`) | **non**, sauf si joué = meilleur |
| réflexion longue (sprint 51) | pas forcément | **non** |

Coups cités ailleurs sans faits :
- **coup adverse fautif** de la sorte e (« erreur adverse X : perte… ») ;
- **coups du déroulé** (`story_line` : « Tournant(s) : coup 24.Qxf1+ (−30 pts) », « Pire coup »),
  sur lesquels le LLM bâtit le Bilan ;
- **tous les autres coups** du PGN, visibles en fin de message.

### Consignes existantes qui touchent au sujet

« ne dis qu'une pièce est prise ou épargnée que si ces faits le montrent » ne vaut que pour les
deux suites comparées (sorte a/b) ; règle générale : « Utilise uniquement les coups et lignes
fournis ci-dessus ; n'invente aucun coup ni évaluation » et « Ne décris aucune attaque, défense,
menace ou colonne absente des lignes matériel / attaquées / structure / faits ». Le LLM est
donc prié de ne rien décrire sans fait… alors que, pour le coup joué en sorte d / e / réflexion
longue, il n'a aucun fait, seulement le PGN brut.

## 3. Diagnostic

1. **Cause plausible de #187** : le coup joué n'a de faits qu'en sorte a/b. Ailleurs, le LLM lit
   « joué 24.Qxf1+ » et devine l'échange depuis le PGN. Même si la position du cas d'origine
   était une a/b, `prend Nf1, échec` seul ne dit pas si la dame peut être reprise : la réponse
   adverse **réellement jouée** (« 24...Kh7 », sans reprise) est ce qui tranche, et elle n'est
   donnée nulle part hors suite forcée moteur.
2. Même trou pour le **coup adverse fautif** (sorte e) et pour les **coups du déroulé** cités
   dans le Bilan.
3. **#92** : exemples périmés (avant sprint 50) ; pas de constat actuel. Les causes listées sont
   pour la plupart traitées ; le trou du point 1 en est une source résiduelle probable
   (« Na6 sacrifie un pion », « tu prends tout sur la colonne d » portent sur des coups sans faits).

## 4. Pistes (à arbitrer)

- **Suite jouée** : pour chaque coup joué cité (positions d / e / c / réflexion longue, et a/b
  si utile), une ligne « suite jouée, faits : » = le coup joué + la réponse adverse **jouée
  dans la partie**, avec leurs faits (`_move_facts(fen_before, [san, réponse])`, sans moteur).
- **Coup adverse fautif (e)** : ses faits (depuis `prev.fen_before`).
- **Déroulé** : faits accolés aux coups cités (tournants, pire coup) dans la ligne donnée au LLM.
- **Consigne** : étendre « ne dis qu'une pièce est prise ou épargnée que si ces faits le
  montrent » à toutes les positions.
- Hors piste : retirer le PGN du message (le LLM s'en sert pour l'ouverture et le contexte ;
  risque de régression non mesuré).

## 5. Critère du run live

Sur une partie où Nico a joué une prise **sans reprise adverse** hors erreur (sorte d, e ou
réflexion longue), le texte du LLM ne parle pas d'échange ; le bloc enrichi (journal ou test)
montre la ligne « suite jouée » avec `prend X` et la réponse adverse. #92 : relevé des faits
inventés sur 2 parties, à comparer aux 3/21 d'avant.
