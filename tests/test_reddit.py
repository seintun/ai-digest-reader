from unittest.mock import Mock, patch

from fetchers.reddit import fetch_reddit_posts, reddit_live_fetch_globally_blocked


def _response(status_code=200, payload=None, content=b""):
    response = Mock()
    response.status_code = status_code
    response.content = content
    response.json.return_value = payload if payload is not None else {"data": {"children": []}}
    return response


def test_fetch_returns_list_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    with patch("fetchers.reddit.requests.get", return_value=_response()):
        posts = fetch_reddit_posts("ArtificialIntelligence", limit=5)
    assert isinstance(posts, list)


def test_403_falls_back_to_rss_by_default(tmp_path, monkeypatch):
    """JSON 403 is terminal for JSON endpoints, but RSS recovery runs by default."""
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.delenv("REDDIT_RSS_FALLBACK_ON_TERMINAL", raising=False)
    rss_content = b"""<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><title>RSS Story</title><link href='https://reddit.com/r/ChatGPT/comments/1/story'/></entry>
    </feed>"""
    with patch(
        "fetchers.reddit.requests.get",
        side_effect=[_response(status_code=403), _response(status_code=200, content=rss_content)],
    ) as get:
        posts = fetch_reddit_posts("ChatGPT", limit=5)

    assert len(posts) == 1
    assert posts[0]["title"] == "RSS Story"
    assert get.call_count == 2
    assert "hot.json" in get.call_args_list[0].args[0]
    assert "hot.rss" in get.call_args_list[1].args[0]


def test_403_returns_empty_when_rss_fallback_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.setenv("REDDIT_RSS_FALLBACK_ON_TERMINAL", "0")
    with patch("fetchers.reddit.requests.get", return_value=_response(status_code=403)) as get:
        posts = fetch_reddit_posts("ChatGPT", limit=5)

    assert posts == []
    assert get.call_count == 1
    assert "hot.json" in get.call_args.args[0]


def test_non_terminal_json_failure_can_fall_back_to_rss(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.delenv("REDDIT_RSS_FALLBACK_ON_TERMINAL", raising=False)
    rss_content = b"""<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><title>RSS Story</title><link href='https://reddit.com/r/test/comments/1/story'/></entry>
    </feed>"""
    with patch(
        "fetchers.reddit.requests.get",
        side_effect=[
            _response(status_code=500),
            _response(status_code=500),
            _response(status_code=200, content=rss_content),
        ],
    ) as get:
        posts = fetch_reddit_posts("test", limit=5)

    assert len(posts) == 1
    assert posts[0]["title"] == "RSS Story"
    assert get.call_count == 3
    assert "hot.rss" in get.call_args.args[0]


def test_probe_disabled_by_default_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.delenv("REDDIT_GLOBAL_BLOCK_PROBE", raising=False)
    with patch("fetchers.reddit.requests.get") as get:
        assert reddit_live_fetch_globally_blocked(["a", "b", "c"]) is False
    get.assert_not_called()


def test_probe_marks_reddit_blocked_after_terminal_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.setenv("REDDIT_GLOBAL_BLOCK_PROBE", "1")
    monkeypatch.setenv("REDDIT_GLOBAL_PROBE_COUNT", "3")
    monkeypatch.setenv("REDDIT_GLOBAL_BLOCK_THRESHOLD", "2")

    with patch("fetchers.reddit.requests.get", return_value=_response(status_code=403)) as get:
        blocked = reddit_live_fetch_globally_blocked(["a", "b", "c"])

    assert blocked is True
    assert get.call_count == 2
    assert (tmp_path / "reddit-blocks.json").exists()


def test_probe_cache_skips_network_when_block_ttl_active(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.setenv("REDDIT_GLOBAL_BLOCK_PROBE", "1")
    monkeypatch.setenv("REDDIT_GLOBAL_BLOCK_TTL_SECONDS", "600")

    with patch("fetchers.reddit.requests.get", return_value=_response(status_code=403)):
        assert reddit_live_fetch_globally_blocked(["a", "b", "c"]) is True

    with patch("fetchers.reddit.requests.get") as get:
        assert reddit_live_fetch_globally_blocked(["a", "b", "c"]) is True

    get.assert_not_called()


def test_subreddit_block_cache_skips_network(tmp_path, monkeypatch):
    monkeypatch.setenv("REDDIT_BLOCK_CACHE_PATH", str(tmp_path / "reddit-blocks.json"))
    monkeypatch.setenv("REDDIT_SUBREDDIT_BLOCK_TTL_SECONDS", "600")

    with patch("fetchers.reddit.requests.get", return_value=_response(status_code=403)):
        assert fetch_reddit_posts("ChatGPT", limit=5) == []

    with patch("fetchers.reddit.requests.get") as get:
        assert fetch_reddit_posts("ChatGPT", limit=5) == []

    get.assert_not_called()
