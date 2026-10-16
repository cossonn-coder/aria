# Sprint 23 — Tronçon 04 : réponse REASONING tronquée

Constat run live 03, scénario D : réponse coupée net (« cloches de V »,
2 558 car.). Cause : `agents/analyst_agent.py` appelle `llm_router.complete`
avec `max_tokens=800` ; l'AnalystAgent produit toutes les réponses
REASONING (URL_READ, WEB_SEARCH, images, analyse).

Arbitrage Nico (2026-10-16) : **800 → 1500, global**. Telegram découpe déjà
les messages > 4096 car. (`interfaces/telegram_interface.py`).

Fichiers : `agents/analyst_agent.py` (une ligne),
`tests/agents/test_analyst_messages_form.py` (test du budget).
Garde-fou prompt `tests/agents/test_analyst_prompt_guard.py` vert.

Re-live : rejouer C (`https://fr.wikipedia.org/wiki/Normandie`) puis D
(`oui`) ; succès = réponse D complète, non coupée en milieu de mot.
