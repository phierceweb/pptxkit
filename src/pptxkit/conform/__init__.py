"""Drive a brand template through every capability and report what it can carry."""

from pptxkit.conform.adopt import Adoption, install, plan
from pptxkit.conform.derive import derive, notes
from pptxkit.conform.run import Conformance, conform

__all__ = ["Adoption", "Conformance", "conform", "derive", "install", "notes", "plan"]
