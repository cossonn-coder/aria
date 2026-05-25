# tests/llm/test_llm_router_messages.py
#
# Garde-fous de la signature multi-messages du LLMRouter (sprint 16).
#
# Couvre :
#   - Préservation stricte de la forme legacy (prompt=str).
#   - Transmission as-is en OpenAI-compat de la forme messages=[...].
#   - Extraction des {role:system} vers le param Anthropic top-level.
#   - Absence de clé "system" Anthropic quand aucun {role:system}.
#   - Xor strict prompt vs messages (les deux, aucun).
#   - Validation _validate_messages : rôle, vide, content vide, clés manquantes.
#
# Convention test_negative_cache.py : pas d'__init__.py dans tests/llm/,
# imports absolus, monkeypatch sur httpx.post.

import httpx
import pytest

from llm.llm_role import LLMRole
from llm.llm_router import ROUTING_TABLE, LLMRouter, _SOUL


# ── Helpers ──────────────────────────────────────────────────────────────────

def _install_capturing_post(monkeypatch, captured: dict, *, anthropic_format: bool = False):
    """Patche httpx.post pour capturer le payload envoyé et retourner une
    réponse factice 200 valide selon le format provider (OpenAI/Anthropic)."""

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        body = (
            {"content": [{"text": "ok"}], "usage": {}}
            if anthropic_format
            else {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        )
        return httpx.Response(
            status_code=200,
            json=body,
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("httpx.post", fake_post)


@pytest.fixture
def force_anthropic_chain(monkeypatch):
    """Force LLMRole.CHAT à n'avoir qu'un provider Anthropic, pour pouvoir
    asserter la structure du payload Anthropic sans dépendre de l'ordre
    réel de la chaîne de fallback."""
    monkeypatch.setitem(
        ROUTING_TABLE,
        LLMRole.CHAT,
        [{
            "provider": "anthropic",
            "model": "claude-test",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: "fake-key",
        }],
    )


# ── 1. Forme legacy préservée ────────────────────────────────────────────────

def test_complete_legacy_unchanged(monkeypatch):
    """complete(prompt=...) doit construire le payload OpenAI historique
    [system(_SOUL), user(prompt)] sans aucune régression de format."""
    captured: dict = {}
    _install_capturing_post(monkeypatch, captured)

    router = LLMRouter()
    result = router.complete(prompt="hello", role=LLMRole.CHAT)

    assert result.content == "ok"
    msgs = captured["json"]["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert _SOUL in msgs[0]["content"], "_SOUL doit être injecté en forme legacy"
    assert msgs[1] == {"role": "user", "content": "hello"}


# ── 2. Forme messages transmise telle quelle (OpenAI-compat) ─────────────────

def test_complete_messages_transmits_as_is(monkeypatch):
    """complete(messages=[...]) transmet la liste telle quelle au provider
    OpenAI-compat sans injection de _SOUL."""
    captured: dict = {}
    _install_capturing_post(monkeypatch, captured)

    input_messages = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
        {"role": "user", "content": "C"},
    ]
    router = LLMRouter()
    result = router.complete(messages=input_messages, role=LLMRole.CHAT)

    assert result.content == "ok"
    assert captured["json"]["messages"] == input_messages, (
        "la liste messages doit être transmise telle quelle"
    )
    # Aucun fragment du soul prompt ne doit avoir été injecté.
    assert _SOUL not in str(captured["json"]), (
        "aucune partie de _SOUL ne doit apparaître dans le payload"
    )


# ── 3. Anthropic : extraction des system messages vers le param top-level ────

def test_complete_messages_anthropic_extracts_system(monkeypatch, force_anthropic_chain):
    """Sur Anthropic, plusieurs {role:system} doivent être concaténés en
    payload['system'] et retirés de payload['messages']."""
    captured: dict = {}
    _install_capturing_post(monkeypatch, captured, anthropic_format=True)

    input_messages = [
        {"role": "system", "content": "A"},
        {"role": "system", "content": "B"},
        {"role": "user", "content": "hi"},
    ]
    router = LLMRouter()
    result = router.complete(messages=input_messages, role=LLMRole.CHAT)

    assert result.content == "ok"
    assert captured["json"]["system"] == "A\n\nB"
    assert captured["json"]["messages"] == [{"role": "user", "content": "hi"}]


# ── 4. Anthropic : pas de clé "system" si aucun {role:system} ────────────────

def test_complete_anthropic_no_system_in_messages(monkeypatch, force_anthropic_chain):
    """Sans aucun {role:system}, la clé 'system' ne doit pas être présente
    dans le payload Anthropic (et non une chaîne vide)."""
    captured: dict = {}
    _install_capturing_post(monkeypatch, captured, anthropic_format=True)

    router = LLMRouter()
    result = router.complete(
        messages=[{"role": "user", "content": "hi"}],
        role=LLMRole.CHAT,
    )

    assert result.content == "ok"
    assert "system" not in captured["json"], (
        "la clé 'system' doit être absente quand aucun system message"
    )
    assert captured["json"]["messages"] == [{"role": "user", "content": "hi"}]


# ── 5. Xor : les deux interdits ──────────────────────────────────────────────

def test_complete_raises_if_both_prompt_and_messages():
    router = LLMRouter()
    with pytest.raises(ValueError, match="pas les deux"):
        router.complete(
            prompt="x",
            messages=[{"role": "user", "content": "y"}],
        )


# ── 6. Xor : aucun interdit ──────────────────────────────────────────────────

def test_complete_raises_if_neither():
    router = LLMRouter()
    with pytest.raises(ValueError, match="pas aucun"):
        router.complete()


# ── 7. Validation : rôle invalide ────────────────────────────────────────────

def test_complete_rejects_invalid_role():
    router = LLMRouter()
    with pytest.raises(ValueError, match=r"role.*tool"):
        router.complete(messages=[{"role": "tool", "content": "x"}])


# ── 8. Validation : liste vide ───────────────────────────────────────────────

def test_complete_rejects_empty_messages():
    router = LLMRouter()
    with pytest.raises(ValueError, match=r"vide|empty"):
        router.complete(messages=[])


# ── 9. Validation : content vide ou whitespace ───────────────────────────────

def test_complete_rejects_empty_content():
    router = LLMRouter()
    with pytest.raises(ValueError):
        router.complete(messages=[{"role": "user", "content": ""}])
    with pytest.raises(ValueError):
        router.complete(messages=[{"role": "user", "content": "   "}])


# ── 10. Validation : clés manquantes ─────────────────────────────────────────

def test_complete_rejects_missing_keys():
    router = LLMRouter()
    with pytest.raises(ValueError):
        router.complete(messages=[{"role": "user"}])
    with pytest.raises(ValueError):
        router.complete(messages=[{"content": "x"}])
