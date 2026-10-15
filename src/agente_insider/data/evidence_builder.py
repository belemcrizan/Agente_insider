"""Agregação determinística; dados brutos nunca saem deste módulo."""

from collections.abc import Mapping

import pandas as pd

from ..config import Z_COLUMNS, AdapterConfig
from ..contracts import Evidence, EvidenceSnapshot, Pattern, QualityIssue, SourceProfile
from ..errors import DataContractError
from .quality import digest, inspect_frame


def build_snapshot(
    *,
    frames: Mapping[str, pd.DataFrame],
    source_references: Mapping[str, str],
    source_run_id: str,
    origin: str,
    config: AdapterConfig,
    complete_extract: Mapping[str, bool] | None = None,
    query_metadata: Mapping[str, dict] | None = None,
) -> EvidenceSnapshot:
    if set(frames) != {"PF", "PJ"} or set(source_references) != {"PF", "PJ"}:
        raise DataContractError("Fontes e referências explícitas PF/PJ são obrigatórias")
    if origin not in {"RUNREPORT", "ATHENA", "TEST_FIXTURE"}:
        raise DataContractError("Origem desconhecida")
    complete = complete_extract or {"PF": False, "PJ": False}
    if set(complete) != {"PF", "PJ"} or any(type(v) is not bool for v in complete.values()):
        raise DataContractError("Declaração de completude PF/PJ inválida")
    sources, evidences, patterns, quality = [], [], [], []
    for source_index, scope in enumerate(("PF", "PJ")):
        frame = frames[scope]
        numeric, schema_hash, content_hash = inspect_frame(frame, config.max_rows_per_scope)
        metadata = (query_metadata or {}).get(scope, {})
        source = SourceProfile(
            scope=scope,
            source_reference=source_references[scope],
            source_run_id=source_run_id,
            schema_fingerprint=schema_hash,
            content_fingerprint=content_hash,
            row_count=len(frame),
            complete_extract=complete[scope],
            **metadata,
        )
        sources.append(source)

        def add(metric, value, scope=scope, source_index=source_index):
            item = Evidence(
                evidence_id=f"E-{scope}-{metric}",
                scope=scope,
                metric=metric,
                value=int(value),
                source_index=source_index,
            )
            evidences.append(item)
            return item.evidence_id

        def issue(code, count=1, scope=scope):
            quality.append(QualityIssue(scope=scope, code=code, count=int(count)))

        total_ref = add("alert_count", len(frame))
        issue("HISTORY_UNAVAILABLE")
        issue("RULE_METADATA_UNAVAILABLE")
        if not source.complete_extract:
            issue("INCOMPLETE_EXTRACT")
        if len(frame) == 0:
            issue("EMPTY_SCOPE", 0)
        elif len(frame) < config.min_group_size:
            issue("SMALL_SCOPE", len(frame))
        if numeric is None:
            names = {name.casefold() for name in frame.columns}
            issue("MISSING_INDICATORS", sum(column not in names for column in Z_COLUMNS))
            continue
        valid = numeric.dropna()
        valid_ref = add("valid_triples", len(valid))
        invalid = len(frame) - len(valid)
        add("invalid_triples", invalid)
        if invalid:
            issue("INVALID_NUMERIC_VALUES", invalid)
        groups = valid.value_counts(sort=False).sort_index()
        add("distinct_triples", len(groups))
        add("largest_group", int(groups.max()) if len(groups) else 0)
        eligible = [
            (key, int(count)) for key, count in groups.items() if count >= config.min_group_size
        ]
        eligible.sort(key=lambda pair: (-pair[1], pair[0]))
        add("eligible_pattern_count", len(eligible))
        if len(eligible) > config.max_patterns_per_scope:
            issue("PATTERNS_TRUNCATED", len(eligible) - config.max_patterns_per_scope)
        for key, count in eligible[: config.max_patterns_per_scope]:
            # Tokens opacos vinculados ao snapshot, nunca os valores da tripla.
            pattern_id = f"P-{scope}-" + digest([content_hash, list(key)])[:20]
            patterns.append(
                Pattern(
                    pattern_id=pattern_id,
                    scope=scope,
                    count=count,
                    evidence_ids=[total_ref, valid_ref],
                )
            )
    snapshot = EvidenceSnapshot(
        snapshot_id="S-pending",
        origin=origin,
        sources=sources,
        evidences=evidences,
        patterns=patterns,
        quality=quality,
        min_group_size=config.min_group_size,
    )
    return snapshot.model_copy(update={"snapshot_id": snapshot_identity(snapshot)})


def snapshot_identity(snapshot: EvidenceSnapshot) -> str:
    content = snapshot.model_dump(mode="json", exclude={"snapshot_id", "created_at"})
    return "S-" + digest(content)
