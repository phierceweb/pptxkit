import pytest

from pptxkit.errors import ThemeError
from pptxkit.theme import Scale
from pptxkit.theme.model import TypeStyle


# --- rejection paths -------------------------------------------------------


def test_type_style_zero_rung_is_rejected():
    with pytest.raises(ThemeError, match="rung"):
        TypeStyle(rung=0, scale=Scale(13.333, 7.5))


def test_type_style_negative_rung_is_rejected():
    with pytest.raises(ThemeError, match="rung"):
        TypeStyle(rung=-1, scale=Scale(13.333, 7.5))


def test_the_canvas_types_are_not_reachable_through_the_model_module():
    """Grid and Scale live in theme.scale; the package __init__ is the only door."""
    from pptxkit.theme import model

    assert not hasattr(model, "Grid")
    assert not hasattr(model, "Scale")
