"""Load a theme by name or path, binding semantic roles onto the referenced template.

Config (env, read at call time, so ``.env`` changes take effect between runs):

- ``PPTXKIT_THEME_DIR`` — directory holding templates and their themes (default ``templates``).
"""

from __future__ import annotations

import hashlib
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from pf_core.log import get_logger

from pptxkit.errors import ThemeError
from pptxkit.theme import blocks
from pptxkit.theme.chartstyle import chart_style
from pptxkit.theme.clrscheme import parse_color_scheme, parse_font_scheme, read_theme_xml
from pptxkit.theme.defaults import (
    CANVAS_H_DEFAULT,
    CANVAS_W_DEFAULT,
    DEFAULT_PALETTE,
    FACE_DEFAULT,
    HEADING_FACE_DEFAULT,
    LINE_WEIGHT_RUNG_DEFAULT,
    MIN_RUNG_DEFAULT,
    REFERENCE_HEIGHT_DEFAULT,
    MONO_DEFAULT,
    blank_presentation,
    default_ramp,
    default_theme,
)
from pptxkit.theme.model import Theme
from pptxkit.theme.palette import build_palette
from pptxkit.theme.scale import Scale
from pptxkit.theme.surface import Surface, inherited_surface
from pptxkit.utils.deck import open_presentation
from pptxkit.utils.env import env_str
from pptxkit.utils.text import MEASURED_FAMILIES, measured

logger = get_logger(__name__)

_EMU_PER_INCH = 914400
_THEME_DIR_DEFAULT = "templates"
_THEME_DIR_ENV_VAR = "PPTXKIT_THEME_DIR"


def theme_dir() -> Path:
    """Directory holding brand templates and the themes bound to them.

    A theme's ``template:`` resolves relative to the theme file, so both live here and
    the binary is never copied. Read at call time, not import time.
    """
    root = env_str(None, _THEME_DIR_ENV_VAR, default=_THEME_DIR_DEFAULT)
    return Path(root)


def resolve_theme(name: str) -> Path:
    """``<theme_dir>/<name>.theme.yaml``, falling back to the packaged built-in themes.

    A name found in neither place returns the theme-dir candidate, so the not-found
    error names the directory the caller controls.
    """
    candidate = theme_dir() / f"{name}.theme.yaml"
    if candidate.is_file():
        return candidate
    builtin = _builtin_dir() / f"{name}.yaml"
    return builtin if builtin.is_file() else candidate


def _builtin_dir() -> Path:
    return Path(str(resources.files("pptxkit"))) / "theme" / "builtin"


def _theme_file(ref: str | Path) -> Path:
    """An existing file for a theme name or a theme path, or a ThemeError saying which."""
    path = Path(ref)
    if path.is_file():
        return path
    if path.suffix or len(path.parts) > 1:
        raise ThemeError(
            f"theme file not found: {path} — that is read as a path, and nothing is "
            f"searched. To load a theme by name, pass the bare name (e.g. 'base'), "
            f"which is looked up in {theme_dir()} and then in the packaged themes"
        )
    resolved = resolve_theme(str(ref))
    if resolved.is_file():
        return resolved
    packaged = ", ".join(sorted(p.stem for p in _builtin_dir().glob("*.yaml")))
    raise ThemeError(
        f"unknown theme {str(ref)!r}: no theme file at {resolved} (set "
        f"PPTXKIT_THEME_DIR to search elsewhere) and no packaged theme of that name "
        f"(packaged: {packaged}). Onboard a brand template with "
        f"'pptxkit conform <brand>.pptx --adopt {ref}', or pass a path to a theme file"
    )


