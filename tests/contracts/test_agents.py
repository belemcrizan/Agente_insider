import copy
import json

import pytest

from agente_insider.agents import AGENTS
from agente_insider.config import OrchestratorConfig
from agente_insider.errors import PolicyError, ResponseContractError
from agente_insider.governance.security import model_payload
from agente_insider.llm.response_parser import parse_response
from tests.fixtures.scenario import outputs, snapshot


@pytest.mark.parametrize("agent", AGENTS, ids=[a.name for a in AGENTS])
def test_each_independent_agent_accepts_its_full_contract(agent):
    prior = outputs()
    obj = agent.validate(
        json.dumps(prior[agent.name]), model_payload(snapshot()), prior, OrchestratorConfig()
    )
    assert isinstance(obj, agent.output_model)
    assert "CONTRATO JSON" in agent.system_prompt


@pytest.mark.parametrize(
    "text",
    [
        "```json\n{}\n```",
        "not JSON",
        "[]",
        "null",
        '{"x":1,"x":2}',
        '{"x":NaN}',
        '{"x":Infinity}',
        "",
    ],
)
def test_strict_json_rejects_wrappers_duplicates_nonfinite_and_wrong_root(text):
    with pytest.raises(ResponseContractError):
        parse_response(text, AGENTS[0].output_model, 10000)


def test_response_size_cap_precedes_parse():
    with pytest.raises(ResponseContractError):
        parse_response(" " * 50, AGENTS[0].output_model, 10)


@pytest.mark.parametrize("agent", AGENTS, ids=[a.name for a in AGENTS])
def test_extra_fields_rejected_at_every_stage(agent):
    data = outputs()[agent.name]
    data["invented_field"] = "forbidden"
    with pytest.raises(ResponseContractError):
        agent.validate(json.dumps(data), model_payload(snapshot()), outputs(), OrchestratorConfig())


@pytest.mark.parametrize(
    "stage,key,field,value",
    [
        (0, "hypotheses", "supporting_evidence_ids", ["E-missing"]),
        (0, "hypotheses", "originating_pattern_ids", ["P-missing"]),
        (4, "risks", "auto_suppression_allowed", True),
        (4, "risks", "official_rule_change_allowed", True),
        (4, "risks", "recommended_action", "CLOSE_ALERT"),
        (3, "validations", "empirically_validated", True),
        (3, "validations", "historical_outcomes_available", True),
        (0, "hypotheses", "empirical_status", "PROVEN"),
    ],
)
def test_invalid_references_and_operational_actions_rejected(stage, key, field, value):
    data = copy.deepcopy(outputs())
    agent = AGENTS[stage]
    data[agent.name][key][0][field] = value
    with pytest.raises(ResponseContractError):
        agent.validate(
            json.dumps(data[agent.name]), model_payload(snapshot()), outputs(), OrchestratorConfig()
        )


@pytest.mark.parametrize(
    "index,key", [(1, "investigations"), (2, "reviews"), (3, "validations"), (4, "risks")]
)
def test_hypothesis_coverage_is_exact(index, key):
    agent = AGENTS[index]
    data = outputs()[agent.name]
    data[key][0]["hypothesis_id"] = "H-UNKNOWN"
    with pytest.raises(ResponseContractError):
        agent.validate(json.dumps(data), model_payload(snapshot()), outputs(), OrchestratorConfig())


def test_duplicate_hypothesis_and_cross_scope_evidence_rejected():
    data = outputs()
    hypothesis = data[AGENTS[0].name]["hypotheses"][0]
    data[AGENTS[0].name]["hypotheses"].append(copy.deepcopy(hypothesis))
    with pytest.raises(ResponseContractError):
        AGENTS[0].validate(
            json.dumps(data[AGENTS[0].name]), model_payload(snapshot()), {}, OrchestratorConfig()
        )
    data = outputs()[AGENTS[0].name]
    data["hypotheses"][0]["supporting_evidence_ids"] = ["E-PJ-alert_count"]
    with pytest.raises(ResponseContractError):
        AGENTS[0].validate(json.dumps(data), model_payload(snapshot()), {}, OrchestratorConfig())


def test_pii_in_generated_text_is_rejected():
    data = outputs()[AGENTS[-1].name]
    data["summary"] = "Envie os resultados para person@example.com"
    with pytest.raises(PolicyError):
        AGENTS[-1].validate(
            json.dumps(data), model_payload(snapshot()), outputs(), OrchestratorConfig()
        )


def test_false_fp_claim_rejected():
    data = outputs()[AGENTS[-1].name]
    data["fp_reduction_proven"] = True
    with pytest.raises(ResponseContractError):
        AGENTS[-1].validate(
            json.dumps(data), model_payload(snapshot()), outputs(), OrchestratorConfig()
        )
