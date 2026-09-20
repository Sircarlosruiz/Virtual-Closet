from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.composition_spec import SKU_MAX_LENGTH, compute_spec_hash, normalize_sku
from services.image_generation.replicate_tryon_adapter import ReplicateTryOnAdapter
from services.usage_accounting_service import (
    UsageAccountingService,
    _flatten_replicate_usage,
    usage_from_prediction,
)


def test_should_report_replicate_usage_without_openai_tokens():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"prediction_id": "abc", "predict_time": 12.5},
        provider="replicate",
    )
    assert record.status == "reported"
    assert record.model == "zhengchong/catvton"
    assert record.call_count == 1
    assert record.raw == {"prediction_id": "abc", "predict_time": 12.5}


def test_should_flatten_nested_replicate_metrics_and_id_alias():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"id": "pred-1", "metrics": {"predict_time": 3.2, "total_time": 4.0}},
        provider="replicate",
    )
    assert record.status == "reported"
    assert record.raw == {
        "prediction_id": "pred-1",
        "predict_time": 3.2,
        "total_time": 4.0,
    }


def test_should_ignore_openai_token_fields_on_replicate_jobs():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"total_tokens": 99, "input_tokens": 10},
        provider="replicate",
    )
    assert record.status == "unknown"
    assert record.call_count is None
    assert record.raw is None or "total_tokens" not in (record.raw or {})


def test_should_ignore_replicate_fields_on_openai_jobs():
    record = UsageAccountingService().normalize(
        "gpt-image-1",
        {"predict_time": 1.2, "prediction_id": "x"},
        provider="openai",
    )
    assert record.status == "unknown"
    assert record.call_count is None


def test_should_keep_openai_token_normalization():
    record = UsageAccountingService().normalize(
        "gpt-image-1",
        {"total_tokens": 120, "input_tokens": 40, "mystery": 1},
    )
    assert record.status == "reported"
    assert record.raw == {"total_tokens": 120, "input_tokens": 40}


def test_should_not_fabricate_zero_for_missing_replicate_fields():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"prediction_id": "abc", "predict_time": None, "total_time": None},
        provider="replicate",
    )
    assert record.status == "reported"
    assert "predict_time" not in record.raw
    assert 0 not in (record.raw or {}).values()


def test_should_drop_unrecognized_replicate_keys():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"prediction_id": "abc", "logs": "secret", "input": {"prompt": "nope"}},
        provider="replicate",
    )
    assert record.status == "reported"
    assert record.raw == {"prediction_id": "abc"}


def test_should_mark_unknown_when_replicate_model_missing():
    record = UsageAccountingService().normalize(
        None,
        {"prediction_id": "abc", "predict_time": 1.0},
        provider="replicate",
    )
    assert record.status == "unknown"
    assert record.call_count is None


def test_should_mark_unknown_on_timeout_payload():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        None,
        provider="replicate",
    )
    assert record.status == "unknown"
    assert record.call_count is None
    assert record.raw is None


def test_should_mark_unknown_when_raw_usage_is_not_a_mapping():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        MagicMock(),
        provider="replicate",
    )
    assert record.status == "unknown"
    assert record.raw is None
    assert record.call_count is None


def test_should_drop_non_scalar_replicate_values():
    record = UsageAccountingService().normalize(
        "zhengchong/catvton",
        {"prediction_id": 123, "predict_time": True, "total_time": "slow"},
        provider="replicate",
    )
    assert record.status == "unknown"
    assert record.raw is None
    assert _flatten_replicate_usage(MagicMock()) == {}


def test_usage_from_prediction_copies_only_safe_fields():
    prediction = SimpleNamespace(
        id="pred-9",
        model="zhengchong/catvton",
        metrics={"predict_time": 8.1, "total_time": 9.0},
        logs="do-not-copy",
        input={"human_image": "data:..."},
        output="https://example.invalid/out.png",
    )
    usage = usage_from_prediction(prediction)
    assert usage == {
        "prediction_id": "pred-9",
        "predict_time": 8.1,
        "total_time": 9.0,
    }


@pytest.mark.asyncio
async def test_adapter_copies_inner_sidecar_onto_result_and_instance():
    inner = MagicMock()
    inner.generate = AsyncMock(return_value=b"image-bytes")
    inner.last_usage = {"prediction_id": "p1", "predict_time": 2.5}
    inner.last_model = "zhengchong/catvton"
    adapter = ReplicateTryOnAdapter(inner=inner, timeout_seconds=900)
    result = await adapter.generate(
        {
            "cloth_type": "upper_body",
            "garment_bytes": b"garment",
            "model_bytes": b"model",
        }
    )
    assert result.usage == {"prediction_id": "p1", "predict_time": 2.5}
    assert result.provider_model == "zhengchong/catvton"
    assert adapter.last_usage == result.usage
    assert adapter.last_model == "zhengchong/catvton"


