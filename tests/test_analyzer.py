import sys
sys.path.insert(0, '/Users/seintun/code/dailydigest')
from analyzer import _build_prompt, _parse_claude_response


# --- Fixtures ---

def make_reddit_post(idx=0, **overrides):
    base = {
        'title': f'Reddit Story {idx}',
        'url': f'https://reddit.com/r/test/{idx}',
        'score': 100 + idx,
        'comments': 50 + idx,
        'subreddit': 'ArtificialIntelligence',
    }
    base.update(overrides)
    return base


def make_hn_post(idx=0, **overrides):
    base = {
        'title': f'HN Story {idx}',
        'url': f'https://news.ycombinator.com/item?id={idx}',
        'score': 200 + idx,
        'comments': 80 + idx,
    }
    base.update(overrides)
    return base


def make_abbreviated_reddit_post(idx=0):
    """Abbreviated field names: t, u, s, c."""
    return {
        't': f'Abbrev Reddit {idx}',
        'u': f'https://reddit.com/abbrev/{idx}',
        's': 42,
        'c': 10,
        'subreddit': 'LocalLLaMA',
    }


def make_abbreviated_hn_post(idx=0):
    """Abbreviated field names: t, u, s, c."""
    return {
        't': f'Abbrev HN {idx}',
        'u': f'https://hn.example.com/{idx}',
        's': 99,
        'c': 33,
    }


# --- _build_prompt tests ---

class TestBuildPrompt:
    def test_reddit_story_ids_use_rd_prefix(self):
        reddit = [make_reddit_post(0), make_reddit_post(1)]
        prompt = _build_prompt(reddit, [])
        assert 'rd-0' in prompt
        assert 'rd-1' in prompt

    def test_hn_story_ids_use_hn_prefix(self):
        hn = [make_hn_post(0), make_hn_post(1)]
        prompt = _build_prompt([], hn)
        assert 'hn-0' in prompt
        assert 'hn-1' in prompt

    def test_reddit_subreddit_appears_in_prompt(self):
        reddit = [make_reddit_post(0, subreddit='LocalLLaMA')]
        prompt = _build_prompt(reddit, [])
        assert 'LocalLLaMA' in prompt

    def test_reddit_title_appears_in_prompt(self):
        reddit = [make_reddit_post(0, title='Unique Reddit Title XYZ')]
        prompt = _build_prompt(reddit, [])
        assert 'Unique Reddit Title XYZ' in prompt

    def test_reddit_url_appears_in_prompt(self):
        reddit = [make_reddit_post(0, url='https://reddit.com/unique-url')]
        prompt = _build_prompt(reddit, [])
        assert 'https://reddit.com/unique-url' in prompt

    def test_reddit_score_appears_in_prompt(self):
        reddit = [make_reddit_post(0, score=9999)]
        prompt = _build_prompt(reddit, [])
        assert '9999' in prompt

    def test_reddit_comments_appears_in_prompt(self):
        reddit = [make_reddit_post(0, comments=1234)]
        prompt = _build_prompt(reddit, [])
        assert '1234' in prompt

    def test_hn_title_appears_in_prompt(self):
        hn = [make_hn_post(0, title='Unique HN Title ABC')]
        prompt = _build_prompt([], hn)
        assert 'Unique HN Title ABC' in prompt

    def test_hn_url_appears_in_prompt(self):
        hn = [make_hn_post(0, url='https://hn.example.com/special')]
        prompt = _build_prompt([], hn)
        assert 'https://hn.example.com/special' in prompt

    def test_abbreviated_field_names_supported_reddit(self):
        reddit = [make_abbreviated_reddit_post(0)]
        prompt = _build_prompt(reddit, [])
        assert 'Abbrev Reddit 0' in prompt
        assert 'LocalLLaMA' in prompt

    def test_abbreviated_field_names_supported_hn(self):
        hn = [make_abbreviated_hn_post(0)]
        prompt = _build_prompt([], hn)
        assert 'Abbrev HN 0' in prompt

    def test_prompt_contains_schema_version_key(self):
        prompt = _build_prompt([make_reddit_post()], [make_hn_post()])
        assert 'schema_version' in prompt

    def test_prompt_contains_must_read_key(self):
        prompt = _build_prompt([make_reddit_post()], [make_hn_post()])
        assert 'mustRead' in prompt

    def test_prompt_contains_full_brief_key(self):
        prompt = _build_prompt([make_reddit_post()], [make_hn_post()])
        assert 'fullBrief' in prompt

    def test_prompt_contains_sections_key(self):
        prompt = _build_prompt([make_reddit_post()], [make_hn_post()])
        assert 'sections' in prompt

    def test_prompt_contains_schema_version_value_2(self):
        prompt = _build_prompt([make_reddit_post()], [make_hn_post()])
        assert '"2"' in prompt

    def test_empty_reddit_list_no_crash(self):
        prompt = _build_prompt([], [make_hn_post()])
        assert 'hn-0' in prompt

    def test_empty_hn_list_no_crash(self):
        prompt = _build_prompt([make_reddit_post()], [])
        assert 'rd-0' in prompt

    def test_both_empty_no_crash(self):
        prompt = _build_prompt([], [])
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_multiple_reddit_posts_all_appear(self):
        reddit = [make_reddit_post(i) for i in range(5)]
        prompt = _build_prompt(reddit, [])
        for i in range(5):
            assert f'rd-{i}' in prompt

    def test_multiple_hn_posts_all_appear(self):
        hn = [make_hn_post(i) for i in range(4)]
        prompt = _build_prompt([], hn)
        for i in range(4):
            assert f'hn-{i}' in prompt

    def test_output_rules_in_prompt(self):
        prompt = _build_prompt([make_reddit_post()], [])
        assert 'OUTPUT RULES' in prompt

    def test_plain_text_rule_in_prompt(self):
        prompt = _build_prompt([make_reddit_post()], [])
        assert 'plain text' in prompt.lower()


