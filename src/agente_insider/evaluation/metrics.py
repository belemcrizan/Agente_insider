from ..contracts import RunResult


def technical_metrics(result: RunResult) -> dict:
    successful = sum(m.status == "SUCCEEDED" for m in result.metrics)
    attempted = [m for m in result.metrics if m.attempts]
    costs_known = bool(attempted) and all(m.estimated_cost is not None for m in attempted)
    # Retentativas/falhas anteriores podem ter sido faturadas sem usage disponível.
    costs_known = costs_known and all(m.attempts == 1 for m in attempted)
    return {
        "run_id": result.run_id,
        "snapshot_id": result.snapshot_id,
        "status": result.status,
        "backend_mode": result.backend_mode,
        "successful_stages": successful,
        "required_stages": 6,
        "stage_success_rate": successful / 6,
        "elapsed_ms": (result.finished_at - result.started_at).total_seconds() * 1000,
        "estimated_total_cost": sum(m.estimated_cost for m in attempted) if costs_known else None,
        "cost_currency": result.cost_currency,
        "business_validation": "PENDING_HUMAN_LABELS_AND_REVIEW",
    }
