"""What `pptxkit doctor` attests, and the statuses it must not confuse: a missing external tool is a
fact about this machine, a broken install is something to fix — and a check that FAILs on an absent
LibreOffice would make `bin/setup` fail on a machine that never needed it."""

from __future__ import annotations

import re

import pytest

from pptxkit import doctor


def test_a_missing_external_tool_warns_and_never_fails(monkeypatch):
    """`bin/setup` runs doctor. If absence were FAIL, setup would refuse to finish on
    a perfectly good machine that only ever builds decks."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setenv("PPTXKIT_SOFFICE", "/nope/soffice")
    monkeypatch.setenv("PPTXKIT_PDFTOPPM", "/nope/pdftoppm")
    monkeypatch.setenv("PPTXKIT_PDFTOTEXT", "/nope/pdftotext")
    monkeypatch.setenv("PPTXKIT_CHROME", "")
    monkeypatch.setattr("pptxkit.services.htmlshot.os.path.exists", lambda _: False)

    results = doctor.check_tools()
    assert {r.name for r in results} == {"soffice", "pdftoppm", "pdftotext", "chrome"}
    assert {r.status for r in results} == {"WARN"}


def test_every_missing_tool_names_a_command_that_installs_it(monkeypatch):
    """A warning nobody can act on gets scrolled past."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr("pptxkit.services.htmlshot.os.path.exists", lambda _: False)
    monkeypatch.setenv("PPTXKIT_CHROME", "")
    for result in doctor.check_tools():
        assert "brew " in result.detail or "apt-get " in result.detail, result.detail


def test_a_chrome_path_that_is_not_there_warns_rather_than_passing(monkeypatch):
    """PPTXKIT_CHROME short-circuits the probe, so the path it names is the one nothing
    else looks at before a build reaches for it."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setenv("PPTXKIT_CHROME", "/nonexistent/chrome")
    chrome = next(r for r in doctor.check_tools() if r.name == "chrome")
    assert chrome.status == "WARN"
    assert "not found (/nonexistent/chrome)" in chrome.detail


def test_the_table_reports_the_version_that_answered():
    """A bug report starts with which pptxkit built the deck."""
    rows = {(r.group, r.name): r for r in doctor.run_checks()}
    version = rows[("pptxkit", "version")]
    assert version.status == "PASS"
    assert re.match(r"\d+\.\d+", version.detail)


def test_a_broken_glyph_bundle_fails_rather_than_warns(monkeypatch):
    """This one *is* the install being wrong, and it is the check bin/setup acts on."""
    monkeypatch.setattr("pptxkit.icons.vendor.verify", lambda *a, **k: ["3 glyph(s) do not match"])
    result = doctor.check_glyphs()
    assert result.status == "FAIL"
    assert "glyphs sync" in result.detail


def test_an_intact_bundle_reports_the_upstream_it_is_pinned_to():
    result = doctor.check_glyphs()
    assert result.status == "PASS"
    assert "glyphs @" in result.detail


def _as_checkout(path):
    """Make `path` look like pptxkit's own source tree, not just any Python project."""
    (path / "pyproject.toml").write_text('[project]\nname = "pptxkit"\n', encoding="utf-8")


def test_an_empty_corpus_skips_and_says_what_that_costs(tmp_path, monkeypatch):
    """A green suite without the corpus proves almost nothing, and doctor is where
    that becomes visible before the tests run rather than after."""
    monkeypatch.chdir(tmp_path)
    _as_checkout(tmp_path)
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(tmp_path / "templates"))
    (tmp_path / "templates").mkdir()
    result = doctor.check_corpus()
    assert result.status == "SKIP"
    assert "unit tests only" in result.detail


def test_outside_a_checkout_the_corpus_check_names_something_the_reader_has(tmp_path, monkeypatch):
    """A wheel carries neither tests/test_templates.py nor templates/README.md."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(tmp_path / "templates"))
    result = doctor.check_corpus()
    assert result.status == "SKIP"
    assert "pptxkit conform" in result.detail
    assert "tests/" not in result.detail
    assert "README" not in result.detail


def test_a_populated_corpus_passes(tmp_path, monkeypatch, synthetic_template):
    # Its own directory: `synthetic_template` writes into tmp_path too, and a corpus
    # of "however many files the fixtures happened to leave" measures nothing.
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(corpus))
    (corpus / "brand.pptx").write_bytes(synthetic_template.read_bytes())
    result = doctor.check_corpus()
    assert result.status == "PASS"
    assert "1 template" in result.detail


def test_the_builtin_theme_resolves_with_no_theme_directory(tmp_path, monkeypatch):
    """The packaged fallback is what makes an install with no theme dir able to build."""
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(tmp_path / "nothing-here"))
    result = doctor.check_theme()
    assert result.status == "PASS"
    assert "packaged" in result.detail


def test_a_foreign_file_at_the_sample_path_is_left_alone(tmp_path, monkeypatch, synthetic_template):
    """Setup never overwrites it, so doctor's job is to say it is not ours."""
    monkeypatch.chdir(tmp_path)
    _as_checkout(tmp_path)
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(tmp_path / "templates"))
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "sample.pptx").write_bytes(synthetic_template.read_bytes())
    result = doctor.check_sample()
    assert result.status == "WARN"
    assert "not the generated sample" in result.detail


def test_outside_a_checkout_the_sample_check_skips(tmp_path, monkeypatch):
    """A pip user has no templates/ and should not be told they are missing one."""
    monkeypatch.chdir(tmp_path)
    result = doctor.check_sample()
    assert result.status == "SKIP"


@pytest.mark.parametrize("status", ["PASS", "WARN", "SKIP"])
def test_only_a_fail_sets_a_non_zero_exit(status):
    """setup runs `doctor || true`, but CI will not — so the code has to mean this."""
    from pf_core.doctor import CheckResult

    assert doctor.report([CheckResult("g", "n", status, "d")]) == 0
    assert doctor.report([CheckResult("g", "n", "FAIL", "d")]) == 1
