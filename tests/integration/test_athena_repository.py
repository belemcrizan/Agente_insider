import copy
from datetime import date

import boto3
import pytest
from botocore.stub import Stubber

from agente_insider.config import Z_COLUMNS
from agente_insider.data.athena_repository import AthenaConfig, AthenaRepository, DateWindow
from agente_insider.errors import DataContractError, PolicyError, QueryFailure

pytestmark = pytest.mark.integration


def config(**updates):
    values = dict(
        database="test_db", tables={"PF": "test_pf", "PJ": "test_pj"}, workgroup="test-wg"
    )
    values.update(updates)
    return AthenaConfig(**values)


def workgroup():
    return {
        "WorkGroup": {
            "Name": "test-wg",
            "State": "ENABLED",
            "Configuration": {
                "EnforceWorkGroupConfiguration": True,
                "BytesScannedCutoffPerQuery": 100_000_000,
                "ResultConfiguration": {
                    "OutputLocation": "s3://approved-test-output/prefix/",
                    "EncryptionConfiguration": {"EncryptionOption": "SSE_KMS"},
                },
            },
        }
    }


def page(rows, *, header=False, token=None):
    data = ([list(Z_COLUMNS)] if header else []) + rows
    value = {
        "ResultSet": {
            "ResultSetMetadata": {"ColumnInfo": [{"Name": c, "Type": "double"} for c in Z_COLUMNS]},
            "Rows": [
                {"Data": [{"VarCharValue": str(v)} if v is not None else {} for v in r]}
                for r in data
            ],
        }
    }
    if token:
        value["NextToken"] = token
    return value


class FakeGlue:
    def get_table(self, **kwargs):
        return {
            "Table": {
                "StorageDescriptor": {
                    "Columns": [{"Name": c, "Type": "double"} for c in Z_COLUMNS]
                },
                "PartitionKeys": [{"Name": "event_date", "Type": "date"}],
            }
        }


class FakeAthena:
    def __init__(self, pages=None):
        self.pages = pages or [page([[2, 1, 1]] * 10, header=True)]
        self.starts, self.reads, self.stops = [], [], []
        self.group = workgroup()
        self.state = "SUCCEEDED"
        self.scanned = 12345

    def get_work_group(self, **kwargs):
        return self.group

    def start_query_execution(self, **kwargs):
        self.starts.append(kwargs)
        return {"QueryExecutionId": "TEST-QUERY-ID"}

    def get_query_execution(self, **kwargs):
        return {
            "QueryExecution": {
                "Status": {"State": self.state},
                "Statistics": {"DataScannedInBytes": self.scanned},
            }
        }

    def get_query_results(self, **kwargs):
        self.reads.append(kwargs)
        return self.pages[len(self.reads) - 1]

    def stop_query_execution(self, **kwargs):
        self.stops.append(kwargs)


def repository(cfg=None, client=None):
    client = client or FakeAthena()
    return AthenaRepository(cfg or config(), athena_client=client, glue_client=FakeGlue()), client


def test_projection_parameters_pagination_and_provenance():
    client = FakeAthena(
        [page([[2, 1, 1], [3, None, 2]], header=True, token="page-two"), page([[4, 2, 2]])]
    )
    repo, client = repository(config(allowed_date_columns={"PF": "event_date"}), client)
    extract = repo.fetch_scope(
        "PF",
        request_id="test-req",
        window=DateWindow(start=date(2026, 1, 1), end_exclusive=date(2026, 2, 1)),
    )
    assert len(extract.cases) == 3
    assert extract.cases.iloc[1, 1] is None
    assert extract.complete_extract
    assert extract.bytes_scanned == 12345
    assert client.reads[1]["NextToken"] == "page-two"
    start = client.starts[0]
    assert "SELECT *" not in start["QueryString"]
    assert "CAST(? AS DATE)" in start["QueryString"]
    assert start["ExecutionParameters"] == ["'2026-01-01'", "'2026-02-01'"]
    assert len(start["ClientRequestToken"]) == 64
    assert not client.stops


def test_limit_overflow_is_explicit_and_does_not_claim_full_population():
    repo, _ = repository(config(max_rows=3))
    extract = repo.fetch_scope("PJ", request_id="test")
    assert len(extract.cases) == 3
    assert not extract.complete_extract


