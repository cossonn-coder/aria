# tests/llm/test_usage_log.py
#
# Journal de la consommation : les tokens de chaque appel, formats OpenAI-compatible
# et Anthropic.

from llm.llm_router import _usage_text


def test_usage_text_openai_compatible():
    usage = {"prompt_tokens": 1200, "completion_tokens": 300, "prompt_cache_hit_tokens": 1000}
    assert _usage_text(usage) == "in=1200 out=300 cache=1000"


def test_usage_text_anthropic():
    usage = {"input_tokens": 50, "output_tokens": 20, "cache_read_input_tokens": 7}
    assert _usage_text(usage) == "in=50 out=20 cache=7"


def test_usage_text_missing():
    assert _usage_text(None) == "in=? out=? cache=0"
