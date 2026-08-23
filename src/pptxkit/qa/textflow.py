"""Extract the text a rendered deck actually contains, and diff it against intent.

Config (env, read at call time, so ``.env`` changes take effect between runs):

- ``PPTXKIT_PDFTOTEXT``           — the pdftotext command (default ``pdftotext``).
- ``PPTXKIT_PDFTOTEXT_TIMEOUT_S`` — seconds before it is killed (default 60).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pf_core.log import get_logger
from pf_core.utils.env import resolve_int

from pptxkit.errors import RenderError
from pptxkit.compile.record import box_of
from pptxkit.qa.model import Finding, Severity
from pptxkit.utils.env import env_str

logger = get_logger(__name__)

_PDFTOTEXT_DEFAULT = "pdftotext"
_TIMEOUT_S_DEFAULT = 60


def extract_pages(
    pdf_path: str | Path,
    *,
    layout: bool = False,
    pdftotext: str | None = None,
    timeout: int | None = None,
) -> list[str]:
    """Return the text of each page of ``pdf_path``, in order.

    Both extraction modes are returned because each splits lines the other keeps whole:
    reading order on wide tracking, ``-layout`` on whatever sits beside a wrapped line.

    Raises:
        RenderError: the PDF is missing, or pdftotext failed or timed out.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise RenderError(f"PDF not found: {pdf_path}")
    binary = env_str(pdftotext, "PPTXKIT_PDFTOTEXT", default=_PDFTOTEXT_DEFAULT)
    timeout_s = resolve_int(timeout, "PPTXKIT_PDFTOTEXT_TIMEOUT_S", default=_TIMEOUT_S_DEFAULT)
    argv = [binary, *(["-layout"] if layout else []), str(pdf_path), "-"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=timeout_s)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise RenderError(f"pdftotext failed on {pdf_path}", cause=e) from e

    pages = result.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    logger.info("pdf_text_extracted", pdf=str(pdf_path), pages=len(pages))
    return pages


def normalise(text: str) -> str:
    """Collapse whitespace and casefold, so layout differences do not read as loss."""
    return " ".join(text.split()).casefold()


def _matchable(text: str) -> str:
    """Fold *text* for containment: normalised, then spacing and hyphens dropped.

    pdftotext rebuilds a line the renderer wrapped at a hyphen two ways — reading
    order deletes the hyphen ("non-text" -> "nontext"), -layout keeps it with the
    row break beside it ("non- text"). Ignoring spacing and hyphens erases both.
    """
    return normalise(text).replace(" ", "").replace("-", "")


def check_overflow(
    manifest: dict[str, Any], pages: list[str], alt_pages: list[str] | None = None
) -> list[Finding]:
    """Flag recorded text that did not survive into the rendered page.

    Text is missing only if absent from *both* extractions (see :func:`extract_pages`).
    ``rendered="image"`` records are skipped: a PDF extractor cannot see text in a picture.
    """
    slides = manifest.get("slides", [])
    if len(slides) != len(pages):
        return [
            Finding(
                slide=0,
                check="page-count",
                severity=Severity.ERROR,
                detail=f"manifest has {len(slides)} slide(s) but the render has {len(pages)} page(s)",
            )
        ]

    alt = alt_pages if alt_pages and len(alt_pages) == len(pages) else [""] * len(pages)
    findings: list[Finding] = []
    for slide, page, alt_page in zip(slides, pages, alt, strict=True):
        haystack = _matchable(page)
        alt_haystack = _matchable(alt_page)
        for shape in slide.get("shapes", []):
            if shape.get("rendered", "native") != "native":
                continue
            lines = shape.get("lines") or ([shape["text"]] if shape.get("text") else [])
            for line in lines:
                needle = _matchable(str(line))
                if needle and needle not in haystack and needle not in alt_haystack:
                    findings.append(
                        Finding(
                            slide=slide["index"],
                            check="overflow",
                            severity=Severity.ERROR,
                            detail=f"{str(line)[:70]!r} was not found in the rendered slide",
                            box=box_of(shape),
                            shape=shape.get("name"),
                        )
                    )
    return findings
