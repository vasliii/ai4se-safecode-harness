"""Factory for selecting SafeCode LLM backends."""

from __future__ import annotations

from typing import Optional

from safecode.auth import CredentialManager
from safecode.llm.backend import LLMBackend
from safecode.llm.mock_llm import MockLLM, Rule
from safecode.llm.real_llm import RealLLM
from safecode.models import RuntimeConfig


def create_llm_backend(
    config: RuntimeConfig,
    credential_manager: CredentialManager,
    mock: bool = False,
    mock_actions: Optional[list[dict]] = None,
    mock_rules: Optional[list[Rule]] = None,
) -> LLMBackend:
    """Create the configured real or mock LLM backend."""
    if mock_actions is not None and mock_rules is not None:
        raise ValueError("mock_actions and mock_rules cannot both be provided")

    if not mock:
        return RealLLM(config, credential_manager)

    if mock_rules is not None:
        return MockLLM(rules=mock_rules)

    return MockLLM(actions=mock_actions or [])
