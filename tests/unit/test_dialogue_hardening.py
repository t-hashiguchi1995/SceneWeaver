import json
from types import SimpleNamespace

import httpx
import pytest

from creator_studio.adapters.llm import LLMResponseError, OpenAICompatibleProvider
from creator_studio.adapters.llm.stub import _normalize
from creator_studio.application.dialogue.validation import validate_candidate


@pytest.mark.parametrize("key", ["candidates", "items", "lines", "results", "data"])
def test_wrappers(monkeypatch, key):
    assert _normalize({key: [1]}, "array") == [1]
    llm, _ = provider(monkeypatch, [json.dumps({key: [1]})])
    assert llm.complete_json(system="", user="", schema_hint="array") == [1]


def test_shapes():
    assert _normalize([], "array") == []
    with pytest.raises(LLMResponseError):
        _normalize([], "object")
    with pytest.raises(LLMResponseError):
        _normalize({"items": "bad"}, "array")


def provider(monkeypatch, contents, **kwargs):
    requests = []
    client = httpx.Client

    def handle(request):
        requests.append(json.loads(request.content))
        value = contents[min(len(requests) - 1, len(contents) - 1)]
        if isinstance(value, int):
            return httpx.Response(value, text="upstream unavailable")
        return httpx.Response(200, json={"choices": [{"message": {"content": value}}]})

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: client(transport=httpx.MockTransport(handle), **kw)
    )
    return OpenAICompatibleProvider(
        base_url="https://example.test", api_key="secret", model="m", **kwargs
    ), requests


@pytest.mark.parametrize(
    "content", ['```json\n{"items": []}\n```', 'Here is JSON: {"items": []} done', "[]"]
)
def test_extraction(monkeypatch, content):
    llm, _ = provider(monkeypatch, [content])
    assert llm.complete_json(system="", user="", schema_hint="array") == []


@pytest.mark.parametrize("bad", ["invalid", '{"wrong": true}', 503])
def test_retry(monkeypatch, bad):
    llm, requests = provider(monkeypatch, [bad, '{"items": []}'])
    assert llm.complete_json(system="", user="request", schema_hint="array") == []
    assert len(requests) == 2
    assert (
        "Return ONLY valid JSON matching the requested shape."
        in requests[1]["messages"][1]["content"]
    )


def test_exhaustion(monkeypatch):
    llm, requests = provider(monkeypatch, ["x" * 900])
    with pytest.raises(LLMResponseError) as error:
        llm.complete_json(system="", user="")
    assert len(requests) == 3
    assert len(error.value.excerpt) == 500


def test_object_mismatch(monkeypatch):
    llm, requests = provider(monkeypatch, ["[]"], max_retries=0)
    with pytest.raises(LLMResponseError):
        llm.complete_json(system="", user="", schema_hint="object")
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (" ", ["empty_text"]),
        ("あいうえお", ["too_long"]),
        ("あ、い。う！？", ["too_long", "too_many_fragments"]),
        ("禁止", ["forbidden_pattern:禁止"]),
        ("あ…、い。", ["too_long"]),
        ("😀あ", []),
    ],
)
def test_validation(text, expected):
    persona = SimpleNamespace(max_chars=4, max_fragments=2, forbidden_patterns=["禁止"])
    assert validate_candidate(text, persona) == expected
