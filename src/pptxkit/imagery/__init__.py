"""Placing photographs: how a source fits a box, and what its pixels do to text on it."""

from pptxkit.imagery.backdrop import Backdrop
from pptxkit.imagery.draw import place_picture, paint_scrim
from pptxkit.imagery.fit import FITS, MASKS, ImageFit, fit_image, parse_aspect, square
from pptxkit.imagery.paint import paint_backdrop
from pptxkit.imagery.sample import cells, composite, effective_bg, solve_alpha, weakest
from pptxkit.imagery.scrim import Scrim, ScrimSpec, scrim_spec

__all__ = [
    "Backdrop",
    "FITS",
    "ImageFit",
    "MASKS",
    "Scrim",
    "ScrimSpec",
    "cells",
    "composite",
    "effective_bg",
    "fit_image",
    "paint_backdrop",
    "paint_scrim",
    "parse_aspect",
    "place_picture",
    "scrim_spec",
    "solve_alpha",
    "square",
    "weakest",
]
