"""The declarative deck spec."""

from pptxkit.spec.model import Background, DeckSpec, Placement, SlideSpec
from pptxkit.spec.parse import parse_deck, parse_deck_text

__all__ = ["Background", "DeckSpec", "Placement", "SlideSpec", "parse_deck", "parse_deck_text"]
