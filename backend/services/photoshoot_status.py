"""Pure derivation of aggregate photoshoot status and counters."""

from __future__ import annotations

from dataclasses import dataclass


def derive(
    *,
    expected_results: int,
    completed_results: int,
    work_pending: bool,
) -> str:
    if work_pending:
        return "running"
    if completed_results >= expected_results and expected_results > 0:
        return "completed"
    if completed_results >= 1:
        return "partial"
    return "failed"


def view_status(
    *,
    stages,
    expected_results: int,
    completed_results: int,
) -> str:
    """Status for GET: queued until a stage actually starts."""
    live = [stage for stage in stages if getattr(stage, "status", None) != "skipped"]
    if completed_results == 0 and all(
        getattr(stage, "status", None) == "pending" for stage in live
    ):
        return "queued"
    work_pending = any(
        getattr(stage, "status", None) in {"pending", "running"} for stage in stages
    )
    return derive(
        expected_results=expected_results,
        completed_results=completed_results,
        work_pending=work_pending,
    )


@dataclass(frozen=True)
class AggregateCounters:
    expected_results: int
    completed_results: int
    failed_results: int


def counters(
    *,
    expected_results: int,
    completed_results: int,
    stages,
    configuration: dict | None = None,
) -> AggregateCounters:
    work_pending = any(
        getattr(stage, "status", None) in {"pending", "running"} for stage in stages
    )
    dead = _dead_slots(stages, configuration or {}, expected_results)
    failed = (
        max(expected_results - completed_results, 0) if not work_pending else dead
    )
    return AggregateCounters(
        expected_results=expected_results,
        completed_results=completed_results,
        failed_results=failed,
    )


def _dead_slots(stages, configuration: dict, expected_results: int) -> int:
    pose_count = len(configuration.get("pose_types") or [])
    by_name = {getattr(stage, "name", None): stage for stage in stages}
    tryoff = by_name.get("tryoff")
    if tryoff is not None and getattr(tryoff, "status", None) == "failed":
        return expected_results

    dead_models: set[str] = set()
    for name in ("vton", "poses"):
        stage = by_name.get(name)
        refs = getattr(stage, "external_refs", None) or []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            if ref.get("status") == "failed" and ref.get("model_id"):
                dead_models.add(str(ref["model_id"]))
    if not pose_count:
        return 0
    return len(dead_models) * pose_count
