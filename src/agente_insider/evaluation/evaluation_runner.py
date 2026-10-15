"""Métricas descritivas de revisão; entrada exige rótulos humanos explícitos."""

from typing import Annotated

from pydantic import Field

from ..contracts import Contract, Identifier


class HumanAssessment(Contract):
    run_id: Identifier
    hypothesis_id: Identifier
    reviewer_id: Identifier
    investigable: bool
    evidence_fidelity: Annotated[int, Field(strict=True, ge=1, le=5)]
    refutation_quality: Annotated[int, Field(strict=True, ge=1, le=5)]
    risk_coverage: Annotated[int, Field(strict=True, ge=1, le=5)]
    investigation_minutes: Annotated[float, Field(ge=0)]


def summarize_assessments(assessments: list[HumanAssessment]) -> dict:
    if not assessments:
        return {
            "review_count": 0,
            "investigable_fraction": None,
            "fp_reduction": None,
            "false_negative_rate": None,
        }
    keys = [(a.run_id, a.hypothesis_id, a.reviewer_id) for a in assessments]
    if len(keys) != len(set(keys)):
        raise ValueError("Avaliação duplicada para a mesma hipótese/revisor")
    return {
        "review_count": len(assessments),
        "investigable_fraction": sum(a.investigable for a in assessments) / len(assessments),
        "mean_evidence_fidelity": sum(a.evidence_fidelity for a in assessments) / len(assessments),
        "mean_refutation_quality": sum(a.refutation_quality for a in assessments)
        / len(assessments),
        "fp_reduction": None,
        "false_negative_rate": None,
    }
