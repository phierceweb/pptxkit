"""Exercises for motion: the roles, the interactive trigger, the hard cut."""

from __future__ import annotations

from typing import Any


def motion_slides() -> dict[str, dict[str, Any]]:
    """One slide per motion capability a template has to carry."""
    slides: dict[str, dict[str, Any]] = {}
    slides["click-to-reveal"] = {
        "title": "Held back until it is asked for",
        "subtitle": "An interactive trigger spends no slide advance",
        "place": [
            {
                "at": {"cols": "left-half"},
                "id": "question",
                "card": {"heading": "What broke?", "body": "Click this card."},
            },
            {
                "at": {"cols": "right-half"},
                "reveals": "question",
                "card": {
                    "heading": "The cache key never invalidated",
                    "body": "Hidden until the question is clicked.",
                },
            },
        ],
    }
    slides["line-role"] = {
        "title": "A rule that draws itself",
        "subtitle": "The component reports a motion role; the theme binds it to a wipe",
        "animate": "one_at_a_time",
        "place": [
            {"at": {"cols": "full", "rows": {"from": 0, "to": 1}}, "rule": {}},
            {
                "at": {"cols": "left-two-thirds", "rows": {"from": 1, "to": 6}},
                "bullets": {"items": ["The rule wipes", "The text fades"]},
            },
        ],
    }
    slides["transition-none"] = {
        "title": "A deliberate hard cut",
        "subtitle": "The one thing a slide may say about a transition",
        "transition": "none",
        "place": [
            {
                "at": {"cols": {"from": 0, "to": 7}},
                "bullets": {
                    "items": ["Which transition is the theme's", "A slide may only refuse it"]
                },
            }
        ],
    }
    return slides
