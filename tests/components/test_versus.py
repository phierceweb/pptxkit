"""What a successful `versus` build never reaches."""

from __future__ import annotations

import pytest

import pptxkit.components  # noqa: F401 — registers the built-ins
from pptxkit.errors import LayoutError
from pptxkit.layouts.components import get_component

LEFT = {"value": "2 days", "label": "by post"}
RIGHT = {"value": "4 hours", "label": "collected in person", "highlight": True}


def _ctx(ctx_factory, **body):
    return ctx_factory({"versus": {"left": LEFT, "right": RIGHT, **body}})


def test_the_glyph_is_inside_a_reveal_group(ctx_factory):
    """Outside every group it hangs between two plates that have not arrived yet."""
    ctx = _ctx(ctx_factory)
    groups = get_component("versus")(ctx).groups
    grouped = {spid for group in groups for spid in group}
    glyphs = [s.shape_id for s in ctx.slide.shapes if s.name.startswith("Icon ")]
    assert glyphs, "no glyph was drawn, so this proves nothing"
    assert set(glyphs) <= grouped


def test_one_reveal_group_per_side(ctx_factory):
    assert len(get_component("versus")(_ctx(ctx_factory)).groups) == 2


def test_the_highlighted_side_is_painted_in_the_accent(ctx_factory):
    """Without this the two plates are indistinguishable and the pair states nothing."""
    ctx = _ctx(ctx_factory)
    get_component("versus")(ctx)
    plates = sorted((s for s in ctx.slide.shapes if not s.text_frame.text), key=lambda s: s.left)
    fills = [s.fill.fore_color.rgb for s in plates if s.fill.type is not None]
    accent = ctx.theme.palette.role("accent-1")
    assert str(fills[-1]) == accent, (fills, accent)
    assert str(fills[0]) != accent


def test_a_side_needs_a_value_and_a_label(ctx_factory):
    ctx = ctx_factory({"versus": {"left": {"value": "1"}, "right": RIGHT}})
    with pytest.raises(LayoutError, match=r"'left' needs a 'value' and a 'label'"):
        get_component("versus")(ctx)


def test_a_missing_side_names_it(ctx_factory):
    ctx = ctx_factory({"versus": {"left": LEFT}})
    with pytest.raises(LayoutError, match=r"'right' needs a 'value' and a 'label'"):
        get_component("versus")(ctx)


def test_an_unknown_side_key_is_refused(ctx_factory):
    ctx = ctx_factory({"versus": {"left": {**LEFT, "colour": "red"}, "right": RIGHT}})
    with pytest.raises(LayoutError, match=r"has the unknown field 'colour'"):
        get_component("versus")(ctx)


def test_highlighting_both_sides_is_refused(ctx_factory):
    ctx = ctx_factory({"versus": {"left": {**LEFT, "highlight": True}, "right": RIGHT}})
    with pytest.raises(LayoutError, match=r"both sides set 'highlight'"):
        get_component("versus")(ctx)


def test_every_returned_id_is_a_real_shape(ctx_factory):
    ctx = _ctx(ctx_factory)
    groups = get_component("versus")(ctx).groups
    ids = {s.shape_id for s in ctx.slide.shapes}
    assert all(spid in ids for group in groups for spid in group)


def test_versus_is_registered():
    from pptxkit.layouts.components import registered_components

    assert "versus" in registered_components()
