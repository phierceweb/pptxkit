"""One parser per block of a theme YAML file, plus the top-level key vocabulary.

``load.py`` reads the file and assembles the :class:`~pptxkit.theme.model.Theme`;
everything that turns one YAML block into a value object lives here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pf_core.log import get_logger

from pptxkit.errors import LayoutError, ThemeError
from pptxkit.theme.defaults import (
    _BOLD as _RAMP_BOLD,
    _HEADING as _RAMP_HEADING,
    DEFAULT_PAIRS,
    DEFAULT_ROLES,
    default_grid,
)
from pptxkit.theme.blocks_motion import motion  # noqa: F401 — re-exported for load.py
from pptxkit.theme.model import TypeStyle
from pptxkit.theme.palette import AUTO_INK
from pptxkit.theme.scale import Grid, Scale
from pptxkit.utils.spans import percent
from pptxkit.theme.stock import is_stock_accent

if TYPE_CHECKING:
    from pptxkit.layouts.chrome import ChromeField
    from pptxkit.layouts.place import Reserved

logger = get_logger(__name__)

_ACCENT_ROLE = re.compile(r"^accent-([1-9][0-9]*)$")
_HEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")
# A mark decorates a painted backdrop, and only 'inverse' paints one — a page slide
# keeps the master's own surface, so layouts/compose.py never looks up any other name.
_MARK_NAMES = ("inverse",)
_RESERVE_KEYS = ("name", "poly")
_KNOWN_KEYS = frozenset(
    {
        "name",
        "template",
        "compose_layout",
        "drop_template_slides",
        "bind",
        "scale",
        "type",
        "marks",
        "reserve",
        "chart",
        "chrome",
        "icons",
        "motion",
    }
)
_REPLACED_KEYS = {
    "grid": "'grid' was replaced by 'scale' (margins and gutter are now fractions of the canvas)",
    "roles": "'roles' was replaced by 'bind', which maps semantic role names onto template slots",
    "overrides": "'overrides' was replaced by 'bind'; an unbound role keeps the "
    "design system's default",
    "compose_on": "'compose_on' is gone — the compiler picks the emptiest layout "
    "across every master",
    "series_colors": "'series_colors' is gone — series cycle the palette's accent roles",
    "safe_zones": "'safe_zones' is gone — use 'reserve': polygons in fractions of the "
    "canvas, applying to every slide",
}


def check_keys(raw: dict[str, Any], *, path: Path) -> None:
    """Reject removed keys by name, and anything the loader does not read."""
    for key, note in _REPLACED_KEYS.items():
        if key in raw:
            raise ThemeError(f"theme {path}: {note}")
    unknown = sorted(set(raw) - _KNOWN_KEYS)
    if unknown:
        raise ThemeError(
            f"theme file {path} has unknown top-level key {unknown[0]!r}; "
            f"known keys: {', '.join(sorted(_KNOWN_KEYS))}"
        )
    if "min_size" in (raw.get("type") or {}):
        raise ThemeError(
            f"theme {path}: key 'type.min_size' was replaced by 'min_pt' "
            f"(points per inch of canvas height)"
        )


def bind(
    cfg: dict[str, Any], scheme: dict[str, str], *, theme_name: str
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Layer explicit role -> template-slot bindings over the system defaults.

    A value is a slot name, or a literal ``RRGGBB`` — a template's real surface need
    not be in its ``clrScheme`` at all. An accent bound to a slot still holding
    Microsoft's shipped value is ignored, keeping the built-in accent.
    """
    roles = dict(DEFAULT_ROLES)
    pairs = dict(DEFAULT_PAIRS)
    for key, value in cfg.items():
        role, slot = str(key), str(value)
        accent = _ACCENT_ROLE.match(role)
        if role not in DEFAULT_ROLES and not accent:
            raise ThemeError(
                f"theme {theme_name!r} binds unknown role {role!r}; known roles: "
                f"{', '.join(sorted(DEFAULT_ROLES))} (plus accent-N)"
            )
        if _HEX.match(slot):
            resolved = slot.lstrip("#").upper()
        else:
            try:
                resolved = scheme[slot]
            except KeyError:
                raise ThemeError(
                    f"theme {theme_name!r} binds {role!r} to unknown template slot "
                    f"{slot!r}; template defines: {', '.join(sorted(scheme))} "
                    f"(or give a literal RRGGBB)"
                ) from None
        if accent and is_stock_accent(resolved):
            logger.warning(
                "stock_accent_ignored", theme=theme_name, role=role, slot=slot, value=resolved
            )
            continue
        roles[role] = resolved
        if accent:
            pairs[role] = (AUTO_INK, role)
    return roles, pairs


