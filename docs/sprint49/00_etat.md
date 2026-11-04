# Sprint 49 — état de conception (AggroChess et coups explosifs)

**Phase** : étude close sans code le 2026-11-04. Le sprint 49 reste à choisir.
**Sujet** : le moteur AggroChess (Rust, GPL-3.0) peut-il améliorer ou remplacer le calcul des coups explosifs (`chess_coach/explosive.py`) ?

## Décisions arrêtées

- AggroChess écarté, ni en remplacement de Stockfish ni en source de candidats : score biaisé, gain marginal (audit §2-3). Il sert seulement de témoin externe dans la mesure.
- Pas de fork : le but de Nico n'est pas d'utiliser le moteur mais de vérifier le détecteur.
- Objectif reformulé par Nico : s'assurer que les coups explosifs trouvent bien les idées de sacrifice, même s'il en est satisfait aujourd'hui. Question = rappel du détecteur.
- Clore sans code : le détecteur trouve les idées de sacrifice (audit §7).

## Questions ouvertes

Aucune. Clôture décidée par Nico, relance à Elo 1737 arrêtée sans résultat ; dettes #176 à #178.

## §REPRISE

Cette étude n'appelle aucune suite. Pour le sprint 49 : `/conception <sujet>`, ce fichier pouvant être remplacé.
