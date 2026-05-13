**1. CRLF parasite — cause non investiguée**
Risque concret : diffs pollués, conflits Git artificiels, scripts shell cassés et exécutions CI imprévisibles selon l’OS. À terme, cela rend l’historique illisible et empêche de distinguer un vrai changement fonctionnel d’un bruit d’encodage. Devient bloquant sous 1–2 mois dès que plusieurs machines ou merges parallèles interviennent. Coût de fix ≈ 2–4 h (audit `.gitattributes`, config autocrlf, normalisation repo). **Priorité : critique**, car corruption silencieuse du workflow.

**2. Pas de hook pre-commit pytest**
Risque concret : régression fonctionnelle intégrée au repo sans alerte immédiate, accumulation de dette technique invisible et perte de confiance dans la branche principale. L’équipe découvre les cassures trop tard, souvent lors d’un refactor non lié. Bloquant en 1 mois typiquement après quelques cycles de dev actifs. Coût de fix ≈ 1–2 h (hook local + doc usage). **Priorité : critique**, car protège directement l’intégrité logicielle.

**3. Livrables doc non commités à clôture de tour**
Risque concret : perte d’état décisionnel, divergence entre code réel et contexte projet, impossibilité de reconstruire l’historique cognitif d’ARIA. Cela crée une dette de compréhension plus dangereuse que la dette technique. Devient bloquant en 2–3 mois lorsque la mémoire projet devient incohérente. Coût de fix ≈ 2 h (checklist fin de tour + template PR). **Priorité : important**, car impact systémique mais non immédiat.

**4. Claude Code ignore parfois la numérotation des briefs**
Risque concret : désynchronisation cognitive entre humain et agent, impossibilité d’auditer les décisions et perte de traçabilité des tâches. La charge mentale repose alors entièrement sur Nico, ce qui ne scale pas. Devient bloquant en 1–2 mois quand le volume de briefs augmente. Coût de fix ≈ 3–5 h (contrainte protocolaire + validation automatique du numéro). **Priorité : important**, car dette organisationnelle croissante.

**5. Shebangs `bin/*.py` en chemin absolu venv**
Risque concret : scripts inutilisables sur autre machine, CI, clone frais ou rebuild d’environnement. Toute reproduction du projet échoue hors machine d’origine. Bloquant immédiatement lors du premier onboarding ou rebuild majeur (<1 mois). Coût de fix ≈ 1 h (`#!/usr/bin/env python3` + regen scripts). **Priorité : critique**, car casse la portabilité fondamentale.

**6. PATH `~/.local/bin` en double**
Risque concret : faible mais réel — résolution ambiguë d’exécutables, comportement shell non déterministe et debugging inutile. Impact surtout cumulatif avec d’autres anomalies d’environnement. Devient pénible plutôt que bloquant (>6 mois). Coût de fix ≈ 10 min (cleanup config shell). **Priorité : nice-to-have**, dette d’hygiène.

**7. `origin/HEAD` non synchronisée local**
Risque concret : checkout ou scripts Git automatiques pointant vers mauvaise branche par défaut, erreurs subtiles lors de clones ou automatisations. Peu visible mais source classique de confusion future. Bloquant seulement lors d’automatisation Git avancée (3–6 mois). Coût de fix ≈ 2 min (`git remote set-head origin -a`). **Priorité : important**, correction triviale à forte valeur préventive.

**8. Store ChromaDB legacy versionné dans le repo**
Risque concret : explosion du repo, conflits binaires permanents, commits inutiles à chaque ouverture et impossibilité de collaboration propre. Le dépôt devient lent, fragile et impossible à maintenir. Bloquant sous 1 mois si usage fréquent du store. Coût de fix ≈ 3–6 h (ignore Git + migration stockage + cleanup historique si nécessaire). **Priorité : critique**, car violation directe des bonnes pratiques VCS.

**9. Dépendance `psutil` non documentée**
Risque concret : environnement non reproductible, crash au déploiement ou sur nouvelle machine sans cause apparente. Dette typique qui apparaît uniquement lors d’un rebuild urgent. Bloquant au premier reinstall complet (<1 mois). Coût de fix ≈ 30 min (audit imports + ajout deps). **Priorité : critique**, car impact direct sur la reproductibilité.

**10. Absence de fichier de dépendances versionné**
Risque concret : impossibilité de reconstruire ARIA de manière déterministe, dérive progressive du venv et bugs fantômes dépendant des versions locales. À moyen terme, le projet devient non portable et non archivable. Bloquant en 1–2 mois avec évolution continue. Coût de fix ≈ 1–2 h (`pip freeze` contrôlé ou migration `pyproject.toml`). **Priorité : critique**, fondation de tout projet Python.

---

### Ordre recommandé — Sprint 7

1. **(10) Fichier de dépendances versionné** — base de reproductibilité globale, condition préalable à toute stabilisation.
2. **(9) Dépendances non documentées** — corrige immédiatement l’état réel du projet avant divergence.
3. **(5) Shebangs non portables** — restaure exécution cross-machine.
4. **(2) Hook pre-commit pytest** — verrouille la qualité après stabilisation environnementale.
5. **(8) ChromaDB versionné** — empêche la dégradation rapide du repo.
6. **(1) CRLF parasite** — nettoyage structurel une fois les fondations sécurisées.
7. **(7) origin/HEAD** — quick win préventif.
8. **(3) Discipline commit documentation** — stabilise la mémoire projet.
9. **(4) Numérotation des briefs Claude** — amélioration organisationnelle après sécurisation technique.
10. **(6) PATH dupliqué** — hygiène finale sans impact critique.
