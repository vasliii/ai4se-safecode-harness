"""Tests for the OpenAI-compatible RealLLM backend."""

from __future__ import annotations

import pytest
import httpx

from safecode.auth import CredentialManager
from safecode.llm import LLMError, LLMTimeoutError, RealLLM
from safecode.models import ContextPayload, FailedTest, RuntimeConfig, TestFeedback, ToolResult


class FakeCredentialManager(CredentialManager):
    def __init__(self, key: str | None) -> None:
        self.key = key

    def get_api_key(self) -> str | None:
        return self.key


def make_context() -> ContextPayload:
    return ContextPayload(
        system_prompt="System safety instructions.",
        task_description="Fix the parser bug.",
        step_id=2,
        blocked_count=1,
        remaining_steps=4,
        last_test_feedback=TestFeedback(
            exit_code=1,
            passed_count=3,
            failed_count=1,
            skipped_count=0,
            duration_ms=120,
            status="failed",
            failed_tests=[FailedTest(name="test_parser", assertion="expected token")],
            progress_summary="Same failure persists.",
            hint="Try a different approach.",
        ),
        last_tool_result=ToolResult(
            tool="run_tests",
            success=True,
            data={"exit_code": 1, "stdout": "FAILED test_parser"},
        ),
        workspace_tree="src/parser.py\ntests/test_parser.py",
        history_summary="step 1 action=run_tests",
    )


def make_llm(key: str | None = "test-api-key") -> RealLLM:
    config = RuntimeConfig(base_url="https://example.test/v1", model="test-model", temperature=0.2)
    return RealLLM(config, FakeCredentialManager(key))


def test_build_messages_contains_system_prompt_and_task_context():
    messages = make_llm()._build_messages(make_context())

    assert messages[0] == {"role": "system", "content": "System safety instructions."}
    assert messages[1]["role"] == "user"
    assert "Fix the parser bug." in messages[1]["content"]
    assert "step_id" in messages[1]["content"]


def test_build_messages_includes_feedback_and_tool_result_details():
    messages = make_llm()._build_messages(make_context())
    user_content = messages[1]["content"]

    assert "failed_count" in user_content
    assert "test_parser" in user_content
    assert "run_tests" in user_content
    assert "FAILED test_parser" in user_content


def test_call_api_uses_correct_url_headers_and_body(monkeypatch):
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{\"tool\": \"finish\", \"params\": {}}"}}]},
        )

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)
    llm = make_llm()
    messages = llm._build_messages(make_context())

    result = llm._call_api(messages)

    assert result == '{"tool": "finish", "params": {}}'
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-api-key"
    assert captured["json"] == {
        "model": "test-model",
        "messages": messages,
        "temperature": 0.2,
    }
    assert captured["timeout"] == 60


def test_query_returns_choice_message_content(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(200, json={"choices": [{"message": {"content": "raw response"}}]})

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    assert make_llm().query(make_context()) == "raw response"


def test_missing_api_key_raises_llm_error():
    with pytest.raises(LLMError, match="API key not configured"):
        make_llm(key=None).query(make_context())


def test_http_error_raises_llm_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(500, json={"message": "server error"})

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    with pytest.raises(LLMError, match="500"):
        make_llm().query(make_context())


def test_api_error_response_raises_llm_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(200, json={"error": {"message": "bad request"}})

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    with pytest.raises(LLMError, match="bad request"):
        make_llm().query(make_context())


def test_timeout_raises_llm_timeout_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    with pytest.raises(LLMTimeoutError, match="timed out"):
        make_llm().query(make_context())


def test_network_error_raises_llm_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        raise httpx.NetworkError("network unavailable")

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    with pytest.raises(LLMError, match="network unavailable"):
        make_llm().query(make_context())


def test_empty_choices_raises_llm_error(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        return httpx.Response(200, json={"choices": []})

    monkeypatch.setattr("safecode.llm.real_llm.httpx.post", fake_post)

    with pytest.raises(LLMError, match="choices"):
        make_llm().query(make_context())
