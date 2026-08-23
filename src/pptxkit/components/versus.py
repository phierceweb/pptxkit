"""Two magnitudes either side of a glyph — a before and an after, or a this and a that.

The glyph makes the pair read as one comparison rather than two facts; `highlight` says
which side the slide is arguing for.
"""

from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from pptxkit.errors import LayoutError
from pptxkit.icons.draw import place_icon
from pptxkit.layouts.components import BodyResult, RevealItem, component
from pptxkit.layouts.registry import SlideCtx
from pptxkit.theme.model import Rect
from pptxkit.utils.shapes import para, rrect, textbox

from pptxkit.components._shape import known_fields, known_item_fields

_FIELDS = ("left", "right", "icon")
_SIDE_FIELDS = frozenset({"value", "label", "note", "highlight"})

_ICON_DEFAULT = "schedule"
_MIDDLE = 1.05
_GLYPH_SIDE = 0.66
_INSET = 0.24
_RADIUS = 0.05
# The stat rung is sized for a tile that fills its placement; a side here also carries a
# label and sometimes a note, so the number gives a little back.
_VALUE_SCALE = 0.86


def _side(ctx: SlideCtx, key: str) -> dict:
    raw = ctx.body.get(key)
    if not isinstance(raw, dict) or "value" not in raw or "label" not in raw:
        raise LayoutError(
            f"slide {ctx.spec.index} (component 'versus'): {key!r} needs a 'value' and "
            f"a 'label' — a versus is two named magnitudes"
        )
    known_item_fields(ctx, raw, _SIDE_FIELDS, noun=key)
    return raw


@component("versus")
def versus(ctx: SlideCtx) -> BodyResult:
    """Two plates and the glyph between them; one reveal group per side."""
    # Both plates fill the placement and centre their own type, so neither key can act.
    for key, value in (("align", ctx.align), ("anchor", ctx.anchor)):
        if value != ("left" if key == "align" else "top"):
            raise LayoutError(
                f"slide {ctx.spec.index} (component 'versus'): {key} {value!r} has "
                f"nothing to act on — a versus fills its placement and sets its own "
                f"type; drop the {key}, or bound the placement with 'rows:'"
            )
    known_fields(ctx, _FIELDS)
    sides = (_side(ctx, "left"), _side(ctx, "right"))
    if all(s.get("highlight") for s in sides):
        raise LayoutError(
            f"slide {ctx.spec.index} (component 'versus'): both sides set 'highlight' — "
            f"it marks the one the slide is arguing for, so only one side takes it"
        )
    glyph = str(ctx.body.get("icon", _ICON_DEFAULT))
    r = ctx.body_rect
    half = (r.width - _MIDDLE) / 2
    if half < 1.2:
        raise LayoutError(
            f"slide {ctx.spec.index} (component 'versus'): each side gets {half:.2f}in "
            f"across — widen the placement"
        )

    stat, body, caption = ctx.style("stat"), ctx.style("body"), ctx.style("caption")
    groups: list[list[RevealItem]] = []

    for side, x in zip(sides, (r.left, r.left + half + _MIDDLE), strict=True):
        role = "accent-1" if side.get("highlight") else "muted"
        fill_hex = ctx.theme.palette.role(role)
        plate = rrect(ctx.slide, x, r.top, half, r.height, ctx.color(role), radius=_RADIUS)
        ctx.manifest.record(plate)
        # The plate is its own surface: the type has to read on it, not on the slide.
        ink = ctx.rgb(ctx.ink_on(fill_hex))
        tf = textbox(
            ctx.slide, x + _INSET, r.top, half - 2 * _INSET, r.height, anchor=MSO_ANCHOR.MIDDLE
        )
        para(
            tf,
            str(side["value"]),
            stat.size * _VALUE_SCALE,
            ink,
            bold=True,
            align=PP_ALIGN.CENTER,
            first=True,
            space_after=2,
            font=ctx.theme.font_for(stat),
        )
        para(
            tf,
            str(side["label"]),
            body.size,
            ink,
            align=PP_ALIGN.CENTER,
            space_after=0,
            font=ctx.theme.face,
        )
        if side.get("note"):
            para(
                tf,
                str(side["note"]),
                caption.size,
                ink,
                align=PP_ALIGN.CENTER,
                space_after=0,
                font=ctx.theme.face,
            )
        recorded = [str(side["value"]), str(side["label"])]
        sizes = [stat.size * _VALUE_SCALE, body.size]
        if side.get("note"):
            recorded.append(str(side["note"]))
            sizes.append(caption.size)
        ctx.manifest.record(
            tf._parent,
            lines=recorded,
            font_pt=body.size,
            line_pt=sizes,
            fg=ctx.ink_on(fill_hex),
            bg=fill_hex,
        )
        groups.append([plate.shape_id, tf._parent.shape_id])

    mark = place_icon(
        ctx.slide,
        glyph,
        Rect(
            r.left + half + (_MIDDLE - _GLYPH_SIDE) / 2,
            r.top + (r.height - _GLYPH_SIDE) / 2,
            _GLYPH_SIDE,
            _GLYPH_SIDE,
        ),
        # The slide pair's ink, not the 'ink' role: the glyph sits on the background
        # between the plates, and on 'inverse' the role is near-invisible there.
        fill=ctx.pair.fg,
        theme=ctx.theme,
    )
    ctx.manifest.record(mark)
    # The glyph joins the first side's group: left outside every group it would be on
    # screen from the first beat, hanging between two plates that have not arrived.
    groups[0].append(mark.shape_id)
    return BodyResult(groups=groups, height=r.height)
