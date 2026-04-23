from schema import validate_summary


def make_valid_summary(**overrides):
    base = {
        "schema_version": "2",
        "simple": "Test summary.",
        "structured": {
            "themes": ["A", "B", "C"],
            "breaking": "Big news.",
            "mustRead": [
                {"id": "rd-0", "title": "T1", "url": "https://a.com", "reason": "R1"},
                {"id": "hn-1", "title": "T2", "url": "https://b.com", "reason": "R2"},
                {"id": "rd-2", "title": "T3", "url": "https://c.com", "reason": "R3"},
            ]
        },
        "fullBrief": {
            "intro": "Intro.",
            "sections": [
                {"heading": "S1", "body": "Body 1."},
                {"heading": "S2", "body": "Body 2."},
            ],
            "closing": "Closing."
        }
    }
    base.update(overrides)
    return base


def test_valid_summary_passes():
    assert validate_summary(make_valid_summary()) is True


# schema_version tests
def test_schema_version_wrong_string_fails():
    d = make_valid_summary(schema_version="1")
    assert validate_summary(d) is False


def test_schema_version_missing_fails():
    d = make_valid_summary()
    del d["schema_version"]
    assert validate_summary(d) is False


def test_schema_version_integer_fails():
    d = make_valid_summary(schema_version=2)
    assert validate_summary(d) is False


# simple field tests
def test_simple_empty_string_fails():
    d = make_valid_summary(simple="")
    assert validate_summary(d) is False


def test_simple_missing_fails():
    d = make_valid_summary()
    del d["simple"]
    assert validate_summary(d) is False


def test_simple_non_string_fails():
    d = make_valid_summary(simple=123)
    assert validate_summary(d) is False


def test_simple_none_fails():
    d = make_valid_summary(simple=None)
    assert validate_summary(d) is False


# structured / themes tests
def test_themes_fewer_than_3_fails():
    d = make_valid_summary()
    d["structured"]["themes"] = ["A", "B"]
    assert validate_summary(d) is False


def test_themes_more_than_3_fails():
    d = make_valid_summary()
    d["structured"]["themes"] = ["A", "B", "C", "D"]
    assert validate_summary(d) is False


def test_themes_non_string_item_fails():
    d = make_valid_summary()
    d["structured"]["themes"] = ["A", "B", 3]
    assert validate_summary(d) is False


def test_themes_missing_fails():
    d = make_valid_summary()
    del d["structured"]["themes"]
    assert validate_summary(d) is False


# breaking tests
def test_breaking_empty_string_fails():
    d = make_valid_summary()
    d["structured"]["breaking"] = ""
    assert validate_summary(d) is False


def test_breaking_missing_fails():
    d = make_valid_summary()
    del d["structured"]["breaking"]
    assert validate_summary(d) is False


def test_breaking_none_fails():
    d = make_valid_summary()
    d["structured"]["breaking"] = None
    assert validate_summary(d) is False


# mustRead tests
def test_must_read_fewer_than_3_fails():
    d = make_valid_summary()
    d["structured"]["mustRead"] = d["structured"]["mustRead"][:2]
    assert validate_summary(d) is False


def test_must_read_more_than_3_fails():
    d = make_valid_summary()
    d["structured"]["mustRead"].append(
        {"id": "hn-3", "title": "T4", "url": "https://d.com", "reason": "R4"}
    )
    assert validate_summary(d) is False


def test_must_read_missing_id_fails():
    d = make_valid_summary()
    item = d["structured"]["mustRead"][0].copy()
    del item["id"]
    d["structured"]["mustRead"][0] = item
    assert validate_summary(d) is False


def test_must_read_missing_title_fails():
    d = make_valid_summary()
    item = d["structured"]["mustRead"][0].copy()
    del item["title"]
    d["structured"]["mustRead"][0] = item
    assert validate_summary(d) is False


