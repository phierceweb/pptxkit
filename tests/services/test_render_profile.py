"""LibreOffice's shared user profile, and why each render needs its own. soffice locks one profile
directory: a second conversion starting while the first holds it exits 0 having converted nothing,
so it surfaces as a missing PDF. Asserted on the argv rather than by racing real conversions."""

from __future__ import annotations

import subprocess

import pytest

from pptxkit.services import render as render_mod


@pytest.fixture
def captured(monkeypatch, tmp_path):
    """Run render_to_images against a fake soffice, returning the argv it was given."""
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        # The converter is expected to leave a PDF behind; make one so the code
        # under test proceeds to the point we are asserting about.
        (tmp_path / "deck.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(render_mod.subprocess, "run", fake_run)
    return calls


def _render(tmp_path):
    """Drive one render. Both subprocesses are faked, so it produces no images —
    the argv is what these tests read, not the output."""
    deck = tmp_path / "deck.pptx"
    deck.write_bytes(b"not really a deck")
    render_mod.render_to_images(deck, tmp_path)


def test_each_conversion_gets_a_user_profile_of_its_own(captured, tmp_path):
    _render(tmp_path)
    assert captured, "soffice was never invoked"
    profiles = [a for a in captured[0] if a.startswith("-env:UserInstallation=")]
    assert profiles, captured[0]


def test_two_conversions_do_not_share_a_profile(captured, tmp_path):
    """Sharing is the whole failure: one directory, one lock, one silent no-op."""
    _render(tmp_path)
    _render(tmp_path)
    # `captured` holds the rasterizer's argv too; only the converter takes a profile.
    used = [a for call in captured for a in call if a.startswith("-env:UserInstallation=")]
    assert len(used) == 2 and used[0] != used[1], used


def test_the_profile_is_a_file_url(captured, tmp_path):
    """soffice ignores a bare path here, silently falling back to the shared profile."""
    _render(tmp_path)
    profile = next(a for a in captured[0] if a.startswith("-env:UserInstallation="))
    assert profile.startswith("-env:UserInstallation=file://"), profile


def test_the_profile_directory_does_not_outlive_the_render(captured, tmp_path):
    """A temp profile per render leaks a directory per render unless it is cleaned."""
    import pathlib

    _render(tmp_path)
    profile = next(a for a in captured[0] if a.startswith("-env:UserInstallation="))
    path = pathlib.Path(profile.split("file://", 1)[1])
    assert not path.exists(), path
