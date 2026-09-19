"""Pure derivation of aggregate photoshoot status."""


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
