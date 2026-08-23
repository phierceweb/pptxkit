"""Turn a slide's reveal groups into PowerPoint timing, and give it a transition.

Everything here runs after the last shape exists, because all of it needs shape ids. A
spec says how many beats an argument has; ``theme.motion`` says what a beat looks like.
"""

from __future__ import annotations

from pptxkit.errors import LayoutError
from pptxkit.layouts.components import RevealItem, shape_id
from pptxkit.layouts.registry import SlideCtx
from pptxkit.motion import (
    add_click_build,
    add_click_reveals,
    add_click_sequence,
    add_transition,
)
from pptxkit.spec.model import Placement

_CHART_ANIMATIONS = ("by_category", "by_series")
_ANIMATIONS = ("none", "together", "one_at_a_time", *_CHART_ANIMATIONS)


def apply_click_reveals(
    ctx: SlideCtx, drawn: list[tuple[Placement, list[list[RevealItem]]]]
) -> None:
    """Keep each ``reveals:`` placement hidden until the placement it names is clicked.

    A slide holds one timing tree, so this and the main-sequence build of ``animate:``
    are mutually exclusive.

    Raises:
        LayoutError: the slide also asks for ``animate:``, a ``reveals:`` names an id
            no placement carries or its own, or either end draws nothing revealable.
    """
    if ctx.spec.animate not in (None, "none"):
        raise LayoutError(
            f"slide {ctx.spec.index}: 'reveals:' and 'animate: {ctx.spec.animate}' "
            f"cannot share a slide — a slide carries one animation timeline, and "
            f"these are different kinds. Drop one."
        )
    shapes = {
        p.id: [shape_id(g) for group in made for g in group]
        for p, made in drawn
        if p.id is not None
    }
    pairs: list[tuple[int, int]] = []
    revealed: list[int] = []
    for placement, made in drawn:
        if not placement.reveals:
            continue
        where = f"slide {ctx.spec.index} ({placement.component})"
        if placement.reveals == placement.id:
            raise LayoutError(f"{where}: 'reveals: {placement.reveals}' names itself")
        if placement.reveals not in shapes:
            known = ", ".join(sorted(shapes)) or "none on this slide"
            raise LayoutError(
                f"{where}: 'reveals: {placement.reveals}' names no placement on this "
                f"slide; ids here: {known}"
            )
        trigger = shapes[placement.reveals]
        targets = [shape_id(g) for group in made for g in group]
        if not trigger or not targets:
            raise LayoutError(
                f"{where}: 'reveals:' needs both placements to draw something that can "
                f"be revealed, and one of them reported no shapes"
            )
        # Every shape the trigger placement drew listens: a card's plate is drawn
        # first and its words last, so wiring only the first leaves the words dead.
        pairs.extend((trig, target) for trig in trigger for target in targets)
        revealed.extend(targets)
    add_click_reveals(ctx.slide, pairs)
    ctx.manifest.record_animation("click_reveals", [[t] for t in revealed])


def apply_reveal(ctx: SlideCtx, groups: list[list[RevealItem]]) -> None:
    """Turn reveal groups into a PowerPoint click build.

    ``by_category``/``by_series`` are chart-only: the chart component emits its own
    ``<p:bldGraphic>`` and reports back empty groups, so empty groups here mean that
    build already happened. Non-empty groups with one of those values means some
    other component reached for chart vocabulary.
    """
    animate = ctx.spec.animate
    if animate is not None and animate not in _ANIMATIONS:
        raise LayoutError(
            f"slide {ctx.spec.index}: unknown animate {animate!r}; "
            f"expected one of {', '.join(_ANIMATIONS)}"
        )
    if animate in _CHART_ANIMATIONS and groups:
        raise LayoutError(
            f"slide {ctx.spec.index}: animate {animate!r} only applies to a native chart"
        )
    if animate is None or animate == "none" or not groups:
        return
    motion = ctx.theme.motion
    if animate == "together":
        # add_click_build fades everything; a role has nothing to say about a build
        # that gives every shape the same entrance.
        add_click_build(
            ctx.slide,
            [shape_id(g) for group in groups for g in group],
            motion.stagger_ms,
        )
    else:
        beat = motion.beat_ms if motion.advance == "after_previous" else None
        add_click_sequence(ctx.slide, _resolve_roles(ctx, groups), motion.stagger_ms, beat_ms=beat)
    ctx.manifest.record_animation(
        "click_build" if animate == "together" else "click_sequence", groups
    )


def _resolve_roles(ctx: SlideCtx, groups: list[list[RevealItem]]) -> list[list[RevealItem]]:
    """Turn each component's motion *role* into the theme's wire-format entrance.

    A component says "I am a line being drawn"; the theme decides that lines wipe, so
    neither the component nor the spec ever names an OOXML preset.

    Raises:
        LayoutError: a component reported a role the theme does not bind.
    """
    roles = ctx.theme.motion.roles
    resolved: list[list[RevealItem]] = []
    for group in groups:
        out: list[RevealItem] = []
        for item in group:
            if not isinstance(item, tuple):
                out.append(item)
                continue
            spid, role = item
            try:
                out.append((spid, roles[role]))
            except KeyError:
                raise LayoutError(
                    f"slide {ctx.spec.index}: component {ctx.component!r} reports "
                    f"motion role {role!r}, which the theme does not bind; known "
                    f"roles: {', '.join(sorted(roles))}"
                ) from None
        resolved.append(out)
    return resolved


def apply_transition(ctx: SlideCtx) -> None:
    """Give the slide the transition the show arrives on.

    Which transition is the theme's; a slide may only refuse it.

    Raises:
        LayoutError: the slide named anything other than ``none``.
    """
    asked = ctx.spec.transition
    if asked is not None and asked != "none":
        raise LayoutError(
            f"slide {ctx.spec.index}: transition {asked!r} — a slide may only say "
            f"'none', for a deliberate hard cut. Which transition a deck uses is the "
            f"theme's ('motion.transition'), so that every deck on the brand moves "
            f"the same way."
        )
    if asked == "none":
        return
    want = ctx.theme.motion.transition
    if want.kind == "none":
        return
    add_transition(ctx.slide, want.kind, direction=want.direction, speed=want.speed)
