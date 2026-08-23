"""Deterministic QA over a built deck and its manifest."""

from pptxkit.qa.inspect import inspect_deck
from pptxkit.qa.model import Finding, QaReport, Severity
from pptxkit.qa.runner import run_qa

__all__ = ["Finding", "QaReport", "Severity", "inspect_deck", "run_qa"]