def rung(
    name: str, cfg: Any, *, face: str, heading_face: str, scale: Scale, reference_height: float
) -> TypeStyle:
    """Build one ramp rung from the point size it is written as.

    A theme states ``pt: 14`` — the size on a canvas ``reference_height`` inches tall;
    what is kept is the ratio, so the ramp scales with the canvas. ``face: heading``
    and ``face: body`` name the theme's two faces; anything else is a literal typeface.
    """
    if not isinstance(cfg, dict):
        raise ThemeError(f"type ramp entry {name!r} must be a mapping")
    for gone, why in (("size", "point size"), ("rung", "points per inch of canvas height")):
        if gone in cfg:
            raise ThemeError(
                f"type ramp entry {name!r}: {gone!r} ({why}) was replaced by 'pt' — "
                f"the size at the theme's reference_height"
            )
    if "pt" not in cfg:
        raise ThemeError(f"type ramp entry {name!r} needs a 'pt'")
    alias = cfg.get("face")
    # An entry that names only a size keeps the design system's weight and face for its
    # rung: `title: {pt: 34}` resizes the title, it does not quietly un-bold it.
    if alias is None:
        resolved = heading_face if name in _RAMP_HEADING else None
    else:
        resolved = {"body": face, "heading": heading_face}.get(alias, str(alias))
    return TypeStyle(
        rung=float(cfg["pt"]) / reference_height,
        scale=scale,
        bold=bool(cfg.get("bold", name in _RAMP_BOLD)),
        italic=bool(cfg.get("italic", False)),
        face=resolved or None,
    )


def grid(cfg: dict[str, Any], scale: Scale) -> Grid:
    """The theme's grid; anything the ``scale:`` block omits falls to the built-in one."""
    base = default_grid(scale)
    margin = cfg.get("margin") or {}

    def frac(block: dict[str, Any], key: str, fallback: float) -> float:
        """A percent of the canvas, or the built-in grid's value where unstated."""
        if key not in block:
            return fallback
        return percent(block[key], key, where="theme 'scale'", error=ThemeError)

    return Grid(
        scale=scale,
        top_frac=frac(margin, "top", base.top_frac),
        right_frac=frac(margin, "right", base.right_frac),
        bottom_frac=frac(margin, "bottom", base.bottom_frac),
        left_frac=frac(margin, "left", base.left_frac),
        columns=int(cfg.get("columns", base.columns)),
        rows=int(cfg.get("rows", base.rows)),
        gutter_frac=frac(cfg, "gutter", base.gutter_frac),
        body_top_frac=frac(cfg, "body_top", base.body_top_frac),
    )


def marks(cfg: dict[str, Any], *, path: Path) -> dict[str, Any]:
    """Theme art, keyed by the background it decorates."""
    unknown = sorted(set(cfg) - set(_MARK_NAMES))
    if unknown:
        raise ThemeError(
            f"theme {path}: mark {unknown[0]!r} names no painted backdrop, so nothing "
            f"would ever lay it down; a mark's name is the background it decorates — "
            f"known marks: {', '.join(_MARK_NAMES)}"
        )
    for name, value in cfg.items():
        if not isinstance(value, dict) or not value.get("media"):
            raise ThemeError(
                f"theme {path}: mark {name!r} needs a mapping with a 'media:' naming an "
                f"image file, got {value!r}"
            )
    return cfg