@pytest.mark.asyncio
async def test_adapter_rejects_unsupported_cloth_type():
    from services.image_generation_providers import ProviderRequestError

    adapter = ReplicateTryOnAdapter(inner=MagicMock(), timeout_seconds=1)
    with pytest.raises(ProviderRequestError, match="cloth_type"):
        await adapter.generate(
            {"cloth_type": "hat", "garment_bytes": b"g", "model_bytes": b"m"}
        )


@pytest.mark.asyncio
async def test_adapter_wraps_inner_exception_as_provider_request():
    from services.image_generation_providers import ProviderRequestError

    inner = MagicMock()
    inner.generate = AsyncMock(side_effect=RuntimeError("boom"))
    adapter = ReplicateTryOnAdapter(inner=inner, timeout_seconds=5)
    with pytest.raises(ProviderRequestError, match="Replicate try-on failed"):
        await adapter.generate(
            {"cloth_type": "upper", "garment_bytes": b"g", "model_bytes": b"m"}
        )


@pytest.mark.asyncio
async def test_adapter_decodes_base64_inputs():
    inner = MagicMock()
    inner.generate = AsyncMock(return_value=b"out")
    inner.last_usage = None
    inner.last_model = None
    adapter = ReplicateTryOnAdapter(inner=inner, timeout_seconds=5)
    result = await adapter.generate(
        {
            "cloth_type": "upper",
            "garment_bytes": "Zg==",
            "model_bytes": "bQ==",
        }
    )
    inner.generate.assert_awaited_once_with(b"f", b"m", "upper")
    assert result.image_bytes == b"out"
    assert result.usage is None


@pytest.mark.asyncio
async def test_catvton_hook_sets_sidecar_from_prediction(monkeypatch):
    """Load CatVTON without `services.vton.__init__` (that package pulls OpenCV)."""
    import importlib.util
    import sys
    import types
    from pathlib import Path

    from core.config import settings

    vton_dir = Path(__file__).resolve().parents[1] / "services" / "vton"
    keys = (
        "services.vton",
        "services.vton.base",
        "services.vton.catvton_replicate_provider",
    )
    saved = {key: sys.modules.get(key) for key in keys}

    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-test")
    monkeypatch.setattr(settings, "CATVTON_REPLICATE_MODEL", "zhengchong/catvton")

    try:
        pkg = types.ModuleType("services.vton")
        pkg.__path__ = [str(vton_dir)]
        pkg.__package__ = "services.vton"
        sys.modules["services.vton"] = pkg

        def _load(modname: str, filename: str):
            spec = importlib.util.spec_from_file_location(modname, vton_dir / filename)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[modname] = mod
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            return mod

        _load("services.vton.base", "base.py")
        catvton_mod = _load(
            "services.vton.catvton_replicate_provider",
            "catvton_replicate_provider.py",
        )

        prediction = SimpleNamespace(
            id="pred-hook",
            model="zhengchong/catvton",
            metrics={"predict_time": 7.5, "total_time": 8.0},
            output="https://example.invalid/out.png",
            wait=lambda: None,
        )
        fake_client = MagicMock()
        fake_client.predictions.create.return_value = prediction
        monkeypatch.setattr(catvton_mod.replicate, "Client", lambda api_token: fake_client)

        class _Resp:
            content = b"png-bytes"

            def raise_for_status(self):
                return None

        class _Http:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, url):
                assert url == "https://example.invalid/out.png"
                return _Resp()

        monkeypatch.setattr(catvton_mod.httpx, "AsyncClient", lambda timeout: _Http())

        provider = catvton_mod.CatVTONReplicateProvider()
        out = await provider.generate(b"g", b"m", "upper")
        assert out == b"png-bytes"
        assert provider.last_usage == {
            "prediction_id": "pred-hook",
            "predict_time": 7.5,
            "total_time": 8.0,
        }
        assert provider.last_model == "zhengchong/catvton"
    finally:
        for key, previous in saved.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous


def test_hyphenated_slug_normalizes_and_enters_spec_hash():
    slug = "blusa-manga-globo-estampada-verano"
    assert len(slug) > 30
    assert len(slug) <= SKU_MAX_LENGTH
    normalized = normalize_sku(slug)
    assert normalized == slug
    hashed = compute_spec_hash(normalized, {"anchor": "bottom-right"}, {}, "base.png", "font-v1")
    other = compute_spec_hash(
        "otra-blusa", {"anchor": "bottom-right"}, {}, "base.png", "font-v1"
    )
    assert hashed != other
