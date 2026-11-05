# Sprint 50, tronçon 03 — run live (Nico)

## Préparation
`sudo systemctl restart aria.service`

## À envoyer
Une ou deux **vraies parties jamais envoyées**, idéalement une partie avec une erreur nette. Pas de fichier de parties pour ce run : les doublons sont refusés et une partie de test ajouterait une fiche à la progression.

## À vérifier sur Telegram
1. Le déroulé apparaît au-dessus du bilan, et ses chiffres concordent avec la courbe.
2. Le bilan cite une idée d'ouverture ou de position, sans cause absente du déroulé ni mat présenté comme acquis.
3. Le matériel annoncé est juste (pas de « pion de plus » pour une tour contre un cavalier), et une chute proche de la plus forte est citée dans le déroulé.
4. Les erreurs jouées vont du rose pâle au noir selon leur gravité, les autres coups joués restent bleus.
5. Un piège est en cyan avec sa ligne « Piège » conditionnelle ; si la partie n'en contient pas, le noter comme non observé.
6. Une variante à mat va jusqu'au mat ; si la partie n'en contient pas, le noter comme non observé.
7. À l'échiquier, la stratégie est blanche.
8. Sur une erreur, la légende montre « Meilleur coup » et « Ton coup » avec leur fin, puis un « Pourquoi » juste au regard de ces deux suites, sans « Plan ».
9. La courbe montre des points reliés.
10. À l'échiquier : flèche d'erreur lisible (case « Erreurs »), « Meilleur coup » coché par défaut, bouton + sur téléphone entre le menu et le retournement.

## À vérifier dans les journaux
`sudo journalctl -u aria --since today -o cat | grep -E "a répondu"`

Comparer `in=` au repère ~6 700 tokens par partie [n=1].

## Critère de succès
Points 1 à 4 et 7 à 10 observés, 5 et 6 observés ou notés non observés.
