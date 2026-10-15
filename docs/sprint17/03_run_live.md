# Sprint 17 — tronçon 03 : run live (Nico)

Exécuté par Nico, pas par un sous-agent. Prérequis : tronçons 01 et 02
commités, pytest vert.

## Étape 0 — remise à zéro de la mémoire de prod (décision Q5)

Nico a validé le 2026-10-15 : rien d'important dans le palace, on repart
d'une mémoire vide (supprime les 286 souvenirs factices écrits par les
tests et les intents créés par les tests). On **archive** plutôt que
supprimer : réversible.

```bash
sudo systemctl stop aria.service
TS=$(date +%Y%m%dT%H%M%S)
mv ~/.mempalace/palace ~/.mempalace/palace.pre-sprint17-$TS
mkdir ~/.mempalace/palace
# garder le choix d'embedder (mpnet multilingue), sinon retour à MiniLM (bug #18)
cp ~/.mempalace/palace.pre-sprint17-$TS/.mempalace-embedder.json \
   ~/.mempalace/palace.pre-sprint17-$TS/.embedder-migration-marker \
   ~/.mempalace/palace/
mv ~/.aria/intents.json ~/.aria/intents.json.pre-sprint17-$TS
sudo systemctl start aria.service
```

Retour arrière : `stop`, remettre les deux dossiers/fichiers archivés, `start`.

## Étape 1 — conversation de test

Dans un terminal : `sudo journalctl -u aria -f -o cat`

Messages Telegram à envoyer, dans l'ordre, sans re-citer les échanges
précédents :

1. « Je prévois de planter des tomates cerises sur mon balcon orienté est. »
2. « Combien de pieds tu me conseilles pour la surface ? »
3. « Et quel engrais pour elles ? »
4. « Tu me disais quoi déjà sur l'orientation ? »

## Critère de succès (clôture fil rouge #34)

- Réponses 2, 3, 4 : Aria comprend implicitement « tomates cerises »,
  « balcon », « est », sans que ce soit répété. La 4 reprend l'orientation
  est évoquée au message 1.
- journalctl, à chaque message : `conversation_history loaded key=<chat_id> messages=N`
  avec N = 0, 2, 4, 6, et `conversation_write OK`.
- Aucun `Traceback`, `RuntimeError`, `ValueError`.
- Latence : noter si la réponse paraît nettement plus lente qu'avant
  (2 embeddings CPU de plus par message, ~+220 ms estimé [bench sprint 6]).

Échec = Aria « redémarre » à un des messages 2-4 → retour à `/conception`
avec les logs.

## Après succès

Clôture (avec Claude Code) : `00_etat.md` à jour, kickoff sprint 18 avec
tableau de dettes (#34 fermée, nouvelles dettes listées dans `00_etat.md`),
merge sur `main`, tag `sprint-17` sur le commit documentaire, push **sur
OK explicite de Nico**.
