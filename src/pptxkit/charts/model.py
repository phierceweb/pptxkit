"""ChartSpec: a validated, renderer-agnostic description of one chart body.

A malformed spec is caught here, naming the slide, rather than surfacing as an
``IndexError`` deep inside a renderer. Wire format: ``docs/authoring.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, cast

from pptxkit.charts._kinds import (
    _ANNOTATE_KEYS,
    _BUBBLE_CHART_TYPES,
    _BUBBLE_ROW_KEYS,
    _CATEGORY_ROW_KEYS,
    _CHART_KEYS,
    _HIGHLIGHTABLE_KINDS,
    _LEGACY_CHART_KEYS,
    _TYPES,
    _XY_CHART_TYPES,
    _XY_ROW_KEYS,
)
from pptxkit.errors import LayoutError
from pptxkit.utils.keys import unknown_field

if TYPE_CHECKING:
    from pptxkit.layouts.registry import SlideCtx


def _shape(chart_type: str) -> str:
    """'category' (values, one per category), 'xy' (x, y), or 'bubble' (x, y, size)."""
    if chart_type in _XY_CHART_TYPES:
        return "xy"
    if chart_type in _BUBBLE_CHART_TYPES:
        return "bubble"
    return "category"


@dataclass(frozen=True)
class Series:
    """One named run of data: ``values`` (one per category) or ``points`` (xy/bubble) —
    exactly one, depending on the chart's data shape."""

    name: str
    values: tuple[float, ...] | None = None
    points: tuple[tuple[float, ...], ...] | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Annotation:
    """A callout pointing at one category."""

    index: int
    title: str
    detail: str


@dataclass(frozen=True)
class ChartSpec:
    """A validated chart body: categories and one or more series."""

    type: str
    categories: tuple[str, ...]
    series: tuple[Series, ...]
    highlight: int | None = None
    annotate: Annotation | None = None
    y_min: float | None = None
    y_max: float | None = None

    def __post_init__(self) -> None:
        """Backstop for directly constructed specs, so none reaches a renderer
        structurally inconsistent. ``from_body`` always raises first.
        """
        if self.type not in _TYPES:
            raise LayoutError(f"'type' must be one of {', '.join(_TYPES)}, got {self.type!r}")
        shape = _shape(self.type)
        if not self.series:
            raise LayoutError("'series' must be non-empty")
        for s in self.series:
            if not isinstance(s, Series):
                raise LayoutError(f"every series must be a Series instance, got {s!r}")

        if shape == "category":
            if not self.categories:
                raise LayoutError("'categories' must be non-empty")
            for s in self.series:
                if s.points is not None:
                    raise LayoutError(
                        f"series {s.name!r} carries 'points' but chart type {self.type!r} is "
                        f"category-shaped; use 'values'"
                    )
                if s.values is None:
                    raise LayoutError(
                        f"series {s.name!r} needs 'values' for chart type {self.type!r}"
                    )
                if len(s.values) != len(self.categories):
                    raise LayoutError(
                        f"series {s.name!r} has {len(self.categories)} categories but "
                        f"{len(s.values)} value(s)"
                    )
            n_points = len(self.categories)
        else:
            if self.categories:
                raise LayoutError(f"chart type {self.type!r} takes 'points', not 'categories'")
            width = 2 if shape == "xy" else 3
            kind = "(x, y) pair" if shape == "xy" else "(x, y, size) triple"
            for s in self.series:
                if s.values is not None:
                    raise LayoutError(
                        f"series {s.name!r} carries 'values' but chart type {self.type!r} is "
                        f"{shape}-shaped; use 'points'"
                    )
                if not s.points:
                    raise LayoutError(
                        f"series {s.name!r} needs 'points' for chart type {self.type!r}"
                    )
                for i, p in enumerate(s.points):
                    if len(p) != width:
                        raise LayoutError(
                            f"series {s.name!r} point {i} must be a {kind}, got {p!r}"
                        )
                    if shape == "bubble" and p[2] <= 0:
                        raise LayoutError(
                            f"series {s.name!r} point {i} has a non-positive bubble size: {p[2]!r}"
                        )
            n_points = len(cast("tuple[tuple[float, ...], ...]", self.series[0].points))

        if self.highlight is not None and not 0 <= self.highlight < n_points:
            noun = "categories" if shape == "category" else "points"
            raise LayoutError(
                f"'highlight' index {self.highlight} is out of range for {n_points} {noun}"
            )
        if self.annotate is not None:
            if not isinstance(self.annotate, Annotation):
                raise LayoutError(
                    f"'annotate' must be an Annotation instance, got {self.annotate!r}"
                )
            if not 0 <= self.annotate.index < len(self.categories):
                raise LayoutError(
                    f"'annotate' index {self.annotate.index} is out of range for "
                    f"{len(self.categories)} categories"
                )

    @classmethod
    def from_body(cls, ctx: SlideCtx, body: dict[str, Any]) -> ChartSpec:
        """Validate and build a ``ChartSpec`` from a chart body block.

        Raises ``LayoutError`` naming the slide and the offending field for every
        malformed value — the caller's raw dict never reaches a renderer unvalidated.
        """
        where = f"slide {ctx.spec.index} (component 'chart')"
        if not isinstance(body, dict):
            raise LayoutError(f"{where}: body must be a mapping, got {body!r}")

        for legacy_key, hint in _LEGACY_CHART_KEYS.items():
            if legacy_key in body:
                raise LayoutError(f"{where}: {hint}")

        unknown = sorted(set(body) - set(_CHART_KEYS))
        if unknown:
            raise LayoutError(unknown_field(unknown[0], _CHART_KEYS, where=where))

        chart_kind = str(body.get("kind", ""))
        if chart_kind not in _TYPES:
            raise LayoutError(
                f"{where}: 'kind' must be one of {', '.join(_TYPES)}, got {chart_kind!r}"
            )
        shape = _shape(chart_kind)

        rows = body.get("data")
        if not isinstance(rows, list) or not rows:
            raise LayoutError(f"{where}: 'data' must be a non-empty list of rows")

        if shape == "category":
            unit = body.get("unit")
            unit = None if unit is None else str(unit)
            categories, series, highlight = _parse_category_rows(where, rows, chart_kind, unit)
        else:
            categories, series, highlight = _parse_point_rows(where, rows, chart_kind, shape)

        annotate = _coerce_annotation(where, body.get("annotate"), limit=len(categories))
        y_min = _coerce_optional_float(where, body, "y_min")
        y_max = _coerce_optional_float(where, body, "y_max")

        if highlight is not None and chart_kind not in _HIGHLIGHTABLE_KINDS:
            raise LayoutError(
                f"{where}: chart kind {chart_kind!r} cannot show 'highlight' — its data points "
                f"have no fill of their own. Kinds that can: "
                f"{', '.join(sorted(_HIGHLIGHTABLE_KINDS))}"
            )
        return cls(
            type=chart_kind,
            categories=categories,
            series=series,
            highlight=highlight,
            annotate=annotate,
            y_min=y_min,
            y_max=y_max,
        )


