"""One slide per capability, written the way a real deck would use it.

Ordered by how often the shape appears across the sample corpus, so a template that
fails early fails on something that matters.
"""

from __future__ import annotations

from typing import Any

from pptxkit.conform.charts import CATEGORY_ROWS, chart_slides
from pptxkit.conform.figures import figure_slides
from pptxkit.conform.marks import mark_slides
from pptxkit.conform.motion import motion_slides
from pptxkit.conform.photos import photo_slides
from pptxkit.conform.tables import table_slides


EXERCISE: dict[str, dict[str, Any]] = {
    "cover": {
        "kicker": "A COVER",
        "title": "The words a title carries",
        "subtitle": "And the line beneath it",
        "chrome": {
            "kicker": {"at": {"box": {"x": "6%", "y": "50%", "w": "50%", "h": "5%"}}},
            "title": {
                "at": {"box": {"x": "6%", "y": "56%", "w": "74%", "h": "18%"}},
                "rung": "hero",
            },
            "subtitle": {
                "at": {"box": {"x": "6%", "y": "76%", "w": "60%", "h": "6%"}},
                "rung": "lead",
            },
        },
    },
    "cover-brand": {
        "kicker": "A BRAND COVER",
        "title": "Reversed out of the brand's own colour",
        "subtitle": "The accent a template actually owns",
        "background": "accent-1",
    },
    "cover-inverse": {
        "kicker": "A DARK COVER",
        "title": "Reversed out of the dark surface",
        "subtitle": "And the line beneath it",
        "background": "inverse",
    },
    "titled": {
        "kicker": "PLAIN",
        "title": "A title over the page surface",
        "subtitle": "Chrome on the light side of the palette",
    },
    "centred-title": {
        "title": "Centred on the canvas",
        "chrome": {
            "title": {
                "at": {"box": {"x": "10%", "y": "36%", "w": "80%", "h": "14%"}},
                "align": "center",
            }
        },
    },
    "low-title": {
        "kicker": "LOW",
        "title": "A title low on the canvas",
        "chrome": {
            "kicker": {"at": {"box": {"x": "6%", "y": "58%", "w": "50%", "h": "4%"}}},
            "title": {"at": {"box": {"x": "6%", "y": "63%", "w": "70%", "h": "13%"}}},
        },
    },
    "bullets": {
        "title": "A list of points",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 7}},
                "bullets": {"items": ["The first point", "The second point", "The third point"]},
            }
        ],
    },
    "two-column": {
        "title": "Two things side by side",
        "place": [
            {"at": {"cols": "left-half"}, "bullets": {"items": ["Left", "Column"]}},
            {"at": {"cols": "right-half"}, "bullets": {"items": ["Right", "Column"]}},
        ],
    },
    "cards": {
        "title": "Three cards across",
        "place": [
            {
                "at": {"cols": "left-third", "rows": {"from": 0, "to": 5}},
                "card": {"heading": "One", "body": "A plate with a heading and a line."},
            },
            {
                "at": {"cols": "mid-third", "rows": {"from": 0, "to": 5}},
                "card": {"heading": "Two", "body": "The same again, beside it."},
            },
            {
                "at": {"cols": "right-third", "rows": {"from": 0, "to": 5}},
                "card": {"heading": "Three", "body": "And a third, to fill the row."},
            },
        ],
    },
    "stats": {
        "title": "Numbers worth reading",
        "place": [
            {
                "at": {"cols": "full", "rows": "top-third"},
                "stats": {
                    "items": [
                        {"value": "42", "label": "first measure"},
                        {"value": "68", "label": "second measure"},
                        {"value": "91", "label": "third measure"},
                    ]
                },
            }
        ],
    },
    "chart-column": {
        "title": "A column chart",
        "place": [
            {
                "at": {"cols": "full", "rows": "top-two-thirds"},
                "chart": {
                    "kind": "column",
                    "data": [
                        {"category": "Q1", "value": 12},
                        {"category": "Q2", "value": 34},
                        {"category": "Q3", "value": 58},
                        {"category": "Q4", "value": 91, "highlight": True},
                    ],
                },
            }
        ],
    },
    "chart-bar-pct": {
        "title": "A bar chart in per cent",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 10}, "rows": "top-half"},
                "chart": {
                    "kind": "bar",
                    "unit": "%",
                    "data": [
                        {"category": "Urban", "value": 36},
                        {"category": "Rural", "value": 64, "highlight": True},
                    ],
                },
            }
        ],
    },
    "ellipses": {
        "title": "Numbered badges",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 2}, "rows": {"from": 0, "to": 3}},
                "ellipse": {"label": "1"},
            },
            {
                "at": {"cols": {"from": 2, "to": 4}, "rows": {"from": 0, "to": 3}},
                "ellipse": {"label": "2"},
            },
            {
                "at": {"cols": {"from": 4, "to": 6}, "rows": {"from": 0, "to": 3}},
                "ellipse": {"label": "3"},
            },
        ],
    },
    "connected": {
        "title": "A flow of three steps",
        "place": [
            {
                "id": "a",
                "at": {"cols": {"from": 0, "to": 3}, "rows": {"from": 1, "to": 4}},
                "card": {"heading": "First", "body": "Where it starts."},
            },
            {
                "id": "b",
                "at": {"cols": {"from": 4, "to": 7}, "rows": {"from": 1, "to": 4}},
                "card": {"heading": "Then", "body": "What follows."},
            },
            {
                "id": "c",
                "at": {"cols": {"from": 8, "to": 11}, "rows": {"from": 1, "to": 4}},
                "card": {"heading": "Last", "body": "Where it ends."},
            },
            {
                "at": {"cols": {"from": 3, "to": 4}, "rows": {"from": 2, "to": 3}},
                "connector": {"from": "a", "to": "b"},
            },
            {
                "at": {"cols": {"from": 7, "to": 8}, "rows": {"from": 2, "to": 3}},
                "connector": {"from": "b", "to": "c"},
            },
        ],
    },
    "flow": {
        "title": "Four steps across",
        "place": [
            {
                "at": {"cols": "full", "rows": "top-two-thirds"},
                "flow": {
                    "numbered": True,
                    "current": 2,
                    "items": [
                        {"head": "Read", "body": "Start with the corpus."},
                        {"head": "Name", "body": "Then the vocabulary."},
                        {"head": "Build", "body": "One shape at a time."},
                        {"head": "Check", "body": "Look at the render."},
                    ],
                },
            }
        ],
    },
    "flow-down": {
        "title": "The same run down the page",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 7}},
                "flow": {
                    "direction": "vertical",
                    "numbered": True,
                    "items": [
                        {"head": "Read", "body": "Start with the corpus."},
                        {"head": "Name", "body": "Then the vocabulary."},
                        {"head": "Build", "body": "One shape at a time."},
                    ],
                },
            }
        ],
    },
    "flow-plain": {
        "title": "Three stages, unnumbered",
        "place": [
            {
                "at": {"cols": "full", "rows": {"from": 1, "to": 7}},
                "flow": {
                    "arrow": "none",
                    "items": [{"head": "Draft"}, {"head": "Review"}, {"head": "Ship"}],
                },
            }
        ],
    },
    "rule": {
        "title": "A divider",
        "place": [{"at": {"cols": "full", "rows": {"from": 0, "to": 1}}, "rule": {}}],
    },
    "panel": {
        "title": "Reversed out of a panel",
        "chrome": {
            "title": {
                "at": {"box": {"x": "6%", "y": "40%", "w": "30%", "h": "20%"}},
                "ink": "inverse-ink",
            }
        },
        "place": [
            {
                "at": {"box": {"x": "0%", "y": "0%", "w": "45%", "h": "100%"}},
                "bleed": True,
                "panel": {"pair": "inverse"},
            }
        ],
    },
    "animated": {
        "title": "Revealed on click",
        "animate": "one_at_a_time",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 7}},
                "bullets": {"items": ["Appears first", "Appears second", "Appears third"]},
            }
        ],
    },
}

