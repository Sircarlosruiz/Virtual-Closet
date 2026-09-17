from collections.abc import Mapping
from dataclasses import dataclass

_SAFE_USAGE_FIELDS = {
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "input_tokens_details",
    "output_tokens_details",
}


@dataclass(frozen=True)
class UsageRecord:
    status: str  # "reported" | "unknown"
    model: str | None
    call_count: int | None
    raw: dict | None


class UsageAccountingService:
    """Normalizes provider usage into a UsageRecord.

    Never fabricates a numeric value where the provider is silent — absent
    usage is recorded as `unknown`, not zero.
    """

    def normalize(self, model: str | None, raw_usage: Mapping[str, object] | None) -> UsageRecord:
        if not raw_usage:
            return UsageRecord(status="unknown", model=model, call_count=None, raw=None)

        safe_raw = {k: v for k, v in raw_usage.items() if k in _SAFE_USAGE_FIELDS}
        if not safe_raw:
            return UsageRecord(status="unknown", model=model, call_count=None, raw=None)

        return UsageRecord(status="reported", model=model, call_count=1, raw=safe_raw)
