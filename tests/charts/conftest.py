"""Fixtures for chart-renderer tests — built directly, not via ``from_body``."""

from __future__ import annotations

import pytest

from pptxkit.charts.model import Annotation, ChartSpec, Series


@pytest.fixture
def chart_spec() -> ChartSpec:
    return ChartSpec(
        type="bar",
        categories=("Q1", "Q2"),
        series=(Series(name="Revenue", values=(12.0, 34.0)),),
    )


@pytest.fixture
def chart_spec_highlighted() -> ChartSpec:
    return ChartSpec(
        type="bar",
        categories=("Q1", "Q2"),
        series=(Series(name="Revenue", values=(12.0, 34.0)),),
        highlight=1,
    )


@pytest.fixture
def spec_1_2_4() -> ChartSpec:
    """Three categories, values 1/2/4 — an exact 1:2:4 ratio for proportionality checks."""
    return ChartSpec(
        type="column",
        categories=("Q1", "Q2", "Q3"),
        series=(Series(name="Value", values=(1.0, 2.0, 4.0)),),
    )


@pytest.fixture
def spec_annotated() -> ChartSpec:
    """A column chart whose last point is both highlighted and annotated."""
    return ChartSpec(
        type="column",
        categories=("Q1", "Q2", "Q3", "Q4"),
        series=(Series(name="Adoption", values=(12.0, 34.0, 58.0, 91.0), unit="%"),),
        highlight=3,
        annotate=Annotation(
            index=3, title="+33 pts in one quarter", detail="after the skills rollout"
        ),
    )
