"""Deterministic MockLLM action scripts for built-in demos."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


FIX_BUG_OLD_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a - b'''

FIX_BUG_NEW_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a + b'''

COMPLETE_FUNCTION_OLD_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    pass'''

COMPLETE_FUNCTION_NEW_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a + b'''


DEMO_MOCK_ACTIONS: dict[str, list[dict[str, Any]]] = {
    "guardrail_block": [
        {"tool": "run_shell", "params": {"command": "rm -rf /"}},
        {"tool": "read_file", "params": {"path": ".env"}},
        {"tool": "read_file", "params": {"path": "../etc/passwd"}},
    ],
    "fix_bug": [
        {"tool": "run_tests", "params": {}},
        {
            "tool": "edit_file",
            "params": {
                "path": "src/calculator.py",
                "old_text": FIX_BUG_OLD_ADD,
                "new_text": FIX_BUG_NEW_ADD,
            },
        },
        {"tool": "run_tests", "params": {}},
        {"tool": "finish", "params": {"summary": "Fixed calculator.add."}},
    ],
    "complete_function": [
        {"tool": "list_files", "params": {"path": "."}},
        {"tool": "read_file", "params": {"path": "src/calculator.py"}},
        {
            "tool": "edit_file",
            "params": {
                "path": "src/calculator.py",
                "old_text": COMPLETE_FUNCTION_OLD_ADD,
                "new_text": COMPLETE_FUNCTION_NEW_ADD,
            },
        },
        {"tool": "run_tests", "params": {}},
        {"tool": "finish", "params": {"summary": "Implemented calculator.add."}},
    ],
}


def get_demo_mock_actions(demo_id: str) -> list[dict[str, Any]] | None:
    """Return a fresh scripted action list for a built-in demo id."""
    actions = DEMO_MOCK_ACTIONS.get(demo_id)
    return deepcopy(actions) if actions is not None else None
