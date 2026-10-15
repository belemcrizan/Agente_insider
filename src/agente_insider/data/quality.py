"""Inspeção numérica sem deduzir regras ou rótulos de investigação."""

import hashlib
import json

import pandas as pd

from ..config import Z_COLUMNS
from ..errors import DataContractError


def digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def inspect_frame(frame: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame | None, str, str]:
    """Retorna somente indicadores numéricos e fingerprints locais.

    Nenhum nome/identificador/observação de cliente é selecionado. As triplas
    são comparadas sem arredondamento ou limites estatísticos inventados.
    """
    if not isinstance(frame, pd.DataFrame) or len(frame) > max_rows:
        raise DataContractError("cases deve ser DataFrame dentro do limite de linhas")
    if any(not isinstance(c, str) for c in frame.columns):
        raise DataContractError("Colunas devem possuir nomes textuais")
    names = [c.casefold() for c in frame.columns]
    if len(names) != len(set(names)):
        raise DataContractError("Colunas ambíguas após normalização")
    schema_hash = digest(sorted(zip(names, map(str, frame.dtypes), strict=True)))
    mapping = dict(zip(names, frame.columns, strict=True))
    if not all(column in mapping for column in Z_COLUMNS):
        return None, schema_hash, digest({"rows": len(frame), "schema": schema_hash})
    selected = frame.loc[:, [mapping[c] for c in Z_COLUMNS]].copy()
    selected.columns = list(Z_COLUMNS)
    numeric = selected.apply(pd.to_numeric, errors="coerce").astype("float64")
    numeric = numeric.replace([float("inf"), -float("inf")], float("nan"))
    # Hash de indicadores relevantes, estável entre ordens de linhas.
    row_hashes = sorted(int(n) for n in pd.util.hash_pandas_object(numeric, index=False))
    return numeric, schema_hash, digest({"rows": row_hashes, "schema": schema_hash})
