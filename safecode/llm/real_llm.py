"""OpenAI-compatible real LLM backend."""

from __future__ import annotations

import json
from typing import Any

import httpx

from safecode.auth import CredentialManager
from safecode.llm.backend import LLMBackend, LLMError, LLMTimeoutError
from safecode.models import ContextPayload, RuntimeConfig


class RealLLM(LLMBackend):
    """Call a real OpenAI-compatible chat completions API."""

    def __init__(self, config: RuntimeConfig, credential_manager: CredentialManager) -> None:
        self.config = config
        self.credential_manager = credential_manager

    def query(self, context: ContextPayload) -> str:
        """Send context to the configured LLM and return the raw response text."""
        messages = self._build_messages(context)
        return self._call_api(messages)

    def _build_messages(self, context: ContextPayload) -> list[dict[str, str]]:
        """Build OpenAI-compatible chat messages from a ContextPayload."""
        payload = context.to_dict()
        system_prompt = str(payload.pop("system_prompt"))
        user_content = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _call_api(self, messages: list[dict[str, str]]) -> str:
        """Call the chat completions API and extract the first message content."""
        api_key = self.credential_manager.get_api_key()
        if not api_key:
            raise LLMError("API key not configured")

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        try:
            response = httpx.post(url, headers=headers, json=body, timeout=60)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMError(str(exc)) from exc

        if response.status_code >= 400:
            raise LLMError(f"HTTP error {response.status_code}: {self._response_text(response)}")

        data = self._parse_response(response)
        if "error" in data:
            raise LLMError(f"API error: {self._error_message(data['error'])}")

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("API response missing choices[0].message.content") from exc

        if not content:
            raise LLMError("API response content is empty")
        return str(content)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("API response is not valid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("API response must be a JSON object")
        return data

    def _response_text(self, response: httpx.Response) -> str:
        try:
            return response.text
        except Exception:
            return "<unavailable>"

    def _error_message(self, error: Any) -> str:
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        return str(error)
