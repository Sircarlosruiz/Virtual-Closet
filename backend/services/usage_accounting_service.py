from collections.abc import Mapping
from dataclasses import dataclass

_SAFE_USAGE_FIELDS_OPENAI = {
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "input_tokens_details",
    "output_tokens_details",
}

# Kept as an alias so intent-008 tests and callers that imported the name still
# resolve. OpenAI-only; Replicate uses `_SAFE_USAGE_FIELDS_REPLICATE`.
_SAFE_USAGE_FIELDS = _SAFE_USAGE_FIELDS_OPENAI

_SAFE_USAGE_FIELDS_REPLICATE = {
    "prediction_id",
    "predict_time",
    "total_time",
}


@dataclass(frozen=True)
class UsageRecord:
    status: str  # "reported" | "unknown"
    model: str | None
    call_count: int | None
    raw: dict | None


def _informed(value: object) -> bool:
    """True when the provider actually sent a value. Zero is informed; None is not."""
    return value is not None and value != ""


def _replicate_scalar(key: str, value: object) -> object | None:
    """Keep only JSON-serializable Replicate whitelist values; never invent 0."""
    if not _informed(value):
        return None
    if key == "prediction_id" and isinstance(value, str):
        return value
    if key in {"predict_time", "total_time"} and isinstance(value, (int, float)) and not isinstance(
        value, bool
    ):
        return value
    return None


def _flatten_replicate_usage(raw: object) -> dict[str, object]:
    """Maps nested Replicate prediction payloads onto the Replicate whitelist."""
    if not isinstance(raw, Mapping):
        return {}
    flat: dict[str, object] = {}
    prediction_id = _replicate_scalar("prediction_id", raw.get("prediction_id"))
    if prediction_id is None:
        prediction_id = _replicate_scalar("prediction_id", raw.get("id"))
    if prediction_id is not None:
        flat["prediction_id"] = prediction_id

    metrics = raw.get("metrics")
    nested: Mapping[str, object] = metrics if isinstance(metrics, Mapping) else {}
    for key in ("predict_time", "total_time"):
        candidate = _replicate_scalar(key, raw.get(key))
        if candidate is None:
            candidate = _replicate_scalar(key, nested.get(key))
        if candidate is not None:
            flat[key] = candidate
    return flat


def usage_from_prediction(prediction: object) -> dict[str, object] | None:
    """Copies identity + metrics from a Replicate Prediction object (ADR-073)."""
    payload = {
        "id": getattr(prediction, "id", None),
        "metrics": getattr(prediction, "metrics", None),
    }
    flat = _flatten_replicate_usage(payload)
    return flat or None


class UsageAccountingService:
    """Normalizes provider usage into a UsageRecord.

    Never fabricates a numeric value where the provider is silent — absent
    usage is recorded as `unknown`, not zero. Whitelist is keyed by `provider`
    (ADR-074): OpenAI token fields and Replicate metrics do not contaminate
    each other. Callers that omit `provider` are treated as OpenAI so intent
    008 keeps working.
    """

    def normalize(
        self,
        model: str | None,
        raw_usage: Mapping[str, object] | None = None,
        *,
        provider: str = "openai",
    ) -> UsageRecord:
        identified = model.strip() if isinstance(model, str) and model.strip() else None
        if not isinstance(raw_usage, Mapping) or not raw_usage:
            return UsageRecord(status="unknown", model=identified, call_count=None, raw=None)

        if provider == "replicate":
            safe_raw = _flatten_replicate_usage(raw_usage)
            if not (
                identified
                and (
                    _informed(safe_raw.get("prediction_id"))
                    or _informed(safe_raw.get("predict_time"))
                )
            ):
                return UsageRecord(
                    status="unknown",
                    model=identified,
                    call_count=None,
                    raw=safe_raw or None,
                )
            return UsageRecord(
                status="reported", model=identified, call_count=1, raw=safe_raw
            )

        safe_raw = {
            k: v
            for k, v in raw_usage.items()
            if k in _SAFE_USAGE_FIELDS_OPENAI and _informed(v)
        }
        if not safe_raw:
            return UsageRecord(status="unknown", model=model, call_count=None, raw=None)
        return UsageRecord(status="reported", model=model, call_count=1, raw=safe_raw)
