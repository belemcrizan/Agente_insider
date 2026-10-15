"""Projeção allowlist, aprovação com escopo e inspeção heurística de respostas."""

import re
from datetime import datetime
from typing import Literal

from pydantic import model_validator

from ..contracts import Contract, EvidenceSnapshot, Identifier, Text, utcnow
from ..errors import PolicyError

PII_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:client_secret|api_key|password)\s*[:=]\s*\S+", re.I),
)


class DataAuthorization(Contract):
    snapshot_id: Identifier
    approved_by: Text
    approval_reference: Text
    environment: Literal["dev", "hml", "prod"]
    provider: Literal["azure_openai"]
    model: Identifier
    expires_at: datetime

    @model_validator(mode="after")
    def timezone_required(self):
        if self.expires_at.tzinfo is None:
            raise ValueError("Validade da autorização deve incluir timezone")
        return self

    def verify(self, snapshot_id: str, *, environment: str, provider: str, model: str):
        if (
            self.snapshot_id != snapshot_id
            or self.expires_at <= utcnow()
            or self.environment != environment
            or self.provider != provider
            or self.model != model
        ):
            raise PolicyError("Autorização ausente, expirada ou incompatível")


def reject_sensitive_text(value: object) -> None:
    """Defesa adicional, não certificação de anonimização ou correção semântica."""
    if isinstance(value, dict):
        for item in value.values():
            reject_sensitive_text(item)
    elif isinstance(value, list):
        for item in value:
            reject_sensitive_text(item)
    elif isinstance(value, str) and any(pattern.search(value) for pattern in PII_PATTERNS):
        raise PolicyError("Conteúdo potencialmente sensível bloqueado")


def model_payload(snapshot: EvidenceSnapshot) -> dict:
    """Não transfere tabelas, metadados livres, triplas, identificadores ou linhas."""
    eligible_scopes = {s.scope for s in snapshot.sources if s.row_count >= snapshot.min_group_size}
    evidences = [
        e.model_dump()
        for e in snapshot.evidences
        if e.scope in eligible_scopes and (e.value == 0 or e.value >= snapshot.min_group_size)
    ]
    refs = {e["evidence_id"] for e in evidences}
    patterns = [
        p.model_dump()
        for p in snapshot.patterns
        if p.scope in eligible_scopes and set(p.evidence_ids) <= refs
    ]
    result = {
        "schema_version": snapshot.schema_version,
        "snapshot_id": snapshot.snapshot_id,
        "origin": snapshot.origin,
        "evidences": evidences,
        "patterns": patterns,
        "quality_codes": sorted({q.code for q in snapshot.quality}),
        "complete_extract": all(s.complete_extract for s in snapshot.sources),
        "has_adjudicated_outcomes": False,
        "official_rules_changed": False,
    }
    reject_sensitive_text(result)
    return result
