import sys
sys.path.insert(0, '/Users/seintun/code/dailydigest')
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
