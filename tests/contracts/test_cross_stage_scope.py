import json

import pytest

from agente_insider.agents import AGENTS
from agente_insider.config import OrchestratorConfig
from agente_insider.errors import ResponseContractError
from agente_insider.governance.security import model_payload
from tests.fixtures.scenario import outputs, snapshot


@pytest.mark.parametrize(
    "index,key", [(1, "investigations"), (2, "reviews"), (3, "validations"), (4, "risks")]
)
def test_later_stages_cannot_attach_unrelated_scope_evidence(index, key):
    agent = AGENTS[index]
    data = outputs()[agent.name]
    if index == 1:
        data[key][0]["findings"][0]["evidence_id"] = "E-PJ-alert_count"
    else:
        data[key][0]["evidence_ids"] = ["E-PJ-alert_count"]
    with pytest.raises(ResponseContractError):
        agent.validate(json.dumps(data), model_payload(snapshot()), outputs(), OrchestratorConfig())
