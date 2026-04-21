"""Typed contract for Claude AI summary output. Single source of truth."""
from typing import Any, TypedDict, List


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


def validate_summary(data: Any) -> bool:
    """
    Validates that data conforms to DigestSummary shape.
    Returns False on any missing key or wrong type.
    """
    try:
        if not isinstance(data, dict):
            return False

        if data.get("schema_version") != "2":
            return False

        simple = data.get("simple")
        if not isinstance(simple, str) or not simple:
            return False

        structured = data.get("structured")
        if not isinstance(structured, dict):
            return False

        themes = structured.get("themes")
        if not isinstance(themes, list) or len(themes) != 3:
            return False
        if any(not isinstance(theme, str) for theme in themes):
            return False

        breaking = structured.get("breaking")
        if not isinstance(breaking, str) or not breaking:
            return False

        must_read = structured.get("mustRead")
        if not isinstance(must_read, list) or len(must_read) != 3:
            return False
        for item in must_read:
            if not isinstance(item, dict):
                return False
            for key in ("id", "title", "url", "reason"):
                value = item.get(key)
                if not isinstance(value, str):
                    return False

        full_brief = data.get("fullBrief")
        if not isinstance(full_brief, dict):
            return False

        intro = full_brief.get("intro")
        if not isinstance(intro, str) or not intro:
            return False

        sections = full_brief.get("sections")
        if not isinstance(sections, list) or len(sections) < 2 or len(sections) > 4:
            return False
        for section in sections:
            if not isinstance(section, dict):
                return False
            heading = section.get("heading")
            body = section.get("body")
            if not isinstance(heading, str) or not heading:
                return False
            if not isinstance(body, str) or not body:
                return False

        closing = full_brief.get("closing")
        if not isinstance(closing, str) or not closing:
            return False

        return True
    except (AttributeError, TypeError):
        return False


# v3 schema additions
SCHEMA_VERSION = "3"


def validate_v3_digest(digest: Any) -> bool:
    """Validate top-level structure of a v3 digest envelope."""
    required = {"v", "d", "g", "r", "h"}
    if not all(k in digest for k in required):
        return False
    if digest.get("v") != 3:
        return False
    return True
