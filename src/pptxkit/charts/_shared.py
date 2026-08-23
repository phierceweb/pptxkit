"""Pure, theme-driven computations for chart rendering."""

from __future__ import annotations

from pptx.dml.color import RGBColor

_GRADIENT_LIGHTEN_FRACTION = 0.28  # how far toward white the second gradient stop sits


# The units that read before the number. Everything else is a suffix.
_PREFIX_UNITS = frozenset({"$", "£", "€", "¥", "₹"})


def label_number_format(unit: str | None, *, thousands_sep: bool) -> str | None:
    """The Excel number-format code for data labels, or ``None`` to leave the default.

    ``unit`` is quoted literally (``0"%"``) rather than Excel's ``%`` code, which
    multiplies the value by 100.
    """
    if not unit and not thousands_sep:
        return None
    digits = "#,##0" if thousands_sep else "0"
    if not unit:
        return digits
    if unit in _PREFIX_UNITS:
        return f'"{unit}"{digits}'
    return f'{digits}"{unit}"'


def lighten(color: RGBColor, fraction: float = _GRADIENT_LIGHTEN_FRACTION) -> RGBColor:
    """Blend ``color`` toward white by ``fraction`` — keeps a gradient reading
    as one hue with depth rather than two colours."""
    return RGBColor(*(round(c + (255 - c) * fraction) for c in color))
