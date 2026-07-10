import pytest

from safecode.llm import LLMBackend, LLMError, LLMTimeoutError
from safecode.models import ContextPayload


class EchoLLM(LLMBackend):
    def query(self, context: ContextPayload) -> str:
        return f"step={context.step_id}"


def make_context() -> ContextPayload:
    return ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=3,
        blocked_count=0,
        remaining_steps=7,
    )


def test_llm_backend_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        LLMBackend()


def test_concrete_backend_can_return_string() -> None:
    backend = EchoLLM()

    response = backend.query(make_context())

    assert isinstance(backend, LLMBackend)
    assert response == "step=3"
    assert isinstance(response, str)


def test_llm_exceptions_are_exported() -> None:
    assert issubclass(LLMError, Exception)
    assert issubclass(LLMTimeoutError, LLMError)