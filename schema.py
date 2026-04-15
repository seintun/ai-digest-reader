"""Typed contract for Claude AI summary output. Single source of truth."""
from typing import TypedDict, List


class MustReadItem(TypedDict):
    id: str       # story reference e.g. "rd-0", "hn-2"
    title: str    # story title (plain text)
    url: str      # direct URL to story
    reason: str   # one sentence — why this matters


class FullBriefSection(TypedDict):
    heading: str  # section title (plain text, no markdown)
    body: str     # one paragraph (plain text, no markdown)


class FullBrief(TypedDict):
    intro: str                       # opening paragraph
    sections: List[FullBriefSection] # 2-4 sections
    closing: str                     # one-sentence takeaway


class Structured(TypedDict):
    themes: List[str]           # exactly 3 theme strings
    breaking: str               # most significant news, one sentence
    mustRead: List[MustReadItem] # exactly 3 items


class DigestSummary(TypedDict):
    schema_version: str  # always "2"
    simple: str          # 2-3 sentence plain text TL;DR
    structured: Structured
    fullBrief: FullBrief


def validate_summary(data: dict) -> bool:
    """
    Validates that data conforms to DigestSummary shape.
    Returns False on any missing key or wrong type.
    """
    try:
        assert data.get("schema_version") == "2"
        assert isinstance(data.get("simple"), str) and data["simple"]

        s = data.get("structured", {})
        assert isinstance(s.get("themes"), list) and len(s["themes"]) == 3
        assert all(isinstance(t, str) for t in s["themes"])
        assert isinstance(s.get("breaking"), str) and s["breaking"]
        assert isinstance(s.get("mustRead"), list) and len(s["mustRead"]) == 3
        for item in s["mustRead"]:
            assert all(k in item for k in ("id", "title", "url", "reason"))
            assert all(isinstance(item[k], str) for k in ("id", "title", "url", "reason"))

        fb = data.get("fullBrief", {})
        assert isinstance(fb.get("intro"), str) and fb["intro"]
        assert isinstance(fb.get("sections"), list) and len(fb["sections"]) >= 2
        for sec in fb["sections"]:
            assert isinstance(sec.get("heading"), str) and sec["heading"]
            assert isinstance(sec.get("body"), str) and sec["body"]
        assert isinstance(fb.get("closing"), str) and fb["closing"]

        return True
    except (AssertionError, AttributeError, TypeError):
        return False
