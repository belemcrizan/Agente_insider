"""Integração isolada com a interface IaraGenAI fornecida pelo operador."""

from typing import Literal

from ..errors import AuthenticationFailure, ModelUnavailable, PolicyError, TransientModelError
from .base import ModelReply


class IaraBackend:
    mode: Literal["IARA"] = "IARA"

    def __init__(
        self,
        client,
        *,
        model: str,
        allowed_models: frozenset[str],
        environment: str = "dev",
        provider: str = "azure_openai",
    ):
        if model not in allowed_models or environment not in {"dev", "hml", "prod"}:
            raise PolicyError("Modelo ou ambiente não autorizado")
        if provider != "azure_openai":
            raise PolicyError("Provider não autorizado por este adaptador")
        self.client = client
        self.model = model
        self.environment = environment
        self.provider = provider

    def generate(
        self, *, stage: str, system: str, user: str, max_completion_tokens: int
    ) -> ModelReply:
        """Não autentica nem registra segredos. Sem retry implícito nesta classe.

        Configure retries/timeouts do transporte no SDK corporativo aprovado.
        A compatibilidade com o ambiente real deve ser validada no SageMaker.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                enable_polling=True,
                response_format={"type": "json_object"},
                max_tokens=max_completion_tokens,
            )
            if (
                not response.choices
                or getattr(response.choices[0], "finish_reason", None) == "length"
            ):
                raise ModelUnavailable("Resposta truncada ou ausente")
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content.strip():
                raise ModelUnavailable("Resposta textual ausente")
            usage = getattr(response, "usage", None)

            def tokens(name):
                value = getattr(usage, name, None)
                return value if type(value) is int and 0 <= value <= 1_000_000 else None

            return ModelReply(content, tokens("prompt_tokens"), tokens("completion_tokens"))
        except (AuthenticationFailure, ModelUnavailable):
            raise
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            name = type(exc).__name__
            if status in {401, 403} or name in {"AuthenticationError", "PermissionDeniedError"}:
                raise AuthenticationFailure("Autenticação/autorização indisponível") from None
            if status in {429, 500, 502, 503, 504}:
                raise TransientModelError("Falha transitória do gateway") from None
            # Timeout de transporte tem resultado desconhecido: não repetir para evitar custo duplo.
            raise ModelUnavailable("Gateway indisponível ou interface incompatível") from None
