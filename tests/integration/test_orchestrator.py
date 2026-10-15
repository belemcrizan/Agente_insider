import copy
import json
import time
from datetime import timedelta

import pytest

from agente_insider import AgenteInsiderOrchestrator, OrchestratorConfig
from agente_insider.contracts import STAGES, utcnow
from agente_insider.data.runreport_adapter import EvidenceAdapter
from agente_insider.errors import AuthenticationFailure, PolicyError, TransientModelError
from agente_insider.evaluation.metrics import technical_metrics
from agente_insider.governance.audit import CheckpointStore, verify_event_chain
from agente_insider.governance.security import DataAuthorization
from agente_insider.reporting import executive_markdown
from tests.fixtures.scenario import FixtureBackend, outputs, runreport, snapshot

pytestmark = pytest.mark.integration


def real_shape_snapshot():
    # Dados ainda fabricados; apenas exercita o caminho de origem real sob teste.
    return EvidenceAdapter.from_runreport(
        runreport(),
        source_references={"PF": "TEST:PF", "PJ": "TEST:PJ"},
        source_run_id="TEST-UPSTREAM",
    )


def approval(snap, **updates):
    values = dict(
        snapshot_id=snap.snapshot_id,
        approved_by="test-reviewer",
        approval_reference="TEST-APPROVAL",
        environment="dev",
        provider="azure_openai",
        model="test-model",
        expires_at=utcnow() + timedelta(minutes=5),
    )
    values.update(updates)
    return DataAuthorization(**values)


def test_six_stages_execute_and_persist_without_overwrite(tmp_path):
    backend = FixtureBackend()
    store = CheckpointStore(tmp_path / "private", approval_reference="TEST-ONLY")
    result = AgenteInsiderOrchestrator(backend, checkpoint_store=store).run(snapshot())
    assert result.status == "COMPLETE_STRUCTURALLY_VALIDATED", result.error_code
    assert backend.calls == list(STAGES)
    assert len(result.stages) == 6
    assert all(m.status == "SUCCEEDED" for m in result.metrics)
    assert result.backend_mode == "TEST_FIXTURE"
    assert not result.fp_reduction_proven
    assert result.human_review_required
    files = list((store.root / result.run_id).glob("*.json"))
    assert len(files) == 9  # manifest + snapshot + seis etapas + result
    events = [
        json.loads(line)
        for line in (store.root / result.run_id / "events.jsonl").read_text().splitlines()
    ]
    assert verify_event_chain(events)
    events[1]["status"] = "TAMPERED"
    assert not verify_event_chain(events)
    with pytest.raises(FileExistsError):
        store.checkpoint(result.run_id, 1, STAGES[0], {})
    assert "TESTE SINTÉTICO" in executive_markdown(result)


@pytest.mark.parametrize("failed_index", range(6))
def test_failure_at_each_stage_blocks_only_dependents_and_preserves_previous(failed_index):
    values = outputs()
    values[STAGES[failed_index]] = "invalid JSON"
    backend = FixtureBackend(values)
    result = AgenteInsiderOrchestrator(backend).run(snapshot())
    assert result.status == "BLOCKED"
    assert backend.calls == list(STAGES[: failed_index + 1])
    assert len(result.stages) == failed_index
    assert result.metrics[failed_index].status == "FAILED"
    assert all(m.status == "SKIPPED" for m in result.metrics[failed_index + 1 :])
    assert "Execução bloqueada" in executive_markdown(result)


def test_auth_failure_not_retried_and_no_exception_text_in_logs(caplog):
    values = outputs()
    values[STAGES[0]] = AuthenticationFailure("NEVER-LOG-THIS-SECRET")
    backend = FixtureBackend(values)
    with caplog.at_level("INFO", logger="agente_insider.audit"):
        result = AgenteInsiderOrchestrator(backend).run(snapshot())
    assert result.error_code == "AUTHENTICATION_FAILED"
    assert result.metrics[0].attempts == 1
    assert "NEVER-LOG-THIS-SECRET" not in caplog.text


def test_only_explicit_transient_errors_are_retried():
    class OnceTransient(FixtureBackend):
        did_fail = False

        def generate(self, **kwargs):
            if not self.did_fail:
                self.did_fail = True
                raise TransientModelError("synthetic transient")
            return super().generate(**kwargs)

    backend = OnceTransient()
    result = AgenteInsiderOrchestrator(
        backend, config=OrchestratorConfig(retry_backoff_seconds=0)
    ).run(snapshot())
    assert result.status == "COMPLETE_STRUCTURALLY_VALIDATED"
    assert result.metrics[0].attempts == 2
    assert technical_metrics(result)["estimated_total_cost"] is None


