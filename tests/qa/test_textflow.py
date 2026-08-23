from pptxkit.qa.model import Severity
from pptxkit.qa.textflow import check_overflow, normalise


def _manifest(*slides):
    return {"deck": "d.pptx", "slides": list(slides)}


def _slide(index, *records, layout="content"):
    return {"index": index, "layout": layout, "shapes": list(records)}


def _rec(text=None, lines=None, rendered="native"):
    return {
        "shape_id": 2,
        "name": "Box",
        "box": dict(zip("xywh", (1, 1, 2, 1), strict=True)),
        "text": text,
        "lines": lines or [],
        "font_pt": None,
        "fg": None,
        "bg": None,
        "rendered": rendered,
    }


def test_normalise_collapses_whitespace_and_case():
    assert normalise("  Hello   WORLD \n") == "hello world"


def test_text_present_on_the_page_is_clean():
    m = _manifest(_slide(1, _rec(lines=["Alpha", "Beta"])))
    assert check_overflow(m, ["alpha beta gamma"]) == []


def test_a_missing_line_is_an_error():
    m = _manifest(_slide(1, _rec(lines=["Alpha", "Beta"])))
    findings = check_overflow(m, ["Alpha only"])
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].check == "overflow"
    assert "Beta" in findings[0].detail


def test_whitespace_differences_do_not_trip_it():
    m = _manifest(_slide(1, _rec(lines=["Complexity  ·  Consistency"])))
    assert check_overflow(m, ["Complexity · Consistency"]) == []


def test_image_rendered_records_are_skipped():
    m = _manifest(_slide(1, _rec(lines=["inside a panel"], rendered="image")))
    assert check_overflow(m, ["nothing here"]) == []


def test_a_record_with_only_text_falls_back_to_it():
    m = _manifest(_slide(1, _rec(text="Solo")))
    assert check_overflow(m, ["nothing"])[0].detail.count("Solo") == 1


def test_empty_and_whitespace_lines_are_ignored():
    m = _manifest(_slide(1, _rec(lines=["", "   "])))
    assert check_overflow(m, [""]) == []


def test_each_slide_is_matched_to_its_own_page():
    m = _manifest(_slide(1, _rec(lines=["one"])), _slide(2, _rec(lines=["two"])))
    assert check_overflow(m, ["one", "two"]) == []
    findings = check_overflow(m, ["two", "one"])
    assert {f.slide for f in findings} == {1, 2}


def test_a_page_count_mismatch_is_reported_once():
    m = _manifest(_slide(1, _rec(lines=["one"])), _slide(2, _rec(lines=["two"])))
    findings = check_overflow(m, ["one"])
    assert len(findings) == 1
    assert findings[0].slide == 0
    assert findings[0].check == "page-count"
    # A page-count mismatch means the render and the manifest disagree about how many
    # slides exist, so every later per-slide finding is aligned against the wrong page.
    assert findings[0].severity is Severity.ERROR


def test_a_duplicate_line_is_reported_once_per_record():
    m = _manifest(_slide(1, _rec(lines=["gone", "gone"])))
    assert len(check_overflow(m, ["nothing"])) == 2


def test_normalise_preserves_punctuation_and_glyphs():
    assert normalise("•  Alpha") == "•  alpha".replace("  ", " ")
    assert normalise("A · B") == "a · b"


def test_a_swapped_glyph_is_still_detected():
    m = _manifest(_slide(1, _rec(lines=["•  Alpha"])))
    assert len(check_overflow(m, ["※  Alpha"])) == 1


def test_text_found_only_in_the_alternate_extraction_is_not_flagged():
    """Each pdftotext mode splits lines the other keeps whole; either alone false-positives."""
    manifest = _manifest(_slide(1, _rec(lines=["wrapped label here"])))
    assert (
        check_overflow(manifest, ["wrapped label\nother column\nhere"], ["wrapped label here"])
        == []
    )


def test_text_missing_from_both_extractions_is_flagged():
    manifest = _manifest(_slide(1, _rec(lines=["gone"])))
    findings = check_overflow(manifest, ["nothing"], ["nothing either"])
    assert [f.check for f in findings] == ["overflow"]
    assert findings[0].severity is Severity.ERROR


def test_a_missing_alternate_extraction_is_tolerated():
    manifest = _manifest(_slide(1, _rec(lines=["present"])))
    assert check_overflow(manifest, ["present"]) == []


def test_a_line_wrapped_at_its_hyphen_survives_dehyphenation():
    """Reading order rejoins a word wrapped at its hyphen by deleting the hyphen."""
    m = _manifest(_slide(1, _rec(lines=["it must clear the 3:1 non-text minimum."])))
    assert check_overflow(m, ["it must clear the 3:1 nontext minimum."]) == []


def test_a_hyphen_kept_at_a_row_break_in_the_alternate_extraction():
    """-layout keeps the wrap hyphen at the row end, with a break where the wrap was."""
    m = _manifest(_slide(1, _rec(lines=["it must clear the 3:1 non-text minimum."])))
    assert (
        check_overflow(
            m, ["unrelated reading-order text"], ["it must clear the 3:1 non-\ntext minimum."]
        )
        == []
    )


def test_a_line_clipped_at_its_hyphen_is_still_flagged():
    """Real overflow that truncates at the hyphen is loss, not a wrap artifact."""
    m = _manifest(_slide(1, _rec(lines=["it must clear the 3:1 non-text minimum."])))
    findings = check_overflow(m, ["it must clear the 3:1 non-"])
    assert [f.check for f in findings] == ["overflow"]