def load_theme(
    name_or_path: str | Path | None = None,
    *,
    slide_w: float = CANVAS_W_DEFAULT,
    slide_h: float = CANVAS_H_DEFAULT,
) -> Theme:
    """Read a theme and specialize the design system into its template.

    ``name_or_path`` is either a path to a theme YAML file, or a bare theme name —
    ``load_theme("base")``, ``load_theme("acme")`` — resolved through
    :func:`resolve_theme` exactly as a spec's ``theme:`` is.

    ``bind:`` maps semantic role names onto slots in the template's own
    ``clrScheme``; every unbound role keeps its system default.

    With no argument the built-in design system is returned, resolved onto a blank
    canvas of ``slide_w`` x ``slide_h`` inches.

    Raises:
        ThemeError: the name resolves to nothing, the file or its template is missing
            or unreadable, a key or role is unknown, a bind names a slot the template
            does not define, or a bind leaves a colour pair below WCAG AA.
    """
    if name_or_path is None:
        return default_theme(slide_w=slide_w, slide_h=slide_h)
    path = _theme_file(name_or_path)
    try:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ThemeError(f"invalid YAML in theme file {path}: {e}") from e
    if not isinstance(raw, dict):
        raise ThemeError(f"theme file {path} must contain a mapping at its top level")
    blocks.check_keys(raw, path=path)

    name = str(raw.get("name", path.stem))
    declared = str(raw.get("template", "")).strip()
    template: Path | None = None

    if declared:
        template = (path.parent / declared).resolve()
        if not template.is_file():
            raise ThemeError(f"template not found: {template} (referenced by {path})")
        prs = open_presentation(template)
    else:
        if raw.get("bind"):
            raise ThemeError(
                f"theme {name!r} declares 'bind:' but no 'template:' — there is no "
                f"template palette to bind onto; drop the bind or name a template"
            )
        if raw.get("marks"):
            raise ThemeError(
                f"theme {name!r} declares 'marks:' but no 'template:' — mark media is "
                f"resolved beside the template or out of it; drop the marks or name "
                f"a template"
            )
        prs = blank_presentation(slide_w=slide_w, slide_h=slide_h)

    scale = Scale(slide_w=prs.slide_width / _EMU_PER_INCH, slide_h=prs.slide_height / _EMU_PER_INCH)

    surface: Surface | None = None
    if template is None:
        palette = DEFAULT_PALETTE
        major, minor = HEADING_FACE_DEFAULT, FACE_DEFAULT
    else:
        layout = _compose_layout(prs, raw.get("compose_layout"))
        theme_xml = read_theme_xml(layout.slide_master)
        major, minor = parse_font_scheme(theme_xml)
        roles, pairs = blocks.bind(
            raw.get("bind") or {}, parse_color_scheme(theme_xml), theme_name=name
        )
        palette = build_palette(roles, pairs=pairs)
        surface = inherited_surface(layout)

    type_cfg = raw.get("type") or {}
    # A template's fontScheme routinely lags the face its slides really use, so an
    # explicit face: wins over it. major is the display face, minor the body face.
    face = str(type_cfg.get("face") or minor)
    heading_face = str(type_cfg.get("heading_face") or major)
    # Wrap estimates come from the face's own advances; an unmeasured face falls back
    # to the widest glyph across families — safe, loose, and invisible downstream.
    for role, candidate in (("face", face), ("heading_face", heading_face)):
        if not measured(candidate):
            logger.warning(
                "theme_face_unmeasured",
                theme=name,
                role=role,
                face=candidate,
                measured=MEASURED_FAMILIES,
            )
    ramp = default_ramp(scale, heading_face=heading_face)
    reference_h = float(type_cfg.get("reference_height", REFERENCE_HEIGHT_DEFAULT))
    ramp.update(
        {
            name_: blocks.rung(
                name_,
                cfg,
                face=face,
                heading_face=heading_face,
                scale=scale,
                reference_height=reference_h,
            )
            for name_, cfg in (type_cfg.get("ramp") or {}).items()
        }
    )

    theme = Theme(
        name=name,
        template=template,
        drop_template_slides=bool(raw.get("drop_template_slides", False)),
        palette=palette,
        scale=scale,
        face=face,
        heading_face=heading_face,
        mono=str(type_cfg.get("mono") or MONO_DEFAULT),
        ramp=ramp,
        min_pt=scale.pt(
            float(type_cfg["min_pt"]) / reference_h if "min_pt" in type_cfg else MIN_RUNG_DEFAULT
        ),
        grid=blocks.grid(raw.get("scale") or {}, scale),
        motion=blocks.motion(raw.get("motion"), path=path),
        marks=blocks.marks(raw.get("marks") or {}, path=path),
        line_weight=scale.pt(
            float(type_cfg["line_weight_pt"]) / reference_h
            if "line_weight_pt" in type_cfg
            else LINE_WEIGHT_RUNG_DEFAULT
        ),
        chart=chart_style(raw.get("chart") or {}, path=path),
        reserve=blocks.reserve(raw.get("reserve"), path=path),
        chrome=blocks.chrome(raw.get("chrome"), path=path),
        icons=blocks.icons(raw.get("icons"), path=path),
        compose_layout=(str(raw["compose_layout"]) if raw.get("compose_layout") else None),
        surface=surface,
        hash=_hash(path, template),
    )
    logger.info(
        "theme_loaded",
        theme=theme.name,
        template=str(template),
        roles=len(palette.roles),
        accents=len(palette.accents),
    )
    return theme


def _compose_layout(prs, prefer: str | None = None):
    """The layout the deck composes on — whose palette and surface the theme takes."""
    # Imported here, not at module scope: pptxkit.layouts' package __init__ pulls in
    # compose and the registry, which import back through pptxkit.theme.
    from pptxkit.layouts.resolve import pick_compose_layout

    return pick_compose_layout(prs, prefer=prefer)


def _hash(theme_path: Path, template: Path | None) -> str:
    """Identity for cache keys — changes when either the YAML or the template changes."""
    h = hashlib.sha256()
    h.update(theme_path.read_bytes())
    if template is not None:
        h.update(template.read_bytes())
    return h.hexdigest()[:16]
