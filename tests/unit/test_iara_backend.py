from types import SimpleNamespace

import pytest

from agente_insider.errors import (
    AuthenticationFailure,
    ModelUnavailable,
    PolicyError,
    TransientModelError,
)
from agente_insider.llm.iara_backend import IaraBackend


class FakeCompletions:
    def __init__(self, response=None, error=None):
        self.response, self.error = response, error
        self.params = None

    def create(self, **kwargs):
        self.params = kwargs
        if self.error:
            raise self.error
        return self.response


def backend(response=None, error=None):
    response = response or SimpleNamespace(
        choices=[
            SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content='{"ok": true}'))
        ],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )
    completions = FakeCompletions(response, error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return IaraBackend(
        client, model="test-model", allowed_models=frozenset({"test-model"})
    ), completions


def invoke(gateway):
    return gateway.generate(stage="test", system="system", user="data", max_completion_tokens=700)


def test_corporate_call_shape_and_token_measurement_without_network():
    gateway, completions = backend()
    reply = invoke(gateway)
    assert reply.input_tokens == 11
    assert reply.output_tokens == 7
    assert completions.params["response_format"] == {"type": "json_object"}
    assert completions.params["enable_polling"] is True
    assert completions.params["max_tokens"] == 700
    assert completions.params["model"] == "test-model"


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, AuthenticationFailure),
        (403, AuthenticationFailure),
        (429, TransientModelError),
        (500, TransientModelError),
        (503, TransientModelError),
        (400, ModelUnavailable),
    ],
)
def test_gateway_error_taxonomy_sanitizes_messages(status, expected):
    error = RuntimeError("SENSITIVE-ORIGINAL-MESSAGE")
    error.status_code = status
    gateway, _ = backend(error=error)
    with pytest.raises(expected) as captured:
        invoke(gateway)
    assert "SENSITIVE-ORIGINAL-MESSAGE" not in str(captured.value)


@pytest.mark.parametrize("content,reason", [("", "stop"), (None, "stop"), ('{"x":', "length")])
def test_empty_and_truncated_completions_fail(content, reason):
    gateway, _ = backend(
        SimpleNamespace(
            choices=[
                SimpleNamespace(finish_reason=reason, message=SimpleNamespace(content=content))
            ]
        )
    )
    with pytest.raises(ModelUnavailable):
        invoke(gateway)


def test_unapproved_model_is_blocked():
    with pytest.raises(PolicyError):
        IaraBackend(None, model="unapproved", allowed_models=frozenset({"approved"}))
