# tests/agents/test_analyst_prompt_guard.py
#
# Garde-fou contre la régression du prompt AnalystAgent.
#
# Contexte :
#   commit e507606 — Fix #1 : suppression du verrouillage de domaine ("Réponds
#   UNIQUEMENT dans le domaine de l'intent actuel"). L'intent est désormais
#   présenté comme contexte mémoire, pas comme frontière cognitive.
#
#   commit 31c21a4 — regression : le refactor INGESTION a accidentellement réverté
#   le prompt vers l'ancienne version (DOMAINE ACTUEL / RÈGLES STRICTES).
#
#   commit 07522c8 — Fix #1 restauré.
#
# Ces tests détectent cette classe de régression sans dupliquer le prompt :
# ils lisent la constante PROMPT depuis le module.

from agents.analyst_agent import PROMPT


def test_domain_lock_instruction_absent():
    """Fix #1 — l'instruction de verrouillage de domaine ne doit plus exister."""
    prompt_lower = PROMPT.lower()
    assert "domaine actuel" not in prompt_lower, (
        "Régression Fix #1 : 'DOMAINE ACTUEL' est réapparu dans le prompt. "
        "Voir commit 31c21a4 (régression) et 07522c8 (fix)."
    )
    assert "uniquement dans le domaine" not in prompt_lower, (
        "Régression Fix #1 : 'uniquement dans le domaine' est réapparu dans le prompt. "
        "Voir commit 31c21a4 (régression) et 07522c8 (fix)."
    )


def test_open_scope_instruction_present():
    """Fix #1 — l'instruction de réponse sans restriction de domaine doit être présente."""
    assert "quel que soit le sujet" in PROMPT.lower(), (
        "Régression Fix #1 : la règle 'quel que soit le sujet' a disparu du prompt. "
        "Voir commit 07522c8."
    )
    assert "projet récent en mémoire" in PROMPT.lower(), (
        "Régression Fix #1 : 'projet récent en mémoire' a disparu du prompt — "
        "l'intent doit être présenté comme contexte mémoire, pas comme frontière. "
        "Voir commit 07522c8."
    )


def test_prompt_not_trivial():
    """Le prompt ne doit pas être vide ou tronqué."""
    assert len(PROMPT) > 200, (
        f"Le prompt est anormalement court ({len(PROMPT)} chars). "
        "Vérifier que la constante PROMPT est bien définie dans analyst_agent.py."
    )
