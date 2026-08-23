"""Compile a deck spec into a .pptx plus its build manifest."""

from pptxkit.compile.build import BuildResult, build_deck
from pptxkit.compile.record import ShapeRecord, SlideRecord
from pptxkit.compile.manifest import ManifestRecorder

__all__ = ["BuildResult", "ManifestRecorder", "ShapeRecord", "SlideRecord", "build_deck"]
