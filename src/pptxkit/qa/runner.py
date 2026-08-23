"""Run every QA check over a built deck and its manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pf_core.log import get_logger

from pptxkit.errors import SpecError
from pptxkit.paths import render_dir
from pptxkit.qa.geometry import (
    check_bounds,
    check_placement_fit,
    check_contrast,
    check_reserved,
    check_text_fit,
    check_type_sizes,
)
from pptxkit.qa.imagery import check_render_contrast
from pptxkit.qa.model import Finding, QaReport, Severity
from pptxkit.qa.package import check_package
from pptxkit.qa.report import write_json, write_markdown
from pptxkit.qa.textflow import check_overflow, extract_pages
from pptxkit.services.render import render_to_images
from pptxkit.theme import load_theme

logger = get_logger(__name__)


def _theme_file(given: str | Path | None, recorded: Any, manifest_path: Path) -> Path | None:
    """The theme to check against: the caller's, else the manifest's own.

    A recorded path is written relative to the manifest, so it resolves against the
    manifest rather than the working directory. An absolute one — an older manifest, or
    a build whose theme shared no ancestor with its output — is used as written.
    """
    if given:
        return Path(given)
    if not recorded:
        return None
    path = Path(recorded)
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def _stale_manifest(deck: Path, data: dict, manifest_path: Path) -> list[Finding]:
    """Does this manifest still describe this file?

    Every check below believes the manifest, so a deck hand-edited after the build makes
    the findings describe a file that is gone. A warning, not an error: the hand-edit is a
    sanctioned workflow.
    """
    recorded = data.get("deck_hash")
    if not recorded:
        return []
    actual = hashlib.sha256(deck.read_bytes()).hexdigest()[: len(recorded)]
    if actual == recorded:
        return []
    return [
        Finding(
            slide=0,
            check="stale-manifest",
            severity=Severity.WARN,
            detail=(
                f"{deck.name} has changed since it was built — {manifest_path.name} "
                f"records {recorded}, the file is {actual}. Every other finding below "
                f"describes the build, not this file; rebuild to check what you have"
            ),
        )
    ]


def run_qa(
    deck: str | Path,
    *,
    manifest: str | Path | None = None,
    theme_path: str | Path | None = None,
    render: bool = True,
    outdir: str | Path | None = None,
) -> QaReport:
    """Check ``deck`` against its manifest and, unless ``render`` is False, its render.

    Raises:
        SpecError: the manifest is missing or names no theme.
        ThemeError: the theme or its template cannot be loaded.
        RenderError: the render or text extraction failed.
    """
    deck = Path(deck)
    manifest_path = Path(manifest) if manifest else deck.with_suffix(".manifest.json")
    if not manifest_path.is_file():
        raise SpecError(f"manifest not found: {manifest_path} — build the deck first")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    theme_file = _theme_file(theme_path, data.get("theme_path"), manifest_path)
    if not theme_file:
        raise SpecError(f"{manifest_path.name}: no theme_path recorded — pass --theme")
    theme = load_theme(theme_file)

    findings: list[Finding] = []
    findings.extend(_stale_manifest(deck, data, manifest_path))
    if not data.get("slides"):
        findings.append(
            Finding(
                slide=0,
                check="empty-manifest",
                severity=Severity.WARN,
                detail=f"{manifest_path.name} records no slides — nothing was checked",
            )
        )
    for check in (
        check_bounds,
        check_placement_fit,
        check_reserved,
        check_type_sizes,
        check_contrast,
        check_text_fit,
    ):
        findings.extend(check(data, theme))
    # Reads the saved package, not the manifest: this is the one check that
    # answers whether PowerPoint will open the file at all.
    findings.extend(check_package(deck))

    out = Path(outdir) if outdir else render_dir(deck)
    if render:
        images = render_to_images(deck, out)
        pdf = out / f"{deck.stem}.pdf"
        findings.extend(check_overflow(data, extract_pages(pdf), extract_pages(pdf, layout=True)))
        findings.extend(check_render_contrast(data, images))
        logger.info("qa_rendered", slides=len(images))

    findings.sort(key=lambda f: (f.slide, -f.severity.rank, f.check))
    report = QaReport(deck=str(deck), findings=tuple(findings))
    write_markdown(report, out / "qa.md")
    write_json(report, out / "qa.json")
    logger.info("qa_done", deck=str(deck), findings=len(findings))
    return report
