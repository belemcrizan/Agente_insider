import json

import pytest
from pydantic import ValidationError

from agente_insider import AgenteInsiderOrchestrator
from agente_insider.cli import main
from agente_insider.evaluation.evaluation_runner import HumanAssessment, summarize_assessments
from tests.fixtures.scenario import FixtureBackend, snapshot


def test_human_assessment_is_descriptive_and_never_claims_fp_reduction():
    empty = summarize_assessments([])
    assert empty["investigable_fraction"] is None
    a = HumanAssessment(
        run_id="TEST-RUN",
        hypothesis_id="TEST-H",
        reviewer_id="TEST-R1",
        investigable=True,
        evidence_fidelity=4,
        refutation_quality=3,
        risk_coverage=4,
        investigation_minutes=5.0,
    )
    summary = summarize_assessments([a])
    assert summary["review_count"] == 1
    assert summary["investigable_fraction"] == 1.0
    assert summary["fp_reduction"] is None
    assert summary["false_negative_rate"] is None
    with pytest.raises(ValueError):
        summarize_assessments([a, a])
    with pytest.raises(ValidationError):
        HumanAssessment.model_validate({**a.model_dump(), "evidence_fidelity": 6})


def test_doctor_and_schema_are_local_and_do_not_claim_authentication(capsys):
    assert main(["doctor"]) == 0
    diagnostic = json.loads(capsys.readouterr().out)
    assert diagnostic["iara_authentication"] == "NOT_TESTED"
    assert main(["schema", "risk_specialist"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert "RiskReview" in schema["$defs"]


def test_cli_validates_snapshot_and_detects_mutation(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    snap = snapshot()
    path.write_text(snap.model_dump_json())
    assert main(["validate-snapshot", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["contract_valid"]
    data = snap.model_dump(mode="json")
    data["snapshot_id"] = "S-altered"
    path.write_text(json.dumps(data))
    with pytest.raises(SystemExit):
        main(["validate-snapshot", str(path)])


def test_cli_report_and_metrics_expose_actual_mode(tmp_path, capsys):
    result = AgenteInsiderOrchestrator(FixtureBackend()).run(snapshot())
    path = tmp_path / "run.json"
    path.write_text(result.model_dump_json())
    assert main(["report", str(path)]) == 0
    assert "TESTE SINTÉTICO" in capsys.readouterr().out
    assert main(["metrics", str(path)]) == 0
    values = json.loads(capsys.readouterr().out)
    assert values["successful_stages"] == 6
    assert values["business_validation"] == "PENDING_HUMAN_LABELS_AND_REVIEW"