def test_must_read_missing_url_fails():
    d = make_valid_summary()
    item = d["structured"]["mustRead"][0].copy()
    del item["url"]
    d["structured"]["mustRead"][0] = item
    assert validate_summary(d) is False


def test_must_read_missing_reason_fails():
    d = make_valid_summary()
    item = d["structured"]["mustRead"][0].copy()
    del item["reason"]
    d["structured"]["mustRead"][0] = item
    assert validate_summary(d) is False


def test_must_read_non_string_value_fails():
    d = make_valid_summary()
    d["structured"]["mustRead"][0] = {
        "id": "rd-0", "title": "T1", "url": "https://a.com", "reason": 42
    }
    assert validate_summary(d) is False


# fullBrief as wrong type
def test_full_brief_as_string_fails():
    d = make_valid_summary(fullBrief="old schema string")
    assert validate_summary(d) is False


# fullBrief.sections tests
def test_full_brief_only_one_section_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [{"heading": "S1", "body": "Body 1."}]
    assert validate_summary(d) is False


def test_full_brief_empty_sections_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = []
    assert validate_summary(d) is False


def test_full_brief_sections_missing_heading_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"body": "Body 1."},
        {"heading": "S2", "body": "Body 2."},
    ]
    assert validate_summary(d) is False


def test_full_brief_sections_missing_body_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"heading": "S1"},
        {"heading": "S2", "body": "Body 2."},
    ]
    assert validate_summary(d) is False


def test_full_brief_sections_empty_heading_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"heading": "", "body": "Body 1."},
        {"heading": "S2", "body": "Body 2."},
    ]
    assert validate_summary(d) is False


def test_full_brief_sections_empty_body_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"heading": "S1", "body": ""},
        {"heading": "S2", "body": "Body 2."},
    ]
    assert validate_summary(d) is False


# fullBrief.intro / closing tests
def test_full_brief_intro_missing_fails():
    d = make_valid_summary()
    del d["fullBrief"]["intro"]
    assert validate_summary(d) is False


def test_full_brief_intro_empty_fails():
    d = make_valid_summary()
    d["fullBrief"]["intro"] = ""
    assert validate_summary(d) is False


def test_full_brief_closing_missing_fails():
    d = make_valid_summary()
    del d["fullBrief"]["closing"]
    assert validate_summary(d) is False


def test_full_brief_closing_empty_fails():
    d = make_valid_summary()
    d["fullBrief"]["closing"] = ""
    assert validate_summary(d) is False


# top-level missing keys
def test_missing_structured_key_fails():
    d = make_valid_summary()
    del d["structured"]
    assert validate_summary(d) is False


def test_missing_full_brief_key_fails():
    d = make_valid_summary()
    del d["fullBrief"]
    assert validate_summary(d) is False


# edge cases
def test_empty_dict_fails():
    assert validate_summary({}) is False


def test_full_brief_intro_none_fails():
    d = make_valid_summary()
    d["fullBrief"]["intro"] = None
    assert validate_summary(d) is False


def test_full_brief_closing_none_fails():
    d = make_valid_summary()
    d["fullBrief"]["closing"] = None
    assert validate_summary(d) is False


def test_sections_with_exactly_2_passes():
    assert validate_summary(make_valid_summary()) is True


def test_sections_with_4_passes():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"heading": "S1", "body": "B1."},
        {"heading": "S2", "body": "B2."},
        {"heading": "S3", "body": "B3."},
        {"heading": "S4", "body": "B4."},
    ]
    assert validate_summary(d) is True


def test_sections_with_5_fails():
    d = make_valid_summary()
    d["fullBrief"]["sections"] = [
        {"heading": "S1", "body": "B1."},
        {"heading": "S2", "body": "B2."},
        {"heading": "S3", "body": "B3."},
        {"heading": "S4", "body": "B4."},
        {"heading": "S5", "body": "B5."},
    ]
    assert validate_summary(d) is False