def test_transient_attempts_are_bounded():
    values = outputs()
    values[STAGES[0]] = TransientModelError("synthetic transient")
    backend = FixtureBackend(values)
    result = AgenteInsiderOrchestrator(
        backend, config=OrchestratorConfig(retry_backoff_seconds=0, max_attempts=2)
    ).run(snapshot())
    assert result.status == "BLOCKED"
    assert backend.calls == [STAGES[0], STAGES[0]]
    assert result.metrics[0].attempts == 2


def test_timeout_does_not_retry_or_start_next_stage():
    class Slow(FixtureBackend):
        def generate(self, **kwargs):
            time.sleep(0.08)
            return super().generate(**kwargs)

    backend = Slow()
    result = AgenteInsiderOrchestrator(
        backend, config=OrchestratorConfig(stage_timeout_seconds=0.02)
    ).run(snapshot())
    assert result.status == "BLOCKED"
    assert result.error_code == "STAGE_TIMEOUT_NO_RETRY"
    assert result.metrics[0].attempts == 1
    time.sleep(0.1)  # Apenas teste curto; permite encerrar a thread fabricada.
    assert backend.calls == [STAGES[0]]


def test_no_backend_returns_evidence_only():
    result = AgenteInsiderOrchestrator().run(snapshot())
    assert result.status == "EVIDENCE_ONLY"
    assert result.backend_mode == "NONE"
    assert not result.stages
    assert all(m.status == "SKIPPED" for m in result.metrics)


def test_real_data_cannot_use_fixture_backend():
    backend = FixtureBackend()
    result = AgenteInsiderOrchestrator(backend).run(real_shape_snapshot())
    assert result.status == "BLOCKED"
    assert result.error_code == "POLICY_BLOCKED"
    assert not backend.calls


@pytest.mark.parametrize("case", ["missing", "wrong_snapshot", "expired", "wrong_model"])
def test_real_gateway_requires_matching_live_authorization(case):
    class FakeIaraForPolicyTest(FixtureBackend):
        mode, model, environment, provider = "IARA", "test-model", "dev", "azure_openai"

    snap = real_shape_snapshot()
    auth = None if case == "missing" else approval(snap)
    if case == "wrong_snapshot":
        auth = approval(snap, snapshot_id="S-other")
    if case == "expired":
        auth = approval(snap, expires_at=utcnow() - timedelta(seconds=1))
    if case == "wrong_model":
        auth = approval(snap, model="other-model")
    backend = FakeIaraForPolicyTest()
    result = AgenteInsiderOrchestrator(backend).run(snap, authorization=auth)
    assert result.status == "BLOCKED"
    assert not backend.calls


def test_valid_authorization_rechecked_and_allows_contract_test_only():
    class FakeIaraForPolicyTest(FixtureBackend):
        mode, model, environment, provider = "IARA", "test-model", "dev", "azure_openai"

    snap = real_shape_snapshot()
    backend = FakeIaraForPolicyTest(outputs(snap))
    result = AgenteInsiderOrchestrator(backend).run(snap, authorization=approval(snap))
    assert result.status == "COMPLETE_STRUCTURALLY_VALIDATED"
    assert backend.calls == list(STAGES)


def test_mutated_snapshot_is_detected_before_any_call():
    snap = snapshot()
    snap.evidences.append(snap.evidences[0])
    backend = FixtureBackend()
    result = AgenteInsiderOrchestrator(backend).run(snap)
    assert result.status == "BLOCKED"
    assert not backend.calls


def test_prompt_limit_blocks_without_truncating_evidence():
    result = AgenteInsiderOrchestrator(
        FixtureBackend(), config=OrchestratorConfig(max_prompt_chars=1000)
    ).run(snapshot())
    assert result.status == "BLOCKED"
    assert result.metrics[0].attempts == 0


def test_price_unknown_is_null_and_prices_explicit_are_estimations():
    result = AgenteInsiderOrchestrator(FixtureBackend()).run(snapshot())
    assert technical_metrics(result)["estimated_total_cost"] is None
    config = OrchestratorConfig(
        input_price_per_million=1.0, output_price_per_million=2.0, currency="TEST_CURRENCY"
    )
    result = AgenteInsiderOrchestrator(FixtureBackend(), config=config).run(snapshot())
    assert technical_metrics(result)["estimated_total_cost"] == pytest.approx(0.0012)


def test_checkpoint_store_rejects_git_directory_and_missing_approval(tmp_path):
    (tmp_path / ".git").mkdir()
    with pytest.raises(PolicyError):
        CheckpointStore(tmp_path / "artifacts", approval_reference="TEST")
    with pytest.raises(PolicyError):
        CheckpointStore(tmp_path / "anything", approval_reference="")


def test_executive_cannot_omit_hypotheses():
    values = copy.deepcopy(outputs())
    values[STAGES[-1]]["prioritized_hypothesis_ids"] = ["H-OTHER"]
    result = AgenteInsiderOrchestrator(FixtureBackend(values)).run(snapshot())
    assert result.status == "BLOCKED"
    assert result.error_code == "RESPONSE_CONTRACT_ERROR"