def icons(cfg: Any, *, path: Path) -> Path | None:
    """The theme's own icon directory, resolved beside the theme file.

    Searched before the shipped set, so a brand overrides a name without renaming
    anything in the decks.
    """
    if cfg is None:
        return None
    directory = (path.parent / str(cfg)).resolve()
    if not directory.is_dir():
        raise ThemeError(
            f"theme {path}: icons directory not found: {directory} — 'icons:' names a "
            f"directory of .svg files beside the theme, not an icon"
        )
    return directory


def chrome(cfg: Any, *, path: Path) -> dict[str, ChromeField]:
    """The theme's title treatment: where each chrome line sits and how it is set.

    Every value is a fraction of the canvas plus ``align``/``anchor``. A field the
    theme omits stacks from the top margin at the content width.
    """
    # Imported here for the same reason as _region below.
    from pptxkit.layouts.chrome import chrome_field

    if cfg is None:
        return {}
    if not isinstance(cfg, dict):
        raise ThemeError(
            f"theme {path}: 'chrome' is a mapping of chrome field to its treatment, got {cfg!r}"
        )
    out: dict[str, ChromeField] = {}
    for key, entry in cfg.items():
        try:
            out[str(key)] = chrome_field(entry, name=str(key))
        except LayoutError as e:
            raise ThemeError(f"theme {path}: {e}") from None
    return out


def reserve(cfg: Any, *, path: Path) -> tuple[Reserved, ...]:
    """Every reserved region the theme declares, as polygons in canvas fractions."""
    if cfg is None:
        return ()
    if not isinstance(cfg, list):
        raise ThemeError(
            f"theme {path}: 'reserve' is a list of regions, each a mapping with a 'name' "
            f"and a 'poly', got {cfg!r}"
        )
    return tuple(_region(entry, path=path) for entry in cfg)


def _region(cfg: Any, *, path: Path) -> Reserved:
    # Imported here, not at module scope: layouts.place reads pptxkit.theme.model, so
    # a module-scope import would reach back into this package while it is still loading.
    from pptxkit.layouts.place import Reserved

    if not isinstance(cfg, dict):
        raise ThemeError(
            f"theme {path}: each 'reserve' entry is a mapping with a 'name' and a "
            f"'poly', got {cfg!r}"
        )
    name = str(cfg.get("name", "unnamed"))
    where = f"theme {path}: reserved region {name!r}"
    if "applies_to" in cfg:
        raise ThemeError(
            f"{where}: 'applies_to' is gone — a slide has no layout to scope "
            f"a region to; every region applies to every slide"
        )
    unknown = sorted(set(cfg) - set(_RESERVE_KEYS))
    if unknown:
        raise ThemeError(
            f"{where}: unknown key {unknown[0]!r}; known keys: {', '.join(_RESERVE_KEYS)}"
        )
    poly = cfg.get("poly")
    if not isinstance(poly, list):
        raise ThemeError(
            f"{where}: needs a 'poly' list of {{x, y}} points in percents of the canvas"
        )
    return Reserved(name=name, poly=tuple(_point(p, where=where) for p in poly))


def _point(value: Any, *, where: str) -> tuple[float, float]:
    if isinstance(value, (list, tuple)):
        raise ThemeError(
            f"{where}: a 'poly' point is keyed — write {{x: 78%, y: 0%}}, not {value!r}"
        )
    if not isinstance(value, dict) or set(value) != {"x", "y"}:
        raise ThemeError(
            f"{where}: every 'poly' point is an {{x, y}} mapping in percents of the "
            f"canvas, got {value!r}"
        )
    return (
        percent(value["x"], "poly.x", where=where, error=ThemeError),
        percent(value["y"], "poly.y", where=where, error=ThemeError),
    )