def test_schema_version_constant():
    from schema import SCHEMA_VERSION
    assert SCHEMA_VERSION == "4"


def test_validate_v3_digest_valid():
    from schema import validate_v3_digest
    valid = {
        "v": 3, "d": "2026-04-21", "g": "2026-04-21T10:00:00",
        "r": [], "h": []
    }
    assert validate_v3_digest(valid) is True


def test_validate_v3_digest_wrong_version():
    from schema import validate_v3_digest
    assert validate_v3_digest({"v": 2, "d": "x", "g": "x", "r": [], "h": []}) is False


def test_validate_v3_digest_missing_key():
    from schema import validate_v3_digest
    assert validate_v3_digest({"v": 3, "d": "x", "g": "x", "r": []}) is False  # missing h


def test_validate_v3_digest_with_rs():
    from schema import validate_v3_digest
    valid = {"v": 3, "d": "2026-04-21", "g": "x", "r": [], "h": [], "rs": []}
    assert validate_v3_digest(valid) is True


def test_validate_v3_digest_not_dict():
    from schema import validate_v3_digest
    assert validate_v3_digest(None) is False
    assert validate_v3_digest("string") is False
    assert validate_v3_digest([]) is False


def test_validate_v4_digest_valid():
    from schema import validate_v4_digest
    valid = {
        "v": 4, "d": "2026-04-21", "g": "2026-04-21T10:00:00",
        "r": [], "h": [], "rs": []
    }
    assert validate_v4_digest(valid) is True


def test_validate_v4_digest_wrong_version():
    from schema import validate_v4_digest
    invalid = {"v": 3, "d": "x", "g": "x", "r": [], "h": [], "rs": []}
    assert validate_v4_digest(invalid) is False


# extract_excerpt tests
from schema import extract_excerpt


def test_extract_excerpt_none_input():
    assert extract_excerpt(None) == ""


def test_extract_excerpt_empty_string():
    assert extract_excerpt("") == ""


def test_extract_excerpt_short_content_returned_as_is():
    assert extract_excerpt("Hello world.") == "Hello world."


def test_extract_excerpt_strips_html_tags():
    assert extract_excerpt("<p>Hello <b>world</b>.</p>") == "Hello world."


def test_extract_excerpt_collapses_whitespace():
    assert extract_excerpt("Hello   \n  world.") == "Hello world."


def test_extract_excerpt_truncates_at_sentence_boundary():
    content = "First sentence. Second sentence. Third sentence."
    result = extract_excerpt(content, max_chars=20)
    assert result == "First sentence."


def test_extract_excerpt_hard_truncates_with_ellipsis_when_no_boundary():
    content = "Nopunctuationhereatallandthisiswaytoolong"
    result = extract_excerpt(content, max_chars=10)
    assert result == "Nopunctuat\u2026"


def test_extract_excerpt_respects_max_chars_parameter():
    content = "Short. But this part is longer than fifty characters total."
    result = extract_excerpt(content, max_chars=50)
    assert len(result) <= 50
    assert result.endswith(".")


# parse_llm_json tests
from schema import parse_llm_json


def test_parse_llm_json_plain_json():
    assert parse_llm_json('{"key": "value"}') == {"key": "value"}


def test_parse_llm_json_fenced_json():
    text = "```json\n{\"key\": \"value\"}\n```"
    assert parse_llm_json(text) == {"key": "value"}


def test_parse_llm_json_embedded_in_prose():
    text = 'Here is the result: {"key": "value"} and that is it.'
    assert parse_llm_json(text) == {"key": "value"}


def test_parse_llm_json_invalid_json_returns_none():
    assert parse_llm_json("not json at all") is None


def test_parse_llm_json_empty_string_returns_none():
    assert parse_llm_json("") is None


def test_parse_llm_json_array_returns_none():
    assert parse_llm_json("[1, 2, 3]") is None
