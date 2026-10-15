"""Conector opcional: SELECT projetado e limitado, metadados Glue e parâmetros de datas.

O caminho recomendado continua sendo EvidenceAdapter.from_runreport, sem novas consultas.
Este conector nunca aceita SQL produzido por LLM e não cria serviços ou tabelas.
"""

import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Annotated

import pandas as pd
from pydantic import Field, model_validator

from ..config import Z_COLUMNS, AdapterConfig, Settings
from ..contracts import EvidenceSnapshot
from ..errors import DataContractError, PolicyError, QueryFailure
from .evidence_builder import build_snapshot
from .quality import digest

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def quoted(name: str) -> str:
    if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
        raise PolicyError("Identificador SQL fora da allowlist de caracteres")
    return '"' + name + '"'


class AthenaConfig(Settings):
    database: str
    tables: dict[str, str]
    workgroup: str
    region: str = "sa-east-1"
    max_rows: Annotated[int, Field(strict=True, ge=1, le=100000)] = 10000
    timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 120.0
    poll_seconds: Annotated[float, Field(gt=0, le=10)] = 1.0
    max_scan_bytes: Annotated[int, Field(strict=True, ge=10_000_000, le=10**15)] = 1_000_000_000
    # Só colunas de data explicitamente aprovadas e descobertas podem filtrar consultas.
    allowed_date_columns: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_identifiers(self):
        quoted(self.database)
        if set(self.tables) != {"PF", "PJ"} or not self.workgroup.strip():
            raise ValueError("Tabelas PF/PJ e workgroup explícitos são obrigatórios")
        for table in self.tables.values():
            quoted(table)
        if not set(self.allowed_date_columns) <= {"PF", "PJ"}:
            raise ValueError("Escopo de filtro desconhecido")
        for column in self.allowed_date_columns.values():
            quoted(column)
        return self


class DateWindow(Settings):
    start: date
    end_exclusive: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end_exclusive:
            raise ValueError("Intervalo de datas inválido")
        return self


@dataclass(frozen=True)
class DataExtract:
    cases: pd.DataFrame
    query_execution_id: str
    bytes_scanned: int
    complete_extract: bool


