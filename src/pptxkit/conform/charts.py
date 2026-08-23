"""Every creatable chart kind, with the data shape each one demands."""

from __future__ import annotations

from typing import Any

from pptxkit.charts.model import _BUBBLE_CHART_TYPES, _XY_CHART_TYPES
from pptxkit.charts.native import _CHART_TYPES

CATEGORY_ROWS: list[dict[str, Any]] = [
    {"category": "Q1", "value": 12},
    {"category": "Q2", "value": 34},
    {"category": "Q3", "value": 58},
    {"category": "Q4", "value": 91},
]
_XY_ROWS = [{"x": 1, "y": 12}, {"x": 2, "y": 34}, {"x": 3, "y": 58}, {"x": 4, "y": 91}]
_BUBBLE_ROWS = [
    {"x": 1, "y": 12, "size": 4},
    {"x": 2, "y": 34, "size": 9},
    {"x": 3, "y": 58, "size": 6},
]


def chart_slides() -> dict[str, dict[str, Any]]:
    """Every exercise in this family, keyed by name."""
    out = {}
    for kind in sorted(_CHART_TYPES):
        rows = (
            _BUBBLE_ROWS
            if kind in _BUBBLE_CHART_TYPES
            else _XY_ROWS
            if kind in _XY_CHART_TYPES
            else CATEGORY_ROWS
        )
        out[f"chart-{kind}"] = {
            "title": f"A {kind} chart",
            "place": [
                {
                    "at": {"cols": "full", "rows": {"from": 0, "to": 9}},
                    "chart": {"kind": kind, "data": [dict(r) for r in rows]},
                }
            ],
        }
    return out
