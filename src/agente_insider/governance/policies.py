"""Semântica mínima entre etapas; não valida a verdade de texto livre."""

from ..contracts import (
    CriticalOutput,
    ExecutiveOutput,
    HypothesisOutput,
    InvestigationOutput,
    MethodologicalOutput,
    RiskOutput,
)
from ..errors import ResponseContractError
from .security import reject_sensitive_text


def unique_refs(refs, allowed):
    if len(refs) != len(set(refs)) or not set(refs) <= set(allowed):
        raise ResponseContractError("Referência repetida ou inexistente")


def validate_output(output, payload: dict, prior: dict, max_hypotheses: int):
    evidence_map = {e["evidence_id"]: e for e in payload["evidences"]}
    patterns = {p["pattern_id"]: p for p in payload["patterns"]}
    hypotheses = prior.get("hypothesis_generator", {}).get("hypotheses", [])
    hypothesis_ids = {h["hypothesis_id"] for h in hypotheses}
    if isinstance(output, HypothesisOutput):
        ids = [h.hypothesis_id for h in output.hypotheses]
        if len(ids) != len(set(ids)) or len(ids) > max_hypotheses:
            raise ResponseContractError("Quantidade ou IDs de hipóteses inválidos")
        for h in output.hypotheses:
            unique_refs(h.originating_pattern_ids, patterns)
            unique_refs(h.supporting_evidence_ids, evidence_map)
            scopes = {patterns[p]["scope"] for p in h.originating_pattern_ids}
            if any(evidence_map[e]["scope"] not in scopes for e in h.supporting_evidence_ids):
                raise ResponseContractError("Evidência de escopo sem padrão de origem")
    elif isinstance(output, ExecutiveOutput):
        unique_refs(output.prioritized_hypothesis_ids, hypothesis_ids)
        unique_refs(output.observed_pattern_ids, patterns)
        unique_refs(output.supporting_evidence_ids, evidence_map)
        unique_refs(output.opposing_evidence_ids, evidence_map)
        if set(output.prioritized_hypothesis_ids) != hypothesis_ids:
            raise ResponseContractError("Síntese deve cobrir todas as hipóteses")
    else:
        key = {
            InvestigationOutput: "investigations",
            CriticalOutput: "reviews",
            MethodologicalOutput: "validations",
            RiskOutput: "risks",
        }[type(output)]
        items = getattr(output, key)
        ids = [item.hypothesis_id for item in items]
        if len(ids) != len(set(ids)) or set(ids) != hypothesis_ids:
            raise ResponseContractError("Cobertura incompleta ou repetida das hipóteses")
        for item in items:
            hypothesis = next(h for h in hypotheses if h["hypothesis_id"] == item.hypothesis_id)
            scopes = {patterns[p]["scope"] for p in hypothesis["originating_pattern_ids"]}
            if hasattr(item, "evidence_ids"):
                unique_refs(item.evidence_ids, evidence_map)
                if any(evidence_map[e]["scope"] not in scopes for e in item.evidence_ids):
                    raise ResponseContractError("Evidência fora do escopo da hipótese")
            for field in ("findings", "counterevidence"):
                for finding in getattr(item, field, []):
                    if (
                        finding.evidence_id not in evidence_map
                        or evidence_map[finding.evidence_id]["scope"] not in scopes
                    ):
                        raise ResponseContractError("Evidência inexistente")
    reject_sensitive_text(output.model_dump())
    return output
