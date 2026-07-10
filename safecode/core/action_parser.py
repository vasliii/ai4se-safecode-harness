"""Parse raw LLM responses into structured actions."""

from __future__ import annotations

import json
import re
from typing import Any, TypeAlias

from safecode.core.exceptions import InvalidActionError
from safecode.models import ParsedAction

ParamSpec: TypeAlias = tuple[type, bool]

TOOL_SCHEMAS: dict[str, dict[str, ParamSpec]] = {
    "list_files": {
        "path": (str, True),
        "recursive": (bool, False),
    },
    "read_file": {
        "path": (str, True),
        "start_line": (int, False),
        "end_line": (int, False),
    },
    "search_content": {
        "pattern": (str, True),
        "path": (str, False),
        "file_pattern": (str, False),
    },
    "write_file": {
        "path": (str, True),
        "content": (str, True),
    },
    "edit_file": {
        "path": (str, True),
        "old_text": (str, True),
        "new_text": (str, True),
    },
    "run_tests": {
        "args": (str, False),
    },
    "run_shell": {
        "command": (str, True),
    },
    "finish": {
        "summary": (str, False),
    },
}

_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class ActionParser:
    """Parse and validate JSON actions returned by an LLM backend."""

    def parse(self, response: str) -> ParsedAction:
        cleaned_response = self._strip_markdown_code_block(response)
        payload = self._load_json(cleaned_response)

        if not isinstance(payload, dict):
            raise InvalidActionError("missing_fields", "Action payload must be a JSON object.")

        if "tool" not in payload or "params" not in payload or not isinstance(payload["params"], dict):
            raise InvalidActionError("missing_fields", "Action payload must contain tool and params fields.")

        tool = payload["tool"]
        params = payload["params"]

        if tool not in TOOL_SCHEMAS:
            raise InvalidActionError("unknown_tool", f"Unknown tool: {tool}")

        if not self._valid_params(params, TOOL_SCHEMAS[tool]):
            raise InvalidActionError("invalid_params", f"Invalid params for tool: {tool}")

        return ParsedAction(
            tool=tool,
            params=dict(params),
            thought_summary=payload.get("thought_summary"),
        )

    def _load_json(self, response: str) -> Any:
        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise InvalidActionError("invalid_json", "LLM response is not valid JSON.") from exc

    def _strip_markdown_code_block(self, response: str) -> str:
        match = _CODE_BLOCK_RE.search(response.strip())
        if match:
            return match.group(1).strip()
        return response.strip()

    def _valid_params(self, params: dict[str, Any], schema: dict[str, ParamSpec]) -> bool:
        for name, (expected_type, required) in schema.items():
            if name not in params:
                if required:
                    return False
                continue
            if not self._matches_type(params[name], expected_type):
                return False
        return True

    def _matches_type(self, value: Any, expected_type: type) -> bool:
        if expected_type is int:
            return isinstance(value, int) and not isinstance(value, bool)
        return isinstance(value, expected_type)