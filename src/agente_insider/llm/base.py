"""Contrato injetável para gateway, sem backend sintético de produção."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ModelReply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelBackend(Protocol):
    mode: Literal["IARA", "TEST_FIXTURE"]
    model: str
    environment: str
    provider: str

    def generate(
        self, *, stage: str, system: str, user: str, max_completion_tokens: int
    ) -> ModelReply: ...
