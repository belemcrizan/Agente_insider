import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from agente_insider.config import OrchestratorConfig
from agente_insider.contracts import EvidenceSnapshot, RiskReview
from agente_insider.governance.security import DataAuthorization
from tests.fixtures.scenario import outputs, snapshot


@pytest.mark.parametrize("value", [0, 1, "false", "true", None])
def test_safety_invariants_require_actual_json_booleans(value):
    data = outputs()["risk_specialist"]["risks"][0]
    data["auto_suppression_allowed"] = value
    with pytest.raises(ValidationError):
        RiskReview.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_source",
        "total",
        "count_sum",
        "cardinality",
        "partial_metrics",
        "bad_pattern",
        "small_pattern",
    ],
)
def test_snapshot_rejects_inconsistent_aggregate_provenance(change):
    data = snapshot().model_dump(mode="json")
    if change == "duplicate_source":
        data["sources"][1]["scope"] = "PF"
    elif change == "total":
        data["evidences"][0]["value"] = 9
    elif change == "count_sum":
        next(e for e in data["evidences"] if e["metric"] == "invalid_triples")["value"] = 1
    elif change == "cardinality":
        next(e for e in data["evidences"] if e["metric"] == "valid_triples")["value"] = 0
    elif change == "partial_metrics":
        data["evidences"] = [e for e in data["evidences"] if e["metric"] != "invalid_triples"]
    elif change == "bad_pattern":
        data["patterns"][0]["evidence_ids"] = ["E-unknown"]
    elif change == "small_pattern":
        data["patterns"][0]["count"] = 3
    with pytest.raises(ValidationError):
        EvidenceSnapshot.model_validate_json(json.dumps(data))


def test_authorization_rejects_naive_timezone():
    with pytest.raises(ValidationError):
        DataAuthorization(
            snapshot_id="S-test",
            approved_by="test",
            approval_reference="TEST",
            environment="dev",
            provider="azure_openai",
            model="test-model",
            expires_at=datetime(2030, 1, 1),
        )


def test_cost_configuration_rejects_unknown_currency_and_nonfinite_price():
    with pytest.raises(ValidationError):
        OrchestratorConfig(input_price_per_million=1.0)
    with pytest.raises(ValidationError):
        OrchestratorConfig(
            input_price_per_million=float("nan"), output_price_per_million=1.0, currency="TEST"
        )