# --- _parse_claude_response tests ---

class TestParseClaudeResponse:
    VALID_JSON = '{"schema_version": "2", "simple": "Test."}'

    def test_plain_json_parses(self):
        result = _parse_claude_response(self.VALID_JSON)
        assert result == {"schema_version": "2", "simple": "Test."}

    def test_json_with_leading_trailing_whitespace(self):
        result = _parse_claude_response(f'  \n{self.VALID_JSON}\n  ')
        assert result is not None
        assert result['schema_version'] == '2'

    def test_json_fenced_with_json_tag(self):
        fenced = f'```json\n{self.VALID_JSON}\n```'
        result = _parse_claude_response(fenced)
        assert result is not None
        assert result['schema_version'] == '2'

    def test_json_fenced_with_plain_backticks(self):
        fenced = f'```\n{self.VALID_JSON}\n```'
        result = _parse_claude_response(fenced)
        assert result is not None
        assert result['schema_version'] == '2'

    def test_json_with_extra_text_parses_first_object(self):
        noisy = (
            "Here is your digest in JSON format:\n"
            f"{self.VALID_JSON}\n"
            "Let me know if you want adjustments."
        )
        result = _parse_claude_response(noisy)
        assert result is not None
        assert result['schema_version'] == '2'

    def test_malformed_json_returns_none(self):
        result = _parse_claude_response('{not valid json}')
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_claude_response('')
        assert result is None

    def test_plain_text_returns_none(self):
        result = _parse_claude_response('Here is your summary: no json here.')
        assert result is None

    def test_nested_json_preserved(self):
        nested = '{"a": {"b": [1, 2, 3]}}'
        result = _parse_claude_response(nested)
        assert result == {"a": {"b": [1, 2, 3]}}

    def test_full_summary_object_parses(self):
        full = '''{
  "schema_version": "2",
  "simple": "Summary.",
  "structured": {
    "themes": ["A", "B", "C"],
    "breaking": "News.",
    "mustRead": [
      {"id": "rd-0", "title": "T", "url": "https://a.com", "reason": "R"},
      {"id": "hn-1", "title": "T2", "url": "https://b.com", "reason": "R2"},
      {"id": "rd-2", "title": "T3", "url": "https://c.com", "reason": "R3"}
    ]
  },
  "fullBrief": {
    "intro": "Intro.",
    "sections": [
      {"heading": "S1", "body": "B1."},
      {"heading": "S2", "body": "B2."}
    ],
    "closing": "Close."
  }
}'''
        result = _parse_claude_response(full)
        assert result is not None
        assert result['schema_version'] == '2'
        assert len(result['structured']['themes']) == 3
        assert len(result['structured']['mustRead']) == 3
        assert len(result['fullBrief']['sections']) == 2
