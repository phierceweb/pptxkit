"""Compile a deck spec into a .pptx and its build manifest."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from pf_core.log import get_logger
from pf_core.utils.io import atomic_write_bytes, atomic_write_text

import pptxkit.components  # noqa: F401 — import registers the built-in body components
from pptxkit.compile.background import flatten_master_background
from pptxkit.compile.content import write_content
from pptxkit.compile.record import Provenance
from pptxkit.compile.manifest import ManifestRecorder
from pptxkit.compile.prune import prune_unused_layouts
from pptxkit.paths import scratch
from pptxkit.errors import SpecError
from pptxkit.layouts.compose import render_slide
from pptxkit.layouts.registry import SlideCtx
from pptxkit.layouts.resolve import pick_compose_layout
from pptxkit.spec import parse_deck
from pptxkit.theme import Theme, blank_presentation, load_theme
from pptxkit.theme.load import resolve_theme, theme_dir  # noqa: F401 — re-exported
from pptxkit.utils.deck import delete_slide, open_presentation, register_notes_master
from pptxkit.utils.shapes import notes as set_notes

logger = get_logger(__name__)


@dataclass(frozen=True)
class BuildResult:
    """Where the build put things."""

    deck: Path
    manifest: Path
    slides: int


def build_deck(
    spec_path: str | Path,
    *,
    theme_path: str | Path | None = None,
    out: str | Path | None = None,
    keep_layouts: bool = False,
) -> BuildResult:
    """Compile ``spec_path`` into a ``.pptx`` plus a sibling ``.manifest.json``.

    Args:
        spec_path: Path to the ``.deck.yaml``.
        theme_path: Theme file. Defaults to the spec's ``theme:`` name resolved
            through :func:`pptxkit.theme.load.resolve_theme` — the theme directory
            (``PPTXKIT_THEME_DIR``), then the packaged built-ins.
        out: Output ``.pptx``. Overrides the spec's ``out:``.
        keep_layouts: Keep the template's unused slide layouts and masters, and the
            media only they reach. Off by default — they are pruned.

    Returns:
        A :class:`BuildResult` naming the deck, the manifest, and the slide count.

    Raises:
        SpecError: the spec is malformed, or no output path was given.
        ThemeError: the theme or its template is missing or malformed.
        LayoutError: a placement names a component that cannot draw what it was given.
    """
    spec = parse_deck(spec_path)
    # load_theme first: it owns the message for a name or path that resolves to nothing.
    theme = load_theme(theme_path or spec.theme)
    theme_file = (Path(theme_path) if theme_path else resolve_theme(spec.theme)).resolve()

    dest = Path(out) if out else spec.out
    if dest is None:
        raise SpecError(
            f"{spec.source.name}: no output path — set 'out:' in the deck config or pass --out"
        )

    prs = _presentation(theme)
    _drop_template_slides(prs, theme)
    flatten_master_background(prs, _rgb(theme.palette.pair("page").bg))
    blank = pick_compose_layout(prs, prefer=theme.compose_layout)

    manifest = ManifestRecorder(
        deck=str(dest),
        theme=theme.name,
        theme_hash=theme.hash,
        slide_w=theme.grid.slide_w,
        slide_h=theme.grid.slide_h,
        theme_path=str(theme_file),
        compose_layout=blank.name,
    )

    for slide_spec in spec.slides:
        slide = prs.slides.add_slide(blank)
        manifest.begin_slide(
            slide_spec.index,
            background=slide_spec.background.pair,
            section=slide_spec.section,
            notes=slide_spec.notes,
        )
        ctx = SlideCtx(
            slide=slide,
            theme=theme,
            spec=slide_spec,
            manifest=manifest,
            sections=spec.sections,
            base=spec.source.resolve().parent,
        )
        render_slide(ctx)
        if slide_spec.notes:
            set_notes(slide, slide_spec.notes)

    if not keep_layouts:
        prune_unused_layouts(prs)
    register_notes_master(prs)

    dest.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    prs.save(buf)
    payload = buf.getvalue()
    atomic_write_bytes(dest, payload)
    spec_hash = _digest(spec.source.read_bytes())
    _keep_source(spec.source, dest)
    manifest.provenance = Provenance(
        build_id=_digest(spec_hash.encode(), theme.hash.encode(), _version().encode()),
        pptxkit=_version(),
        spec=str(spec.source),
        spec_hash=spec_hash,
        deck_hash=_digest(payload),
    )
    manifest_path = manifest.write(dest.with_suffix(".manifest.json"))
    write_content(manifest.to_dict(), dest.with_suffix(".content.md"))
    logger.info("deck_built", deck=str(dest), slides=len(spec.slides), theme=theme.name)
    return BuildResult(deck=dest, manifest=manifest_path, slides=len(spec.slides))


def _presentation(theme: Theme):
    """The deck's starting file: the theme's template, or a blank canvas if it names none."""
    if theme.template is None:
        return blank_presentation(slide_w=theme.scale.slide_w, slide_h=theme.scale.slide_h)
    return open_presentation(theme.template)


def _drop_template_slides(prs, theme: Theme) -> None:
    """Remove the template's own sample slides, newest index first."""
    if not theme.drop_template_slides:
        return
    for index in reversed(range(len(prs.slides._sldIdLst))):
        delete_slide(prs, index)


def _keep_source(source: Path, dest: Path) -> None:
    """Copy the spec that made this deck in beside it, under ``.build/``.

    A spec edited between versions would otherwise leave its earlier builds
    unregenerable, in a directory labelled disposable.
    """
    kept = scratch(dest.parent) / f"{dest.stem}.deck.yaml"
    atomic_write_text(kept, source.read_text(encoding="utf-8"))


def _digest(*parts: bytes) -> str:
    """Short content id, in ``theme/load.py``'s convention."""
    h = hashlib.sha256()
    for part in parts:
        h.update(part)
    return h.hexdigest()[:16]


def _version() -> str:
    """The pptxkit that wrote this manifest, so an old one is recognisable as old."""
    try:
        return metadata.version("pptxkit")
    except metadata.PackageNotFoundError:
        # Running from a source tree with nothing installed; recorded, not guessed.
        return "unknown"


def _rgb(hex_value: str) -> tuple[int, int, int]:
    value = hex_value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
