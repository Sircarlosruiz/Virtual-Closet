import hashlib
import inspect

import pytest

from api.schemas.composition import OverlayAnchor, OverlayPlacement, OverlayStyle
from services import sku_renderer
from services.composition_spec import UnsupportedFontError, compute_spec_hash
from tests.test_sku_composition_service import make_base


def _placement(**overrides) -> OverlayPlacement:
    values = {"anchor": OverlayAnchor.bottom_right, "offset_x": 24, "offset_y": 24}
    values.update(overrides)
    return OverlayPlacement(**values)


def _style(**overrides) -> OverlayStyle:
    values = {"color": "#000000", "font_size": 48}
    values.update(overrides)
    return OverlayStyle(**values)


def test_render_is_byte_for_byte_deterministic():
    base = make_base()
    first = sku_renderer.render_composition(base, "REF: CAM-001", _placement(), _style())
    second = sku_renderer.render_composition(base, "REF: CAM-001", _placement(), _style())

    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_font_version_is_stable_and_rejects_unknown_families():
    assert sku_renderer.font_version("default") == sku_renderer.font_version("default")
    with pytest.raises(UnsupportedFontError):
        sku_renderer.font_version("comic-sans")


def test_evaluate_fit_accepts_then_rejects_by_available_area():
    size = sku_renderer.image_size_from_bytes(make_base(600, 800))

    accepted = sku_renderer.evaluate_fit(size, "REF: CAM-001", _placement(), _style())
    assert accepted["fits"] is True
    assert accepted["rendered_width"] <= accepted["available_width"]

    rejected = sku_renderer.evaluate_fit(
        size,
        "REF: CAM-001",
        _placement(max_width=5, max_height=5),
        _style(),
    )
    assert rejected["fits"] is False
    assert rejected["reason"]


def test_resolve_frame_honours_anchors():
    assert sku_renderer.resolve_frame((100, 100), _placement(offset_x=0, offset_y=0, anchor=OverlayAnchor.top_left), 10, 10) == (0, 0, 100, 100)
    assert sku_renderer.resolve_frame((100, 100), _placement(offset_x=5, offset_y=5), 10, 10) == (85, 85, 90, 90)
    assert sku_renderer.resolve_frame((100, 100), _placement(offset_x=5, offset_y=5, anchor=OverlayAnchor.center), 10, 10)[:2] == (45, 45)


def test_spec_hash_is_sensitive_to_every_pixel_input():
    baseline = compute_spec_hash("SKU", {}, {}, "a.png", "font-v1")
    font_changed = compute_spec_hash("SKU", {}, {}, "a.png", "font-v2")
    base_changed = compute_spec_hash("SKU", {}, {}, "b.png", "font-v1")

    assert len({baseline, font_changed, base_changed}) == 3


def test_composition_path_never_imports_a_provider():
    import services.sku_composition_service as service_module

    source = inspect.getsource(service_module) + inspect.getsource(sku_renderer)
    for token in ("image_generation_providers", "replicate", "openai", "LocalGPU"):
        assert token not in source
