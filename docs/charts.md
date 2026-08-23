# Charts — a real, native chart part

How `charts/native.py` turns a validated `ChartSpec` into a native OOXML chart —
a real, editable PowerPoint chart with an embedded worksheet, built via
python-pptx's chart API. This doc is about the **renderer's internals**: the
per-type option sets, the palette, and how to add a type.

**To write a chart in a deck spec, read [`docs/authoring.md`](authoring.md)
instead** — it owns the wire format (`kind:`, the row-oriented `data:` list,
`value:` vs `values:`, `highlight:`, the full table of all 29 kinds) and every
error message the chart block can produce. Nothing about the spec's shape is
duplicated here.

For AI assistants: [`pptx-deck-building.md`](pptx-deck-building.md) covers the render/QA loop
end to end; this doc is the full reference for the chart renderer
specifically.

---

## Table of Contents

- [What reaches the renderer](#what-reaches-the-renderer)
- [The native renderer](#the-native-renderer)
- [Chart build animation](#chart-build-animation)
- [Room for the labels a bar chart sets on its left](#room-for-the-labels-a-bar-chart-sets-on-its-left)
- [Negative values, and why the render cannot check them](#negative-values-and-why-the-render-cannot-check-them)
- [Refusing a truncated axis](#refusing-a-truncated-axis)
- [The categorical palette](#the-categorical-palette)
- [Adding a new chart type](#adding-a-new-chart-type)

## What reaches the renderer

`ChartSpec.from_body` parses the spec's `chart:` block and hands the renderer a
frozen `ChartSpec`: a `type`, `categories`, one or more `Series`, an optional
`highlight` index, `annotate`, and `y_min`/`y_max`.

The spec's wire format is **row-oriented** — one `data:` row per datapoint, each
carrying its own category (or `x`/`y`/`size`), its own numbers, and its own
`highlight` flag. `from_body` derives the `categories`/`series` tuples the
renderer consumes, so nothing downstream of the parse sees rows. Series names and
their order come from the first row's `values` mapping.

Two consequences worth knowing when working on the renderer:

- **`highlight` arrives as an index**, resolved from whichever row set
  `highlight: true`. The renderer's per-point colour override is unchanged.
- **`Series.unit` comes from the block, not the row.** `unit:` is a key of the
  `chart:` block, threaded through `_parse_category_rows` onto every `Series`, and
  `_style_data_labels` writes it into the label number format as a literal. Only
  the point-shaped parser takes no `unit` argument, so it stays `None` on the
  xy-scatter and bubble kinds: `unit:` is accepted there and does nothing.

`annotate` is validated and carried on the spec but **no renderer draws it**.

## The native renderer

`charts/native.py` builds a real chart part via python-pptx's chart API —
`add_chart`, an embedded `CategoryChartData`/`XyChartData`/`BubbleChartData`
worksheet (shape-dependent), and per-series or per-point fill styled from the
theme. It draws all **29** creatable `ChartSpec` types — every type
python-pptx can build: the 22 category-shaped types (`bar`, `column`,
`column-stacked`, `column-stacked-100`, `bar-stacked`, `bar-stacked-100`,
`line`, `line-markers`, `line-stacked`, `line-stacked-100`,
`line-markers-stacked`, `line-markers-stacked-100`, `area`, `area-stacked`,
`area-stacked-100`, `radar`, `radar-filled`, `radar-markers`, `pie`,
`doughnut`, `pie-exploded`, `doughnut-exploded`), the 5 xy-scatter variants,
and the 2 bubble variants — and reads every colour, face and size from the
theme; it never hardcodes a hex value or a point size.

**Every piece of chart text reads the slide's live pair, not the template.**
`_style_data_labels` and `_style_axes` set their own `ctx.fg()`/`ctx.dim()`, and
`_style_text` sets the chart-wide default so the two pieces of text nobody asks
for — the legend, and the title PowerPoint auto-generates for a single-series
chart — cannot fall through to the presentation theme's dark ink and disappear on
an `inverse` slide. The legend also takes the theme's face and the `caption` rung
rather than python-pptx's 18pt default.

Eleven per-type option frozensets drive the divergence, so a new type is added
by extending a set, never by branching on `spec.type`. A twelfth,
`_SIDE_LABEL_CHART_TYPES`, has its own section below:

- `_AXIS_CHART_TYPES` — everything except `pie`/`doughnut`/`pie-exploded`/
  `doughnut-exploded`, which have no category or value axis
  (`chart.category_axis` raises `ValueError` on one). The xy-scatter and
  bubble types all have both axes, so they join this set too.
- `_GAP_WIDTH_CHART_TYPES` — only the bar/column family (including their
  stacked variants); no other plot class exposes `gap_width` in python-pptx —
  not even the xy-scatter and bubble plots.
- `_PIE_FAMILY_CHART_TYPES` — `pie`, `doughnut`, `pie-exploded` and
  `doughnut-exploded`: one series, coloured per point from the categorical
  palette, named by `show_category_name` rather than a legend or axis.
- `_STRUCTURAL_GRIDLINE_CHART_TYPES` — `radar`, `radar-filled` and
  `radar-markers`: their major gridlines are the rings and spokes the data
  is plotted against, so `_style_axes` leaves them at python-pptx's own
  default instead of driving them from `theme.chart.grid` like every other
  axis-bearing type.
- `_NO_DATA_LABEL_CHART_TYPES` — the 5 `xy-scatter*` variants. python-pptx's
  `CT_ScatterChart` lists `c:dLbls` in its tag sequence but never wires up the
  descriptor, so `plot.has_data_labels` raises `AttributeError` for every
  scatter variant; `add_native_chart` skips the data-labels call for these
  types entirely. `CT_BubbleChart` does define it, so `bubble`/`bubble-3d`
  keep their labels like any other type.
- `_MARKER_CHART_TYPES` — `line-markers` (+ its two stacked variants),
  `radar-markers`, and `xy-scatter`/`xy-scatter-lines`/`xy-scatter-smooth`:
  the types python-pptx itself renders with an auto/default marker, themed
  from `theme.chart.marker_size`/`marker_style` instead. Plain `line`,
  `line-stacked(-100)`, plain `radar`, and the two `*-no-markers` scatter
  variants explicitly render with **no** marker (python-pptx writes
  `<c:symbol val="none"/>` at creation) — forcing one on would fight the
  type's own declared identity. `radar-filled`'s `radarStyle="filled"`
  suppresses a marker regardless of what's set (confirmed by forcing one and
  rendering it — nothing appears). Bubble series inherit `.marker` too, but
  `CT_BubbleSer`'s real schema has no marker child; a bubble's own
  size-driven circle is already its marker.
- `_STROKE_CHART_TYPES` — every `line`/`radar`/`xy-scatter` variant, marker or
  not (14 types). A point on these has no fillable shape of its own — only a
  stroke and, on some types, a marker — so `_fill_point` forces a solid fill
  here regardless of `theme.chart.gradient`: a gradient stored on a shape
  nothing draws is confirmed-invisible (rendered and inspected pixel by
  pixel) and costs two gradient-stop elements for nothing. `bubble`/`bubble-3d`
  are excluded — a bubble's point *is* a visible filled circle, so its
  gradient stays meaningful.
- `_PERCENT_AXIS_CHART_TYPES` — the 5 `*-stacked-100` types. `_style_axes` forces
  a `0%` tick format on the value axis, and `_style_data_labels` drops the series'
  `unit` — an axis already reading in percent has nothing left for a suffix to add.
- `_SERIES_FILL_CHART_TYPES` — `area`, `area-stacked`, `area-stacked-100` and
  `radar-filled`: one continuous band per series rather than a mark per point, so
  gradient and shadow are applied to the **series** through `_fill_series`, not
  point by point.
- `_HORIZONTAL_BAR_CHART_TYPES` — `bar`, `bar-stacked` and `bar-stacked-100`.
  Their bars run the other way, so `theme.chart.gradient_angle` is rotated a
  quarter turn and the gradient still runs along the bar rather than across it.
- `_CONNECTED_CHART_TYPES` — every type but `xy-scatter`, which is points and
  nothing else. The rest take a themed stroke; giving one to a pure scatter would
  draw a line through data chosen to have none.

Marker fill always takes the series' own colour from the categorical palette
(`_style_marker`, called once per series) rather than a fixed colour, so a
themed marker matches its line instead of introducing a new one.

Editable in PowerPoint (Edit Data), animatable by category or by series,
vector at any zoom, and its labels are real text — visible to a PDF text
extractor and `qa`'s overflow check, unlike a screenshotted image would be.

## Chart build animation

A native chart's own build — bars arriving one category at a time on click,
rather than the whole chart appearing at once — is the slide-level `animate:`
field, same field as any other component's click build:

```yaml
title: Adoption climbs every quarter
animate: by_category    # or by_series
place:
  - at: {cols: full}
    chart:
      kind: column
      data:
        - {category: Q1, value: 12}
        - {category: Q4, value: 91}
```

`by_category` and `by_series` map to `add_chart_build`'s `by="category"` /
`by="series"`, which the `chart` component calls directly on the chart
`graphicFrame` — this is a different OOXML mechanism from the `<p:bldP>`
visibility toggle every other component's `animate:` uses
(`one_at_a_time`/`together`), because a chart is a `graphicFrame` build
(`<p:bldGraphic>`/`<a:bldChart>`), not a shape-visibility one. Asking for either
value on a non-chart component is rejected rather than silently downgraded. See
`docs/pptx-deck-building.md`'s Animations section for the OOXML and the
verification caveat.

**Keynote does not play a chart build.** The same file that builds one category per
click in PowerPoint shows the chart whole in Keynote — `<p:bldGraphic>`/`<a:bldChart>`
is the one construct here with a known consumer gap. For a Keynote audience use
`animate: together`, or split the categories across slides.

**Not every kind can build by category.** `_BUILDABLE_BY_CATEGORY` in
`charts/model.py` names the ones that can, and `by_category` on anything else
raises. A category build reveals one category's marks per click, so it needs the
category to *be* a mark: a bar, a wedge, a point on a line. On a radar the
categories are vertices of one closed outline — filled, they are a single
polygon — so the build emits a click per category and nothing moves. Observed in
Keynote on `radar-filled`: six clicks, no change. This is the same refusal
`_HIGHLIGHTABLE_KINDS` makes, for the same reason.

`by_series` is not restricted: every kind has series, and a chart with one series
builds in a single click, which is honest rather than dead.

## Room for the labels a bar chart sets on its left

A bar chart's category labels run down the left of the plot, and nothing in the
file says how much room they get — so each renderer decides. LibreOffice shrinks
the plot area to fit them; Keynote does not, and a long label runs off the slide.

`_reserve_label_column` writes an explicit `c:manualLayout` on the plot area,
sized from the longest label at the caption rung, floored so the bars keep at
least `_MIN_PLOT_FRACTION` of the frame. Every renderer honours a manual layout,
so the reservation is stated once, in the file.

Only the bar family (`_SIDE_LABEL_CHART_TYPES`) gets one. A column chart's labels
sit *under* the plot, in width they already have, and pinning its plot area would
take room away for nothing.

## Negative values, and why the render cannot check them

**A bar or column chart carrying negative values writes correct OOXML and renders wrongly
through the path `render` and `qa` both use.** The bar is drawn on the *positive* side at
its absolute length, and its data label loses the minus sign — while the value axis
correctly scales to include the negatives.

What was measured, so nobody re-investigates it:

| | |
|---|---|
| The chart's own `numCache` | holds `-146.0` |
| Its embedded workbook | holds `-146` |
| `c:crosses` | `autoZero`, and no `min`/`max` is pinned |
| Stripping `c:dPt`, or setting `invertIfNegative="0"` | changes nothing |
| The same chart built with **bare python-pptx** | renders identically wrong |
| A **line** series with the same values | renders correctly, sign and all |

So the file is right and pptxkit is not implicated: LibreOffice 26.2.5.2 plots and labels
the absolute value of a `barChart` datapoint. PowerPoint is expected to draw it correctly;
the contact sheet you check it on will not, and neither will `qa`. The documented workflow
for every other chart — build it, render it, look at it — is the one thing that cannot
settle this one, so `qa` raises a `chart-negative` warning saying exactly that.

So for a diverging comparison, reach for
[`diverge`](components.md#diverge--signed-bars-either-side-of-a-centre-rule) instead. It
draws the same shape as geometry rather than as a chart, which renders identically
everywhere, at the cost of not being an editable chart object in PowerPoint.

A chart whose values are all positive is unaffected.

## Refusing a truncated axis

`y_min` / `y_max` reach the native chart's value axis directly. Set them
explicitly to stop auto-scaling to the data's own min/max — the same
auto-scale that can make a 12-point move look identical to a 90-point one.
Leaving both unset keeps automatic scaling.

## The categorical palette

Multiple series (or wedges on a pie/doughnut/pie-exploded/doughnut-exploded)
cycle the palette's accent ramp — `accent-1`…`accent-N`, counting only the
accents a theme genuinely binds — so each is visually distinct without a legend
doing all the work. `highlight` overrides whichever colour the cycle assigns to
that one category with the second accent. A single series stays `accent-1`; the
ramp only engages once colour has to carry a distinction between two or more
series or wedges. Keep an example inside the theme's accent count: past it the
cycle repeats, and two series share a colour.

## Adding a new chart type

1. Add it to `ChartSpec`'s `_TYPES` in `charts/model.py` — a type outside this
   set never reaches the renderer. If its data shape isn't one value per
   category, add it to `_XY_CHART_TYPES` or `_BUBBLE_CHART_TYPES` too, so
   `_shape()` and the `points`-vs-`values` validation pick it up.
2. Map it to an `XL_CHART_TYPE` in `charts/native.py`'s `_CHART_TYPES` — 29 of
   `XL_CHART_TYPE`'s 73 members are creatable through python-pptx; the other
   44 raise `NotImplementedError`.
3. Measure the new type against each of the twelve option frozensets in
   [The native renderer](#the-native-renderer) before assuming it matches its
   family — `gap_width` and `has_data_labels` are both silent no-ops or raise
   `AttributeError` on the wrong plot class, so a wrong guess here fails
   quietly rather than loudly. Build a real chart of the type and probe it
   directly rather than reasoning from the plot class's name.
