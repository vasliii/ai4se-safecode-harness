"""Tests for LLM backend factory selection."""

from __future__ import annotations

import pytest

from safecode.auth import CredentialManager
from safecode.llm import LLMBackend, MockLLM, RealLLM, Rule, create_llm_backend
from safecode.models import ContextPayload, RuntimeConfig


class FakeCredentialManager(CredentialManager):
    def get_api_key(self) -> str | None:
        return "test-key"


def make_context() -> ContextPayload:
    return ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=0,
        blocked_count=0,
        remaining_steps=1,
    )


def test_create_real_llm_when_mock_false():
    config = RuntimeConfig()
    credentials = FakeCredentialManager()

    backend = create_llm_backend(config, credentials, mock=False)

    assert isinstance(backend, RealLLM)
    assert isinstance(backend, LLMBackend)
    assert backend.config is config
    assert backend.credential_manager is credentials


def test_create_mock_llm_with_actions():
    actions = [{"tool": "finish", "params": {"summary": "done"}}]

    backend = create_llm_backend(RuntimeConfig(), FakeCredentialManager(), mock=True, mock_actions=actions)

    assert isinstance(backend, MockLLM)
    assert isinstance(backend, LLMBackend)
    assert backend.actions == actions


def test_create_mock_llm_with_rules():
    rules = [Rule(predicate=lambda ctx: ctx.step_id == 0, action={"tool": "run_tests", "params": {}})]

    backend = create_llm_backend(RuntimeConfig(), FakeCredentialManager(), mock=True, mock_rules=rules)

    assert isinstance(backend, MockLLM)
    assert isinstance(backend, LLMBackend)
    assert backend.rules == rules
    assert "run_tests" in backend.query(make_context())


def test_create_mock_llm_without_actions_or_rules_returns_empty_scripted_mock():
    backend = create_llm_backend(RuntimeConfig(), FakeCredentialManager(), mock=True)

    assert isinstance(backend, MockLLM)
    assert isinstance(backend, LLMBackend)
    assert backend.actions == []
    assert "finish" in backend.query(make_context())


def test_mock_actions_and_rules_are_mutually_exclusive():
    rules = [Rule(predicate=lambda ctx: True, action={"tool": "finish", "params": {}})]

    with pytest.raises(ValueError, match="mock_actions and mock_rules"):
        create_llm_backend(
            RuntimeConfig(),
            FakeCredentialManager(),
            mock=True,
            mock_actions=[],
            mock_rules=rules,
        )


def test_create_llm_backend_is_importable_from_package():
    from safecode.llm import create_llm_backend as imported

    assert imported is create_llm_backend
