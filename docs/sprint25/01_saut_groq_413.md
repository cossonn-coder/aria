# Sprint 25 — Tronçon 01 : 413 Groq → sauter les autres Groq + log du corps

Lire d'abord : `CLAUDE.md`, `docs/sprint25/00_etat.md`,
`docs/sprint25/audit_groq_413.md` (§2 sonde, §4 coût).

## Objectif

Un 413 Groq (`Request too large … ITPM: Limit 7000, Requested N`) est
déterministe pour une requête : `groq_2` et `groq_3` (même modèle, même
palier) échouent forcément pareil. Après un 413 sur une entrée `groq*`,
`LLMRouter.complete()` saute les autres entrées `groq*` **de cette requête**
et passe au fournisseur suivant (DeepSeek). Et le log de fallback montre le
corps de la réponse HTTP, pour lire limite et taille demandée dans journalctl.

## Fichier à toucher

`llm/llm_router.py`, méthode `LLMRouter.complete()` (boucle l.209-242 au
commit `5fc1bdd`) :

```python
            try:
                return self._call(**call_kwargs)
            except Exception as e:
                log.error("[LLM FALLBACK] %s failed: %s", provider, e)
                if (isinstance(e, httpx.HTTPStatusError)
                        and e.response.status_code == 429):
                    self._mark_rate_limited(provider)
                last_error = e
                if i < len(chain) - 1:
                    time.sleep(1)
```

## Comportement attendu

1. 413 sur un fournisseur dont le nom commence par `groq` → les entrées
   suivantes dont le nom commence par `groq` sont sautées pour cette requête
   (log `info` court, ex. `[LLM] provider groq_2 skipped (413 sur groq)`).
   Mécanisme libre (variable locale à `complete()`), **pas** de cache
   négatif : le message suivant retente Groq normalement.
2. Log `[LLM FALLBACK]` : si l'exception est un `httpx.HTTPStatusError`,
   ajouter `e.response.text[:200]` au message. Les autres exceptions restent
   logguées comme aujourd'hui.
3. Rien d'autre ne change : 429 et cache négatif, réponses vides, `sleep(1)`.

## Test à ajouter (cas nominal)

Dans `tests/llm/` (nouveau fichier ou à côté de `test_negative_cache.py`,
dont reprendre les helpers `_make_http_error` / fixture `no_sleep`) :
`_call` patché lève un 413 pour `groq`, réussit pour les autres ; on vérifie
que `_call` n'est appelé qu'une fois pour un `groq*`, que la réponse vient de
`deepseek`, et que `router._negative_cache` reste vide.

## Hors scope (ne pas faire)

- Plafond de tokens sur l'historique (piste B écartée par Nico).
- `max_history_turns` / dette #37, `sleep(1)`, ordre de la chaîne.
- Traiter d'autres codes (400, 5xx) comme le 413.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` mis à jour (tronçon ✅ +
§REPRISE).
