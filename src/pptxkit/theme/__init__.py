"""Theme loading: the built-in design system, optionally specialized into a template."""

from pptxkit.theme.chartstyle import ChartStyle
from pptxkit.theme.defaults import (
    DEFAULT_PALETTE,
    DEFAULT_RAMP,
    DEFAULT_ROLES,
    blank_presentation,
    default_theme,
)
from pptxkit.theme.load import load_theme
from pptxkit.theme.model import Theme, TypeStyle
from pptxkit.theme.palette import Pair, Palette, build_palette
from pptxkit.theme.scale import Grid, Scale

__all__ = [
    "DEFAULT_PALETTE",
    "DEFAULT_RAMP",
    "DEFAULT_ROLES",
    "ChartStyle",
    "Grid",
    "Pair",
    "Palette",
    "Scale",
    "Theme",
    "TypeStyle",
    "blank_presentation",
    "build_palette",
    "default_theme",
    "load_theme",
]