def _row_is_highlighted(where: str, ref: str, row: dict) -> bool:
    raw = row.get("highlight", False)
    if not isinstance(raw, bool):
        raise LayoutError(f"{where}: {ref} 'highlight' must be true or false, got {raw!r}")
    return raw


def _parse_category_rows(
    where: str, rows: list, chart_kind: str, unit: str | None = None
) -> tuple[tuple[str, ...], tuple[Series, ...], int | None]:
    """One row per category: ``{category, values|value, highlight?}``. Series names
    and order come from the first row's ``values`` keys; every row after it must
    carry exactly that set."""
    categories: list[str] = []
    single_values: list[float] = []
    multi_values: list[dict[str, float]] = []
    mode: str | None = None
    first_ref: str | None = None
    master_order: list[str] | None = None
    highlight_index: int | None = None
    highlight_ref: str | None = None

    for i, row in enumerate(rows):
        pos = f"row {i + 1}"
        if not isinstance(row, dict):
            raise LayoutError(f"{where}: {pos} must be a mapping, got {row!r}")
        if "x" in row or "y" in row:
            raise LayoutError(
                f"{where}: {pos} carries 'x'/'y' but chart kind {chart_kind!r} is "
                f"category-shaped; use 'category' and 'values'"
            )
        unknown = sorted(set(row) - set(_CATEGORY_ROW_KEYS))
        if unknown:
            raise LayoutError(
                unknown_field(
                    unknown[0], _CATEGORY_ROW_KEYS, where=where, lead=f"{pos} has unknown field"
                )
            )
        if "category" not in row:
            raise LayoutError(f"{where}: {pos} needs a 'category'")
        category = str(row["category"])
        ref = f"{pos} (category {category!r})"

        has_value, has_values = "value" in row, "values" in row
        if has_value and has_values:
            raise LayoutError(f"{where}: {ref} carries both 'value' and 'values' — use one")
        if not has_value and not has_values:
            raise LayoutError(f"{where}: {ref} needs a 'value' or 'values'")
        row_mode = "single" if has_value else "multi"
        if mode is None:
            mode, first_ref = row_mode, ref
        elif row_mode != mode:
            this_key = "value" if row_mode == "single" else "values"
            first_key = "value" if mode == "single" else "values"
            raise LayoutError(
                f"{where}: {ref} uses {this_key!r} but {first_ref} uses {first_key!r} — "
                f"use one or the other for the whole chart"
            )

        if _row_is_highlighted(where, ref, row):
            if highlight_index is not None:
                raise LayoutError(
                    f"{where}: only one row may set 'highlight: true' — {highlight_ref} and "
                    f"{ref} both do"
                )
            highlight_index, highlight_ref = i, ref

        categories.append(category)
        if mode == "single":
            single_values.append(_coerce_row_number(where, ref, "value", row["value"]))
        else:
            values_raw = row["values"]
            if not isinstance(values_raw, dict) or not values_raw:
                raise LayoutError(
                    f"{where}: {ref} 'values' must be a non-empty mapping of series name "
                    f"to number, got {values_raw!r}"
                )
            if master_order is None:
                master_order = list(values_raw.keys())
            else:
                missing = [n for n in master_order if n not in values_raw]
                if missing:
                    raise LayoutError(
                        f"{where}: {ref} is missing series {missing[0]!r} (present in {first_ref})"
                    )
                extra = [n for n in values_raw if n not in master_order]
                if extra:
                    raise LayoutError(
                        f"{where}: {ref} has series {extra[0]!r}, which no other row defines; "
                        f"known series: {', '.join(master_order)}"
                    )
            multi_values.append(
                {name: _coerce_series_value(where, ref, name, v) for name, v in values_raw.items()}
            )

    series: tuple[Series, ...]
    if mode == "single":
        series = (Series(name="", values=tuple(single_values), unit=unit),)
    else:
        series = tuple(
            Series(name=name, values=tuple(row[name] for row in multi_values), unit=unit)
            for name in master_order or ()
        )
    return tuple(categories), series, highlight_index