EXERCISE["swatches"] = {
    "kicker": "THEME",
    "title": "Every role, and the hex it resolved to",
    "subtitle": "Read from the theme this deck was built against",
    "place": [
        {
            "at": {"cols": "full"},
            "swatches": {
                "caption": "A role a theme leaves unbound keeps the design "
                "system's own default, so a theme that binds "
                "nothing still renders."
            },
        }
    ],
}

EXERCISE["grid"] = {
    "kicker": "THEME",
    "title": "A grid, and any polygon it has to respect",
    "subtitle": "The columns every placement resolves against",
    "place": [{"at": {"cols": "full"}, "grid": {}}],
}

EXERCISE["prose"] = {
    "kicker": "COPY",
    "title": "Paragraphs at a readable measure",
    "subtitle": "Dense copy without a costume of bullets",
    "place": [
        {
            "at": {"cols": "left-half"},
            "prose": {
                "paragraphs": [
                    "A paragraph set at the measure a reader can track, not the width the "
                    "canvas happens to offer.",
                    "And a second one, so the spacing between paragraphs is exercised too.",
                ]
            },
        },
        {
            "at": {"cols": "right-half"},
            "align": "center",
            "prose": {
                "cite": "A named speaker",
                "paragraphs": [
                    "A quotation reads as one voice, with its attribution set smaller beneath it."
                ],
            },
        },
    ],
}
EXERCISE["code"] = {
    "kicker": "SPEC",
    "title": "A listing, drawn rather than screenshotted",
    "subtitle": "Real text: selectable, themed, and measurable in the manifest",
    "place": [
        {
            "at": {"cols": "full"},
            "split": [
                {
                    "code": {
                        "heading": "the spec",
                        "accent": ["theme:", "place:"],
                        "lines": [
                            "theme: brand",
                            "---",
                            "place:",
                            "  - at: {cols: full}",
                            "    code:",
                            "      lines: [...]",
                        ],
                    }
                },
                {
                    "callouts": {
                        "heading": "what it buys",
                        "items": [
                            {
                                "head": "No browser in the loop",
                                "body": "A `document:` card rasterizes through headless Chrome; this does not.",
                            },
                            {
                                "head": "QA can read it",
                                "body": "The lines land in the manifest, so overflow is measurable.",
                            },
                        ],
                    }
                },
            ],
        }
    ],
}

