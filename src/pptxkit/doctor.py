"""Attest what this pptxkit can actually do, before something needs it.

**Read-only, always** — nothing here writes, installs or fetches. A missing external
tool is a **WARN, never a FAIL**; only a broken *install* fails.
"""

from __future__ import annotations

import shutil
import sys
from importlib import metadata
from pathlib import Path

from pf_core.doctor import CheckResult

from pptxkit.compile.build import resolve_theme, theme_dir
from pptxkit.paths import in_checkout
from pptxkit.services.render import install_hint
from pptxkit.utils.env import env_str

_TOOLS = (
    ("soffice", "PPTXKIT_SOFFICE", "soffice", "render, and QA's render-based checks"),
    ("pdftoppm", "PPTXKIT_PDFTOPPM", "pdftoppm", "render, and QA's render-based checks"),
    ("pdftotext", "PPTXKIT_PDFTOTEXT", "pdftotext", "QA's overflow check"),
)


def _sample_path() -> Path:
    """Where `pptxkit sample` writes, resolved now — the theme dir is env-tunable."""
    return theme_dir() / "sample.pptx"


def installed_version() -> str:
    """The version of the installed distribution, or a marker for an uninstalled tree."""
    try:
        return metadata.version("pptxkit")
    except metadata.PackageNotFoundError:
        return "0.0.0.dev0"


def _present(binary: str) -> str | None:
    """The binary's path if it is on PATH or is a file, else None."""
    return shutil.which(binary) or (binary if Path(binary).is_file() else None)


def check_version() -> CheckResult:
    """Which pptxkit answered — the first thing a bug report needs."""
    return CheckResult("pptxkit", "version", "PASS", installed_version())


def check_glyphs() -> CheckResult:
    """The shipped icon set is present and matches the manifest pinning it."""
    from pptxkit.icons import vendor

    problems = vendor.verify()
    if problems:
        return CheckResult("glyphs", "bundle", "FAIL", f"{problems[0]} — run 'pptxkit glyphs sync'")
    ref, hashes = vendor.read_manifest()
    return CheckResult("glyphs", "bundle", "PASS", f"{len(hashes):,} glyphs @ {ref[:12]}")


def check_theme() -> CheckResult:
    """`theme: base` resolves — from the theme directory, or the packaged fallback."""
    resolved = resolve_theme("base")
    if not resolved.is_file():
        return CheckResult(
            "theme", "builtin", "FAIL", f"'base' resolves to {resolved}, which is not there"
        )
    where = "packaged" if "builtin" in resolved.parts else f"{theme_dir()}"
    return CheckResult("theme", "builtin", "PASS", f"base resolves ({where})")


def check_sample() -> CheckResult:
    """The generated onboarding template, for anyone following docs/conform.md."""
    sample = _sample_path()
    if not in_checkout():
        return CheckResult(
            "sample", "template", "SKIP", "not a source checkout — 'pptxkit sample' writes one"
        )
    if not sample.is_file():
        return CheckResult(
            "sample", "template", "WARN", f"no {sample} — run 'pptxkit sample' (bin/setup does)"
        )
    from pptxkit.conform.sample import is_sample

    if not is_sample(sample):
        return CheckResult(
            "sample", "template", "WARN", f"{sample} is not the generated sample — left alone"
        )
    return CheckResult("sample", "template", "PASS", str(sample))


def check_corpus() -> CheckResult:
    """Whether the brand-variance guard can run at all on this machine."""
    from pptxkit.conform.sample import is_sample

    templates = theme_dir()
    found = (
        [p for p in sorted(templates.glob("*.pptx")) if not is_sample(p)]
        if templates.is_dir()
        else []
    )
    if not found and not in_checkout():
        return CheckResult(
            "templates",
            "brands",
            "SKIP",
            "no brand template — 'pptxkit conform <brand>.pptx "
            "--adopt <name>' derives a theme from one",
        )
    if not found:
        return CheckResult(
            "templates",
            "brands",
            "SKIP",
            "no brand template — tests/test_templates.py skips, so a "
            "green suite is the unit tests only (templates/README.md)",
        )
    return CheckResult(
        "templates", "brands", "PASS", f"{len(found)} template(s) — the variance guard runs"
    )


def check_tools() -> list[CheckResult]:
    """Each external binary, resolved exactly as the runtime resolves it."""
    out = []
    for tool, env_var, default, needed_by in _TOOLS:
        binary = env_str(None, env_var, default=default)
        found = _present(binary)
        if found:
            out.append(CheckResult("tools", tool, "PASS", found))
        else:
            out.append(
                CheckResult(
                    "tools",
                    tool,
                    "WARN",
                    f"not found ({binary}) — needed by {needed_by}; {install_hint(tool)}",
                )
            )
    from pptxkit.errors import MissingToolError
    from pptxkit.services.htmlshot import _resolve_chrome

    chrome_needs = "needed by shot and any 'document:' slide"
    try:
        chrome = _resolve_chrome(None)
    except MissingToolError:
        out.append(
            CheckResult(
                "tools", "chrome", "WARN", f"none found — {chrome_needs}; {install_hint('chrome')}"
            )
        )
        return out
    found = _present(chrome)
    if found:
        out.append(CheckResult("tools", "chrome", "PASS", found))
    else:
        out.append(
            CheckResult(
                "tools",
                "chrome",
                "WARN",
                f"not found ({chrome}) — {chrome_needs}; {install_hint('chrome')}",
            )
        )
    return out


def run_checks() -> list[CheckResult]:
    """Every check, in the order a reader wants them."""
    results = [check_version(), check_glyphs(), check_theme(), check_sample(), check_corpus()]
    results.extend(check_tools())
    return results


def report(results: list[CheckResult]) -> int:
    """Print the table the way pf-doctor does. Returns the exit code."""
    from rich.console import Console
    from rich.table import Table

    table = Table(title="pptxkit doctor", show_lines=False)
    table.add_column("status", no_wrap=True)
    table.add_column("check", no_wrap=True)
    table.add_column("detail", overflow="fold")
    styles = {"PASS": "green", "WARN": "yellow", "FAIL": "red", "SKIP": "dim"}
    for r in results:
        table.add_row(f"[{styles[r.status]}]{r.status}[/]", f"{r.group}.{r.name}", r.detail)
    console = Console()
    console.print(table)
    counts = {s: sum(1 for r in results if r.status == s) for s in styles}
    console.print(
        f"{counts['PASS']} pass, {counts['WARN']} warn, "
        f"{counts['FAIL']} fail, {counts['SKIP']} skip"
    )
    return 1 if counts["FAIL"] else 0


def main() -> int:
    return report(run_checks())


if __name__ == "__main__":
    sys.exit(main())
