# test/cognition/test_planner_agent.py — version étendue

import json
from unittest.mock import MagicMock, call
from agents.planner_agent import PlannerAgent
from agents.base_agent import AgentContext
from intent.intent import Intent
from cognition.cognitive_trace import CognitiveTrace


def _make_ctx(message="test", result="analyse existante", intent_name="test intent"):
    intent = Intent(name=intent_name)
    ctx = AgentContext(
        message=message,
        intent=intent,
        memories={},
        session_memory={},
        trace=CognitiveTrace(),
        extra={},
    )
    ctx.result = result
    return ctx


def _make_llm(content: str):
    llm = MagicMock()
    llm.complete.return_value = MagicMock(content=content)
    return llm


# =====================================================
# PARSING — cas nominaux
# =====================================================

def test_parse_json_propre():
    agent = PlannerAgent()
    result = agent._parse_response(
        '{"response": "Voici les étapes.", "next_action": "Faire X"}'
    )
    assert result["response"] == "Voici les étapes."
    assert result["next_action"] == "Faire X"


def test_parse_json_avec_backticks():
    agent = PlannerAgent()
    result = agent._parse_response(
        '```json\n{"response": "Réponse.", "next_action": "Action."}\n```'
    )
    assert result["response"] == "Réponse."
    assert result["next_action"] == "Action."


def test_parse_next_action_null():
    agent = PlannerAgent()
    result = agent._parse_response(
        '{"response": "Rien à faire.", "next_action": null}'
    )
    assert result["next_action"] is None


def test_parse_fallback_si_json_invalide():
    agent = PlannerAgent()
    result = agent._parse_response("texte libre sans JSON")
    assert result["response"] == "texte libre sans JSON"
    assert result["next_action"] is None


# =====================================================
# PARSING — cas limites réels (ce que le LLM produit)
# =====================================================

def test_parse_next_action_chaine_vide():
    """LLM retourne "" au lieu de null — doit être traité comme None."""
    agent = PlannerAgent()
    result = agent._parse_response(
        '{"response": "Ok.", "next_action": ""}'
    )
    assert result["next_action"] is None


def test_parse_next_action_chaine_null():
    """LLM retourne la string 'null' au lieu de JSON null."""
    agent = PlannerAgent()
    result = agent._parse_response(
        '{"response": "Ok.", "next_action": "null"}'
    )
    # "null" string != None — comportement à définir
    # actuellement retourné tel quel, ce test documente ce comportement
    assert result["next_action"] == "null"


def test_parse_response_field_absent():
    """LLM omet le champ response."""
    agent = PlannerAgent()
    result = agent._parse_response('{"next_action": "Faire X"}')
    assert result["response"] == ""
    assert result["next_action"] == "Faire X"


def test_parse_json_avec_espaces_et_newlines():
    """LLM ajoute des sauts de ligne autour du JSON."""
    agent = PlannerAgent()
    result = agent._parse_response(
        '\n\n{"response": "Ok.", "next_action": null}\n\n'
    )
    assert result["response"] == "Ok."


def test_parse_response_vide():
    """LLM retourne une chaîne vide — ne doit pas crasher."""
    agent = PlannerAgent()
    result = agent._parse_response("")
    assert isinstance(result["response"], str)
    assert result["next_action"] is None


# =====================================================
# PROMPT — vérification que le contexte est injecté
# =====================================================

def test_prompt_contient_message():
    agent = PlannerAgent()
    ctx = _make_ctx(message="construire une maison", result="analyse ici")
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    agent.run(ctx, llm)

    prompt_used = llm.complete.call_args[0][0]
    assert "construire une maison" in prompt_used


def test_prompt_contient_intent_name():
    agent = PlannerAgent()
    ctx = _make_ctx(intent_name="projet maison")
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    agent.run(ctx, llm)

    prompt_used = llm.complete.call_args[0][0]
    assert "projet maison" in prompt_used


def test_prompt_contient_analyse():
    agent = PlannerAgent()
    ctx = _make_ctx(result="résultat analyse upstream")
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    agent.run(ctx, llm)

    prompt_used = llm.complete.call_args[0][0]
    assert "résultat analyse upstream" in prompt_used


def test_prompt_fallback_si_result_none():
    """Si ctx.result est None, le prompt doit contenir le fallback."""
    agent = PlannerAgent()
    ctx = _make_ctx()
    ctx.result = None
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    agent.run(ctx, llm)

    prompt_used = llm.complete.call_args[0][0]
    assert "Aucune analyse disponible" in prompt_used


# =====================================================
# COMPORTEMENT AGENT
# =====================================================

def test_result_contient_seulement_response():
    agent = PlannerAgent()
    ctx = _make_ctx()
    llm = _make_llm('{"response": "Réponse propre.", "next_action": "Prochaine étape."}')

    ctx = agent.run(ctx, llm)

    assert ctx.result == "Réponse propre."
    assert "next_action" not in ctx.result
    assert "NEXT_ACTION" not in ctx.result


def test_next_action_sur_intent():
    agent = PlannerAgent()
    ctx = _make_ctx()
    llm = _make_llm('{"response": "Ok.", "next_action": "Faire Y"}')

    ctx = agent.run(ctx, llm)

    assert ctx.intent.next_action == "Faire Y"


def test_next_action_null_ne_modifie_pas_intent():
    agent = PlannerAgent()
    ctx = _make_ctx()
    ctx.intent.next_action = "action existante"
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    ctx = agent.run(ctx, llm)

    assert ctx.intent.next_action == "action existante"


def test_intent_none_retourne_ctx_intact():
    agent = PlannerAgent()
    ctx = _make_ctx()
    ctx.intent = None
    ctx.result = "résultat initial"
    llm = _make_llm('{"response": "Ne devrait pas être appelé.", "next_action": null}')

    ctx = agent.run(ctx, llm)

    assert ctx.result == "résultat initial"
    llm.complete.assert_not_called()


def test_llm_appele_une_seule_fois():
    agent = PlannerAgent()
    ctx = _make_ctx()
    llm = _make_llm('{"response": "Ok.", "next_action": null}')

    agent.run(ctx, llm)

    assert llm.complete.call_count == 1