@pytest.mark.parametrize("change", ["no_cutoff", "not_enforced", "no_encryption", "disabled"])
def test_query_not_started_without_workgroup_controls(change):
    repo, client = repository()
    settings = client.group["WorkGroup"]["Configuration"]
    if change == "no_cutoff":
        settings.pop("BytesScannedCutoffPerQuery")
    elif change == "not_enforced":
        settings["EnforceWorkGroupConfiguration"] = False
    elif change == "no_encryption":
        settings["ResultConfiguration"].pop("EncryptionConfiguration")
    else:
        client.group["WorkGroup"]["State"] = "DISABLED"
    with pytest.raises(PolicyError):
        repo.fetch_scope("PF", request_id="test")
    assert not client.starts


def test_scan_budget_cancels_query():
    repo, client = repository()
    client.scanned = 2_000_000_000
    with pytest.raises(QueryFailure):
        repo.fetch_scope("PF", request_id="test")
    assert len(client.stops) == 1


def test_timeout_cancels_query():
    repo, client = repository(config(timeout_seconds=0.01, poll_seconds=0.001))
    client.state = "RUNNING"
    with pytest.raises(QueryFailure):
        repo.fetch_scope("PF", request_id="test")
    assert len(client.stops) == 1


def test_failed_query_sanitizes_source_reason():
    repo, client = repository()
    client.state = "FAILED"
    with pytest.raises(QueryFailure):
        repo.fetch_scope("PF", request_id="test")
    assert client.stops


def test_date_filter_not_in_allowlist_is_blocked():
    repo, client = repository()
    with pytest.raises(PolicyError):
        repo.fetch_scope(
            "PF",
            request_id="test",
            window=DateWindow(start=date(2026, 1, 1), end_exclusive=date(2026, 2, 1)),
        )
    assert not client.starts


@pytest.mark.parametrize("identifier", ['test"; DROP TABLE x', "schema.table", "a b", ""])
def test_identifiers_reject_sql_injection(identifier):
    with pytest.raises((ValueError, PolicyError)):
        config(database=identifier)


def test_missing_schema_does_not_fetch_identifiable_rows():
    repo, client = repository()
    repo.glue.get_table = lambda **kw: {"Table": {"StorageDescriptor": {"Columns": []}}}
    with pytest.raises(DataContractError):
        repo.fetch_scope("PF", request_id="test")
    assert not client.starts


def test_repeated_pagination_token_is_blocked():
    repo, client = repository(
        client=FakeAthena(
            [page([[1, 2, 3]], header=True, token="same"), page([[2, 3, 4]], token="same")]
        )
    )
    with pytest.raises(QueryFailure):
        repo.fetch_scope("PF", request_id="test")
    assert client.stops


def test_full_snapshot_uses_two_bounded_queries_and_preserves_query_ids():
    client = FakeAthena([page([[2, 1, 1]] * 10, header=True), page([[2, 1, 1]] * 15, header=True)])
    repo, client = repository(client=client)
    snap = repo.snapshot(request_id="TEST-SNAPSHOT")
    assert snap.origin == "ATHENA"
    assert len(client.starts) == 2
    assert all(s.query_execution_id == "TEST-QUERY-ID" for s in snap.sources)
    assert all(s.complete_extract for s in snap.sources)


def test_requests_match_installed_boto3_aws_api_shapes_without_network():
    # Stubber valida esquemas do SDK instalado e impede chamadas externas.
    athena = boto3.client(
        "athena",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    glue = boto3.client(
        "glue",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    a_stub, g_stub = Stubber(athena), Stubber(glue)
    g_stub.add_response(
        "get_table",
        {
            "Table": {
                "Name": "test_pf",
                "StorageDescriptor": {
                    "Columns": [{"Name": c, "Type": "double"} for c in Z_COLUMNS]
                },
            }
        },
        {"DatabaseName": "test_db", "Name": "test_pf"},
    )
    a_stub.add_response("get_work_group", copy.deepcopy(workgroup()), {"WorkGroup": "test-wg"})
    a_stub.add_response("start_query_execution", {"QueryExecutionId": "TEST-ID"})
    a_stub.add_response(
        "get_query_execution",
        {
            "QueryExecution": {
                "Status": {"State": "SUCCEEDED"},
                "Statistics": {"DataScannedInBytes": 100},
            }
        },
    )
    a_stub.add_response("get_query_results", page([[2, 1, 1]], header=True))
    with a_stub, g_stub:
        repo = AthenaRepository(config(), athena_client=athena, glue_client=glue)
        assert len(repo.fetch_scope("PF", request_id="TEST-STUBBER").cases) == 1
        a_stub.assert_no_pending_responses()
        g_stub.assert_no_pending_responses()