def _parse_point_rows(
    where: str, rows: list, chart_kind: str, shape: str
) -> tuple[tuple[str, ...], tuple[Series, ...], int | None]:
    """One row per point: ``{x, y, size?, highlight?}`` — xy/bubble charts have no
    categories, so every row folds into a single unnamed series."""
    allowed = _BUBBLE_ROW_KEYS if shape == "bubble" else _XY_ROW_KEYS
    points: list[tuple[float, ...]] = []
    highlight_index: int | None = None
    highlight_ref: str | None = None

    for i, row in enumerate(rows):
        ref = f"row {i + 1}"
        if not isinstance(row, dict):
            raise LayoutError(f"{where}: {ref} must be a mapping, got {row!r}")
        if "category" in row:
            raise LayoutError(
                f"{where}: {ref} carries 'category' but chart kind {chart_kind!r} takes "
                f"'x'/'y', not 'category'"
            )
        unknown = sorted(set(row) - set(allowed))
        if unknown:
            raise LayoutError(
                unknown_field(unknown[0], allowed, where=where, lead=f"{ref} has unknown field")
            )
        if "x" not in row:
            raise LayoutError(f"{where}: {ref} needs an 'x'")
        if "y" not in row:
            raise LayoutError(f"{where}: {ref} needs a 'y'")
        if shape == "bubble" and "size" not in row:
            raise LayoutError(f"{where}: {ref} needs 'size' for chart kind {chart_kind!r}")

        if _row_is_highlighted(where, ref, row):
            if highlight_index is not None:
                raise LayoutError(
                    f"{where}: only one row may set 'highlight: true' — {highlight_ref} and "
                    f"{ref} both do"
                )
            highlight_index, highlight_ref = i, ref

        x = _coerce_row_number(where, ref, "x", row["x"])
        y = _coerce_row_number(where, ref, "y", row["y"])
        if shape == "bubble":
            size = _coerce_row_number(where, ref, "size", row["size"])
            if size <= 0:
                raise LayoutError(f"{where}: {ref} has a non-positive bubble size: {size!r}")
            points.append((x, y, size))
        else:
            points.append((x, y))

    return (), (Series(name="", points=tuple(points)),), highlight_index


def _coerce_row_number(where: str, ref: str, field: str, raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError) as e:
        raise LayoutError(f"{where}: {ref} has a non-numeric {field!r}: {raw!r}") from e


def _coerce_series_value(where: str, ref: str, name: str, raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError) as e:
        raise LayoutError(f"{where}: {ref} series {name!r} has a non-numeric value: {raw!r}") from e


def _coerce_annotation(where: str, raw: Any, *, limit: int) -> Annotation | None:
    """Parse ``annotate: {at, title, detail}`` — ``at`` is the wire key (spec
    ``index`` is only the dataclass attribute.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise LayoutError(f"{where}: 'annotate' must be a mapping, got {raw!r}")
    unknown = sorted(set(raw) - set(_ANNOTATE_KEYS))
    if unknown:
        raise LayoutError(
            unknown_field(
                unknown[0], _ANNOTATE_KEYS, where=where, lead="'annotate' has unknown field"
            )
        )
    missing = [k for k in _ANNOTATE_KEYS if k not in raw]
    if missing:
        raise LayoutError(f"{where}: 'annotate' is missing {missing[0]!r}")
    try:
        index = int(raw["at"])
    except (TypeError, ValueError) as e:
        raise LayoutError(f"{where}: 'annotate.at' must be an int, got {raw['at']!r}") from e
    if not 0 <= index < limit:
        raise LayoutError(
            f"{where}: 'annotate' index {index} is out of range for {limit} categories"
        )
    return Annotation(index=index, title=str(raw["title"]), detail=str(raw["detail"]))


def _coerce_optional_float(where: str, body: dict, key: str) -> float | None:
    raw = body.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as e:
        raise LayoutError(f"{where}: {key!r} must be a number, got {raw!r}") from e
