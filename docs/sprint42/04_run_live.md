# Sprint 42 — tronçon 04 : run live (exécuté par Nico)

Prérequis : tronçons 01-03 commités, `pytest tests/ -q` vert, puis
`sudo systemctl restart aria.service`.

## Préparation (orchestrateur, avant de rendre la main)

Créer dans `docs/sprint42/run_live/` les fichiers à envoyer, et `messages.txt` (une ligne
courte copiable par étape, cf. mémoire « parties run live en fichier ») :

- `notes.txt` : ~20 lignes de texte français ;
- `long.txt` : > 100 000 caractères (texte répété numéroté par paragraphe) ;
- `article.pdf` : PDF avec texte, 2 pages ;
- `scan.pdf` : PDF d'une page faite d'une image de texte (texte rendu en image par Pillow) ;
- `document.png` : la même image de texte ;
- `deux_parties.pgn` : 2 parties courtes (≈ 30 coups) avec en-têtes `[White "Nico"]` ;
- `archive.zip` : n'importe quel zip.

Journal à suivre : `sudo journalctl -u aria -f -o cat`.

## Étapes et critères

| # | Envoi sur Telegram | Attendu |
|---|---|---|
| 1 | `notes.txt` sans légende | résumé général ; journal `telegram_update … type=document`, `url_read OK` (ou équivalent fichier) |
| 2 | `article.pdf` légende « quelles sont les idées principales ? » | synthèse orientée par la question |
| 3 | `long.txt` sans légende, puis `lis la suite` | ARIA dit avoir lu une partie et propose la suite ; la suite porte sur la 2e tranche |
| 4 | `scan.pdf` sans légende | le texte de l'image est résumé (OCR) |
| 5 | `document.png` envoyé **en fichier** | traité comme une photo ; le texte est recopié après « Texte : » |
| 6 | une photo de ticket / écran prise au téléphone (envoi photo normal) | description + texte recopié |
| 7 | `deux_parties.pgn` | annonce « 2 parties trouvées… », puis une réponse groupée : diagrammes « Partie 1 — » / « Partie 2 — », deux titres de partie ; journal `chess_router multi games=2 ok=2` |
| 8 | `archive.zip` | « fichier illisible » en une phrase, pas de trace d'erreur |
| 9 | une question de suivi sur `article.pdf` | réponse depuis la synthèse (pas de relecture du fichier) |

Le cas « > 20 Mo » est couvert par les tests seuls (pas de fichier à envoyer).

## Critère de succès

Étapes 1-8 conformes, aucune trace `ERROR` dans le journal pendant le run.
