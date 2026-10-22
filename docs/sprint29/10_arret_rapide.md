# Sprint 29 — Tronçon 10 : arrêt rapide du service

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_retours_run_live.md` §4.

## Constat
SIGTERM → PTB s'arrête aussitôt, puis la finalisation Python dure 9 s à > 90 s
[n=3] (thread principal en état D : relecture du swap, 3,8 Go de swap occupés) →
SIGKILL systemd. La quarantaine HNSW est indépendante (dette #105).

## Objectif
Après le retour de `telegram.start()` (`run_polling` rendu après arrêt propre de PTB),
sortir sans finalisation Python.

## Fichier
`bot.py`, `main()` : après `telegram.start()` : `log.info("ARIA arrêt")`,
`logging.shutdown()` (vide les handlers), puis `os._exit(0)`. Commentaire : pourquoi
(finalisation lente sous swap ; sqlite chromadb déjà validé à chaque écriture).

## Tests
Un test : `main` avec `AriaKernel` / `TelegramInterface` simulés et `os._exit`
monkeypatché → appelé avec 0 après `start()`.

## Hors-scope
Pas de modification de l'unit systemd, pas de flush HNSW (#105).

## Critère de fin
`pytest tests/ -q` vert ; à valider en live (tronçon 11) : `systemctl restart` < 10 s.
