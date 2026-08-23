"""What a stranger sees when an external tool is missing.

Driven through a subprocess: the noise these guard against is written by the logging
handlers pf-core installs, which an in-process runner never exercises.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptxkit.cli import app


@pytest.fixture
def qa_without_libreoffice(clean_manifest_deck, tmp_path):
    deck, manifest = clean_manifest_deck
    env = {**os.environ, "COLUMNS": "300", "PPTXKIT_SOFFICE": "/nonexistent/soffice"}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pptxkit.cli",
            "qa",
            str(deck),
            "--manifest",
            str(manifest),
            "--outdir",
            str(tmp_path / "qa"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_a_missing_tool_prints_its_message_and_nothing_else(qa_without_libreoffice):
    output = qa_without_libreoffice.stdout + qa_without_libreoffice.stderr
    assert qa_without_libreoffice.returncode == 1
    assert "soffice not found (/nonexistent/soffice)" in output
    assert "Traceback" not in output
    assert "locals" not in output


def test_qa_names_the_flag_that_runs_without_the_tool(qa_without_libreoffice):
    """Every check but overflow and render contrast needs no binary at all."""
    assert "--no-render" in qa_without_libreoffice.stdout + qa_without_libreoffice.stderr


def test_the_version_flag_prints_the_installed_version():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith("pptxkit ")


def test_sample_writes_where_adopt_will_accept_it(tmp_path, monkeypatch):
    """`sample` prints a `conform ... --adopt` line as the next step, and adopt refuses
    a template outside the theme directory (test_conform_adopt.py) — so writing beside
    the caller printed a command that always exited 1."""
    monkeypatch.chdir(tmp_path)
    theme_root = tmp_path / "brand"
    monkeypatch.setenv("PPTXKIT_THEME_DIR", str(theme_root))

    result = CliRunner().invoke(app, ["sample"])

    assert result.exit_code == 0, result.stdout
    written = theme_root / "sample.pptx"
    assert written.is_file()

    hint = [ln for ln in result.stdout.splitlines() if "--adopt" in ln]
    assert hint, result.stdout
    quoted = hint[0].split("conform", 1)[1].split("--adopt")[0].strip()
    assert Path(quoted).resolve().parent == theme_root.resolve()
