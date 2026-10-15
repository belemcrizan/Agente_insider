"""Contratos versionados. JSON válido não significa hipótese comprovada."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"
STAGES = (
    "hypothesis_generator",
    "evidence_investigator",
    "critical_reviewer",
    "methodological_validator",
    "risk_specialist",
    "executive_intelligence",
)
Scope = Literal["PF", "PJ"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
Count = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]
Texts = Annotated[list[Text], Field(min_length=1, max_length=12)]
Refs = Annotated[list[Identifier], Field(max_length=100)]
RequiredRefs = Annotated[list[Identifier], Field(min_length=1, max_length=100)]
Metric = Literal[
    "alert_count",
    "valid_triples",
    "invalid_triples",
    "distinct_triples",
    "largest_group",
    "eligible_pattern_count",
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)

    @field_validator(
        "official_rules_changed",
        "has_adjudicated_outcomes",
        "temporal_holdout_required",
        "correlation_is_not_causation",
        "historical_outcomes_available",
        "empirically_validated",
        "auto_suppression_allowed",
        "official_rule_change_allowed",
        "fp_reduction_proven",
        "human_review_required",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def strict_boolean_literals(cls, value):
        # Pydantic aceita 0/1 em Literal[False/True] mesmo com strict=True.
        if type(value) is not bool:
            raise ValueError("Invariantes booleanos exigem true/false JSON")
        return value


class SourceProfile(Contract):
    scope: Scope
    source_reference: Text
    source_run_id: Identifier
    schema_fingerprint: Identifier
    content_fingerprint: Identifier
    row_count: Count
    complete_extract: bool
    query_execution_id: Identifier | None = None
    bytes_scanned: Annotated[int, Field(strict=True, ge=0, le=10**18)] | None = None


class QualityIssue(Contract):
    scope: Scope
    code: Literal[
        "MISSING_INDICATORS",
        "INVALID_NUMERIC_VALUES",
        "EMPTY_SCOPE",
        "SMALL_SCOPE",
        "PATTERNS_TRUNCATED",
        "INCOMPLETE_EXTRACT",
        "HISTORY_UNAVAILABLE",
        "RULE_METADATA_UNAVAILABLE",
    ]
    count: Count


class Evidence(Contract):
    evidence_id: Identifier
    scope: Scope
    metric: Metric
    value: Count
    source_index: Annotated[int, Field(strict=True, ge=0, le=1)]
    kind: Literal["OBSERVED_AGGREGATE"] = "OBSERVED_AGGREGATE"


class Pattern(Contract):
    pattern_id: Identifier
    scope: Scope
    count: Annotated[int, Field(strict=True, ge=3, le=1_000_000)]
    evidence_ids: RequiredRefs
    kind: Literal["EXACT_NUMERIC_TRIPLE_EXPLORATORY"] = "EXACT_NUMERIC_TRIPLE_EXPLORATORY"


class EvidenceSnapshot(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    snapshot_id: Identifier
    created_at: datetime = Field(default_factory=utcnow)
    origin: Literal["RUNREPORT", "ATHENA", "TEST_FIXTURE"]
    sources: Annotated[list[SourceProfile], Field(min_length=2, max_length=2)]
    evidences: Annotated[list[Evidence], Field(min_length=2, max_length=12)]
    patterns: Annotated[list[Pattern], Field(max_length=200)]
    quality: list[QualityIssue]
    min_group_size: Annotated[int, Field(strict=True, ge=3, le=10000)]
    official_rules_changed: Literal[False] = False
    # Não há contrato aprovado de ingestão de desfechos nesta versão.
    has_adjudicated_outcomes: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        if {s.scope for s in self.sources} != {"PF", "PJ"}:
            raise ValueError("Duas fontes distintas PF/PJ são obrigatórias")
        evidence_ids = [e.evidence_id for e in self.evidences]
        pattern_ids = [p.pattern_id for p in self.patterns]
        if len(evidence_ids) != len(set(evidence_ids)) or len(pattern_ids) != len(set(pattern_ids)):
            raise ValueError("IDs repetidos")
        if len({(e.scope, e.metric) for e in self.evidences}) != len(self.evidences):
            raise ValueError("Métricas duplicadas no mesmo escopo")
        for ev in self.evidences:
            source = self.sources[ev.source_index]
            if ev.scope != source.scope or ev.value > source.row_count:
                raise ValueError("Agregado incompatível com fonte")
        for scope in ("PF", "PJ"):
            source = next(s for s in self.sources if s.scope == scope)
            metrics = {e.metric: e.value for e in self.evidences if e.scope == scope}
            if metrics.get("alert_count") != source.row_count:
                raise ValueError("Total de alertas incompatível com fonte")
            numeric_metrics = {
                "valid_triples",
                "invalid_triples",
                "distinct_triples",
                "largest_group",
                "eligible_pattern_count",
            }
            if set(metrics) & numeric_metrics:
                if not numeric_metrics <= set(metrics):
                    raise ValueError("Métricas numéricas incompletas")
                if metrics["valid_triples"] + metrics["invalid_triples"] != source.row_count:
                    raise ValueError("Contagem de triplas inconsistente")
                if metrics["distinct_triples"] > metrics["valid_triples"]:
                    raise ValueError("Cardinalidade excede triplas válidas")
                if metrics["largest_group"] > metrics["valid_triples"]:
                    raise ValueError("Grupo excede triplas válidas")
                if metrics["eligible_pattern_count"] > metrics["distinct_triples"]:
                    raise ValueError("Quantidade de padrões excede cardinalidade")
        lookup = {e.evidence_id: e for e in self.evidences}
        for pattern in self.patterns:
            if pattern.count < self.min_group_size:
                raise ValueError("Grupo abaixo do mínimo de privacidade")
            if len(pattern.evidence_ids) != len(set(pattern.evidence_ids)) or any(
                ref not in lookup or lookup[ref].scope != pattern.scope
                for ref in pattern.evidence_ids
            ):
                raise ValueError("Proveniência de padrão inválida")
        return self


class ProposedTest(Contract):
    name: Text
    required_data: Texts
    method: Text
    falsification_criteria: Text
    temporal_holdout_required: Literal[True] = True


class Hypothesis(Contract):
    hypothesis_id: Identifier
    title: Text
    statement: Text
    originating_pattern_ids: RequiredRefs
    supporting_evidence_ids: RequiredRefs
    alternative_explanations: Texts
    missing_data: Texts
    proposed_tests: Annotated[list[ProposedTest], Field(min_length=1, max_length=5)]
    falsification_criteria: Texts
    limitations: Texts
    empirical_status: Literal["UNTESTED"]


class HypothesisOutput(Contract):
    hypotheses: Annotated[list[Hypothesis], Field(min_length=1, max_length=8)]


class Finding(Contract):
    evidence_id: Identifier
    interpretation: Text
    category: Literal["OBSERVED", "INFERENCE", "CONTRADICTION"]


class Investigation(Contract):
    hypothesis_id: Identifier
    findings: Annotated[list[Finding], Field(min_length=1, max_length=24)]
    missing_information: Texts
    pending_tests: Texts
    # Ferramentas sugeridas apenas; nenhuma consulta é disparada por uma LLM.
    proposed_tool: Literal["REVIEW_EXISTING_AGGREGATES", "REQUEST_APPROVED_HISTORY"]


class InvestigationOutput(Contract):
    investigations: Annotated[list[Investigation], Field(min_length=1, max_length=8)]


class CriticalReview(Contract):
    hypothesis_id: Identifier
    evidence_ids: RequiredRefs
    alternative_explanations: Texts
    confounders: Texts
    extrapolations: Texts
    counterevidence: Annotated[list[Finding], Field(max_length=24)]
    refutation_tests: Texts
    interpretation_risks: Texts


class CriticalOutput(Contract):
    reviews: Annotated[list[CriticalReview], Field(min_length=1, max_length=8)]


class MethodologicalReview(Contract):
    hypothesis_id: Identifier
    evidence_ids: RequiredRefs
    status: Literal["NEEDS_DATA", "HUMAN_METHOD_REVIEW_REQUIRED"]
    reproducibility_gaps: Texts
    selection_bias: Text
    leakage_risk: Text
    temporal_validation: Text
    statistical_limitations: Texts
    correlation_is_not_causation: Literal[True]
    historical_outcomes_available: Literal[False]
    empirically_validated: Literal[False]


class MethodologicalOutput(Contract):
    validations: Annotated[list[MethodologicalReview], Field(min_length=1, max_length=8)]


class RiskReview(Contract):
    hypothesis_id: Identifier
    evidence_ids: RequiredRefs
    false_negative_risk: Literal["UNKNOWN", "HIGH"]
    safeguards: Texts
    minimum_experiment_conditions: Texts
    human_decisions_required: Texts
    recommended_action: Literal["HUMAN_REVIEW_ONLY"]
    auto_suppression_allowed: Literal[False]
    official_rule_change_allowed: Literal[False]


class RiskOutput(Contract):
    risks: Annotated[list[RiskReview], Field(min_length=1, max_length=8)]


class ExecutiveOutput(Contract):
    summary: Text
    observed_pattern_ids: RequiredRefs
    prioritized_hypothesis_ids: RequiredRefs
    supporting_evidence_ids: RequiredRefs
    opposing_evidence_ids: Refs
    limitations: Texts
    risks: Texts
    recommended_tests: Texts
    technical_dependencies: Texts
    human_decisions: Texts
    next_steps: Texts
    fp_reduction_proven: Literal[False]
    human_review_required: Literal[True]


Output = (
    HypothesisOutput
    | InvestigationOutput
    | CriticalOutput
    | MethodologicalOutput
    | RiskOutput
    | ExecutiveOutput
)


class StageMetric(Contract):
    stage: Identifier
    status: Literal["SUCCEEDED", "FAILED", "SKIPPED"]
    attempts: Annotated[int, Field(strict=True, ge=0, le=3)]
    elapsed_ms: Annotated[float, Field(ge=0)]
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    estimated_cost: Annotated[float, Field(ge=0)] | None = None
    error_code: Identifier | None = None


class RunResult(Contract):
    run_id: Identifier
    snapshot_id: Identifier
    status: Literal["COMPLETE_STRUCTURALLY_VALIDATED", "BLOCKED", "EVIDENCE_ONLY"]
    backend_mode: Literal["IARA", "TEST_FIXTURE", "NONE"]
    started_at: datetime
    finished_at: datetime
    stages: dict[str, dict]
    metrics: list[StageMetric]
    pipeline_fingerprint: Identifier
    error_code: Identifier | None = None
    cost_currency: Identifier | None = None
    fp_reduction_proven: Literal[False] = False
    official_rules_changed: Literal[False] = False
    human_review_required: Literal[True] = True
    empirical_validation: Literal["PENDING"] = "PENDING"
