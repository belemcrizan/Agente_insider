"""Ponte para a interface observada no repositório anterior, sem nova consulta AWS."""

from collections.abc import Mapping
from typing import Protocol

import pandas as pd

from ..config import AdapterConfig
from ..contracts import EvidenceSnapshot
from ..errors import DataContractError
from .evidence_builder import build_snapshot


class BaseResultLike(Protocol):
    cases: pd.DataFrame


class RunReportLike(Protocol):
    results: Mapping[str, BaseResultLike]


class EvidenceAdapter:
    @staticmethod
    def from_runreport(
        relatorio: RunReportLike,
        *,
        source_references: Mapping[str, str],
        source_run_id: str,
        config: AdapterConfig | None = None,
        complete_extract: Mapping[str, bool] | None = None,
    ) -> EvidenceSnapshot:
        """Lê .results[scope].cases; não altera DataFrames ou presume metadados.

        source_run_id e source_references vêm do operador/pipeline real.
        Por padrão o recorte é considerado incompleto até declaração explícita.
        """
        results = getattr(relatorio, "results", None)
        if not isinstance(results, Mapping) or not {"PF", "PJ"}.issubset(results):
            raise DataContractError("relatorio.results deve conter PF/PJ")
        frames = {scope: getattr(results[scope], "cases", None) for scope in ("PF", "PJ")}
        return build_snapshot(
            frames=frames,
            source_references=source_references,
            source_run_id=source_run_id,
            origin="RUNREPORT",
            config=config or AdapterConfig(),
            complete_extract=complete_extract,
        )