EXERCISE.update(chart_slides())
EXERCISE.update(motion_slides())

EXERCISE["reveal-together"] = {
    "title": "Everything at once",
    "animate": "together",
    "place": [
        {"at": {"cols": {"from": 0, "to": 7}}, "bullets": {"items": ["One", "Two", "Three"]}}
    ],
}
EXERCISE["chart-build"] = {
    "title": "A chart built by category",
    "animate": "by_category",
    "place": [
        {
            "at": {"cols": "full", "rows": "top-two-thirds"},
            "chart": {"kind": "column", "data": [dict(r) for r in CATEGORY_ROWS]},
        }
    ],
}
# The one animate: needing more than one series — by_series on a single-series chart
# is one click for the whole chart.
EXERCISE["chart-build-by-series"] = {
    "title": "A chart built one series at a time",
    "animate": "by_series",
    "place": [
        {
            "at": {"cols": "full", "rows": "top-two-thirds"},
            "chart": {
                "kind": "column",
                "data": [
                    {
                        "category": row["category"],
                        "values": {"Direct": row["value"], "Partner": row["value"] // 2},
                    }
                    for row in CATEGORY_ROWS
                ],
            },
        }
    ],
}

EXERCISE["split"] = {
    "title": "A row divided, not measured",
    "subtitle": "Four cards across, and no span written anywhere",
    "place": [
        {
            "at": {"rows": {"from": 0, "to": 6}},
            "split": [
                {"card": {"heading": "One", "body": "A share of the band."}},
                {"card": {"heading": "Two", "body": "The same again."}},
                {"card": {"heading": "Three", "body": "And a third."}},
                {"card": {"heading": "Four", "body": "And a fourth."}},
            ],
        }
    ],
}
EXERCISE["split-uneven"] = {
    "title": "One share wider than its neighbours",
    "place": [
        {
            "at": {"rows": {"from": 0, "to": 6}},
            "split": [
                {"span": 2, "card": {"heading": "Twice", "body": "Two shares of four."}},
                {"card": {"heading": "Once", "body": "One."}},
                {"card": {"heading": "Once more", "body": "And one."}},
            ],
        }
    ],
}

EXERCISE.update(table_slides())


EXERCISE["document"] = {
    "title": "A markdown document",
    "place": [
        {
            "at": {"cols": "left-two-thirds", "rows": {"from": 0, "to": 9}},
            "document": {"source": "{notes}"},
        }
    ],
}

EXERCISE.update(mark_slides())
EXERCISE.update(figure_slides())
EXERCISE.update(photo_slides())