class AthenaRepository:
    def __init__(self, config: AthenaConfig, *, athena_client=None, glue_client=None):
        self.config = config
        if (athena_client is None) != (glue_client is None):
            raise DataContractError("Injete ambos os clientes ou nenhum")
        if athena_client is None:
            import boto3
            from botocore.config import Config

            session = boto3.Session(region_name=config.region)
            transport = Config(
                connect_timeout=5,
                read_timeout=15,
                retries={"mode": "standard", "total_max_attempts": 2},
            )
            athena_client = session.client("athena", config=transport)
            glue_client = session.client("glue", config=transport)
        self.athena, self.glue = athena_client, glue_client

    def discover(self, scope: str) -> dict[str, tuple[str, str]]:
        if scope not in self.config.tables:
            raise PolicyError("Base não autorizada")
        try:
            table = self.glue.get_table(
                DatabaseName=self.config.database, Name=self.config.tables[scope]
            )["Table"]
            columns = table["StorageDescriptor"]["Columns"] + table.get("PartitionKeys", [])
            result = {}
            for column in columns:
                name = column["Name"]
                quoted(name)
                if name.casefold() in result:
                    raise DataContractError("Esquema ambíguo")
                result[name.casefold()] = (name, column["Type"])
            return result
        except (PolicyError, DataContractError):
            raise
        except Exception:
            raise QueryFailure("Não foi possível descobrir esquema Glue") from None

    def _check_workgroup(self):
        try:
            group = self.athena.get_work_group(WorkGroup=self.config.workgroup)["WorkGroup"]
            config = group["Configuration"]
            cutoff = config.get("BytesScannedCutoffPerQuery", 0)
            encrypted = config.get("ResultConfiguration", {}).get("EncryptionConfiguration", {})
            output = config.get("ResultConfiguration", {}).get("OutputLocation", "")
            if (
                group.get("State") != "ENABLED"
                or not config.get("EnforceWorkGroupConfiguration")
                or not 0 < cutoff <= self.config.max_scan_bytes
                or not output.startswith("s3://")
                or encrypted.get("EncryptionOption") not in {"SSE_S3", "SSE_KMS"}
            ):
                raise PolicyError("Workgroup precisa impor limite e saída criptografada aprovados")
        except PolicyError:
            raise
        except Exception:
            raise QueryFailure("Não foi possível verificar workgroup") from None

    def fetch_scope(
        self, scope: str, *, request_id: str, window: DateWindow | None = None
    ) -> DataExtract:
        schema = self.discover(scope)
        missing = [column for column in Z_COLUMNS if column not in schema]
        if missing:
            # O caminho RunReport permite só contagens. Aqui nenhuma linha identificável é buscada.
            raise DataContractError("Indicadores ausentes; reutilize RunReport ou revise esquema")
        self._check_workgroup()
        columns = [schema[column][0] for column in Z_COLUMNS]
        query = (
            "SELECT "
            + ", ".join(quoted(c) for c in columns)
            + " FROM "
            + quoted(self.config.database)
            + "."
            + quoted(self.config.tables[scope])
        )
        parameters = []
        if window:
            name = self.config.allowed_date_columns.get(scope)
            item = schema.get(name.casefold()) if name else None
            if not item or not (item[1] == "date" or item[1].startswith("timestamp")):
                raise PolicyError("Filtro de data não aprovado ou tipo incompatível")
            query += f" WHERE {quoted(item[0])} >= CAST(? AS DATE)"
            query += f" AND {quoted(item[0])} < CAST(? AS DATE)"
            parameters = [f"'{window.start.isoformat()}'", f"'{window.end_exclusive.isoformat()}'"]
        query += f" LIMIT {self.config.max_rows + 1}"
        args = dict(
            QueryString=query,
            QueryExecutionContext={"Database": self.config.database},
            WorkGroup=self.config.workgroup,
            ClientRequestToken=digest([request_id, query, parameters, self.config.workgroup]),
        )
        if parameters:
            args["ExecutionParameters"] = parameters
        query_id = None
        started = time.monotonic()
        try:
            query_id = self.athena.start_query_execution(**args)["QueryExecutionId"]
            while True:
                state = self.athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
                scanned = int(state.get("Statistics", {}).get("DataScannedInBytes", 0))
                status = state["Status"]["State"]
                if scanned > self.config.max_scan_bytes:
                    raise QueryFailure("Orçamento de leitura excedido")
                if status == "SUCCEEDED":
                    break
                if status in {"FAILED", "CANCELLED"}:
                    raise QueryFailure("Consulta não concluída")
                if time.monotonic() - started >= self.config.timeout_seconds:
                    raise QueryFailure("Consulta excedeu prazo")
                time.sleep(self.config.poll_seconds)
            rows, token, seen = [], None, set()
            first_page = True
            while True:
                if time.monotonic() - started >= self.config.timeout_seconds:
                    raise QueryFailure("Leitura dos resultados excedeu prazo")
                request = dict(QueryExecutionId=query_id, MaxResults=1000)
                if token:
                    request["NextToken"] = token
                response = self.athena.get_query_results(**request)
                page = response["ResultSet"]
                actual = [c["Name"] for c in page["ResultSetMetadata"]["ColumnInfo"]]
                if [c.casefold() for c in actual] != list(Z_COLUMNS):
                    raise DataContractError("Colunas retornadas divergem da projeção")
                data = page["Rows"][1:] if first_page else page["Rows"]
                first_page = False
                for row in data:
                    rows.append([cell.get("VarCharValue") for cell in row["Data"]])
                    if len(rows) >= self.config.max_rows + 1:
                        break
                token = response.get("NextToken")
                if not token or len(rows) >= self.config.max_rows + 1:
                    break
                if token in seen:
                    raise QueryFailure("Token de paginação repetido")
                seen.add(token)
            complete = len(rows) <= self.config.max_rows
            frame = pd.DataFrame(rows[: self.config.max_rows], columns=list(Z_COLUMNS))
            return DataExtract(frame, query_id, scanned, complete)
        except Exception as exc:
            if query_id:
                try:
                    self.athena.stop_query_execution(QueryExecutionId=query_id)
                except Exception:
                    pass
            if isinstance(exc, (QueryFailure, DataContractError, PolicyError)):
                raise
            raise QueryFailure(
                "Falha de leitura Athena; detalhes disponíveis no ambiente AWS"
            ) from None

    def snapshot(
        self,
        *,
        request_id: str,
        windows: dict[str, DateWindow] | None = None,
        adapter_config: AdapterConfig | None = None,
    ) -> EvidenceSnapshot:
        extracted = {
            scope: self.fetch_scope(scope, request_id=request_id, window=(windows or {}).get(scope))
            for scope in ("PF", "PJ")
        }
        return build_snapshot(
            frames={s: e.cases for s, e in extracted.items()},
            source_references={
                s: f"{self.config.database}.{self.config.tables[s]}" for s in extracted
            },
            source_run_id=request_id,
            origin="ATHENA",
            config=adapter_config or AdapterConfig(),
            complete_extract={s: e.complete_extract for s, e in extracted.items()},
            query_metadata={
                s: {"query_execution_id": e.query_execution_id, "bytes_scanned": e.bytes_scanned}
                for s, e in extracted.items()
            },
        )
