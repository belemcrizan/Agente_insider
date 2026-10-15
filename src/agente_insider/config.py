"""Configuração explícita: nenhuma tabela, permissão ou preço presumido."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Z_COLUMNS = ("z_score_20dias_d0", "z_score_20dias_d1", "delta_z")


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class AdapterConfig(Settings):
    min_group_size: Annotated[int, Field(strict=True, ge=3, le=10000)] = 5
    max_rows_per_scope: Annotated[int, Field(strict=True, ge=1, le=1_000_000)] = 100_000
    max_patterns_per_scope: Annotated[int, Field(strict=True, ge=1, le=100)] = 20


class OrchestratorConfig(Settings):
    max_hypotheses: Annotated[int, Field(strict=True, ge=1, le=8)] = 4
    max_prompt_chars: Annotated[int, Field(strict=True, ge=1000, le=250000)] = 100000
    max_response_chars: Annotated[int, Field(strict=True, ge=1000, le=100000)] = 40000
    max_completion_tokens: Annotated[int, Field(strict=True, ge=256, le=16000)] = 4000
    # Apenas erros transitórios explicitamente classificados podem ser repetidos.
    max_attempts: Annotated[int, Field(strict=True, ge=1, le=3)] = 2
    stage_timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 90.0
    retry_backoff_seconds: Annotated[float, Field(ge=0, le=10)] = 0.5
    # Preços opcionais aprovados, na MESMA moeda, por milhão de tokens.
    input_price_per_million: Annotated[float, Field(ge=0)] | None = None
    output_price_per_million: Annotated[float, Field(ge=0)] | None = None
    currency: str | None = None

    @model_validator(mode="after")
    def prices_require_currency(self):
        prices = (self.input_price_per_million, self.output_price_per_million)
        if any(p is not None for p in prices):
            if any(p is None for p in prices) or not self.currency or not self.currency.strip():
                raise ValueError("Preços exigem ambos os valores e moeda explícita")
        return self
