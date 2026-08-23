"""Render a chart body as a real OOXML chart."""

from __future__ import annotations

from pptxkit.errors import LayoutError
from pptxkit.charts._kinds import _BUILDABLE_BY_CATEGORY
from pptxkit.charts.model import ChartSpec
from pptxkit.charts.native import add_native_chart
from pptxkit.layouts.components import BodyResult, component
from pptxkit.layouts.registry import SlideCtx
from pptxkit.motion import add_chart_build

from pptxkit.components._shared import require_default_align

_EMU_PER_INCH = 914400

# Slide-level animate -> add_chart_build's 'by'. Any other component asking for
# these is rejected by layouts/compose.py instead.
_CHART_ANIMATIONS = {"by_category": "category", "by_series": "series"}


@component("chart")
def chart(ctx: SlideCtx) -> BodyResult:
    """Place ``ctx.body`` (the slide's ``chart:`` mapping) as a native chart.

    Native charts embed real text a PDF extractor can read, so they're
    recorded ``rendered="native"``.
    """
    require_default_align(ctx)
    spec = ChartSpec.from_body(ctx, ctx.body)
    rect = ctx.body_rect
    animate = ctx.spec.animate

    frame = add_native_chart(ctx, spec, rect)
    ctx.manifest.record(frame, rendered="native")
    height = frame.height / _EMU_PER_INCH
    if animate in _CHART_ANIMATIONS:
        by = _CHART_ANIMATIONS[animate]
        if by == "category" and spec.type not in _BUILDABLE_BY_CATEGORY:
            raise LayoutError(
                f"slide {ctx.spec.index} (component 'chart'): a {spec.type!r} chart "
                f"cannot build by category — its categories are vertices of one "
                f"outline, not separate marks, so the build would be a click per "
                f"category with nothing to show. Use 'animate: together', or a kind "
                f"that builds: {', '.join(sorted(_BUILDABLE_BY_CATEGORY))}"
            )
        parts = len(spec.series) if by == "series" else len(spec.categories)
        add_chart_build(ctx.slide, frame.shape_id, by=by, parts=parts)
        ctx.manifest.record_animation("chart_build", [[frame.shape_id]])
        return BodyResult(groups=[], height=height)
    return BodyResult(groups=[[frame.shape_id]], height=height)
