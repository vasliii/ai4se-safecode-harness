"""Deterministic mock LLM backend for tests and demos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from safecode.llm.backend import LLMBackend
from safecode.models import ContextPayload


@dataclass(frozen=True, slots=True)
class Rule:
    """Rule-based mock response mapping."""

    predicate: Callable[[ContextPayload], bool]
    action: dict[str, Any]


class MockLLM(LLMBackend):
    """Return deterministic JSON actions without network access."""

    def __init__(
        self,
        actions: list[dict[str, Any]] | None = None,
        rules: list[Rule] | None = None,
    ) -> None:
        self.actions = list(actions) if actions is not None else None
        self.rules = list(rules) if rules is not None else None
        self._action_index = 0

    def query(self, context: ContextPayload) -> str:
        """Return the next scripted action or the first matching rule action."""
        if self.actions is not None:
            return self._query_scripted()
        if self.rules is not None:
            return self._query_rules(context)
        return self._finish_response()

    def _query_scripted(self) -> str:
        if self.actions is None or self._action_index >= len(self.actions):
            return self._finish_response()

        action = self.actions[self._action_index]
        self._action_index += 1
        return self._serialize(action)

    def _query_rules(self, context: ContextPayload) -> str:
        if self.rules is None:
            return self._finish_response()

        for rule in self.rules:
            try:
                matched = rule.predicate(context)
            except Exception:
                continue
            if matched:
                return self._serialize(rule.action)
        return self._finish_response()

    def _finish_response(self) -> str:
        return self._serialize({"tool": "finish", "params": {"summary": "MockLLM finished."}})

    def _serialize(self, action: dict[str, Any]) -> str:
        return json.dumps(action, ensure_ascii=False)
