from unittest.mock import Mock, patch

from fetchers.hn import fetch_hn_top_comments, strip_html


def _items_response(children=None, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {
        "id": 123,
        "title": "A story",
        "children": children or [],
    }
    return response


def _comment(text, author="alice", children=None):
    return {"type": "comment", "text": text, "author": author, "children": children or []}


def test_strip_html_removes_tags():
    assert strip_html("<p>hello <b>world</b></p>") == "hello world"


def test_strip_html_unescapes_entities():
    assert strip_html("&gt;quoted &#x2F; slash &amp; amp") == ">quoted / slash & amp"


def test_fetch_top_comments_returns_flattened_text():
    children = [
        _comment("<p>first top comment</p>", author="u1"),
        _comment("<p>second top comment</p>", author="u2"),
        {"type": "comment", "text": "", "author": "empty"},  # skipped: no text
    ]
    with patch("fetchers.hn.requests.get", return_value=_items_response(children)):
        comments = fetch_hn_top_comments(123, limit=5)

    assert len(comments) == 2
    assert comments[0]["author"] == "u1"
    assert "first top comment" in comments[0]["text"]
    assert "<p>" not in comments[0]["text"]


def test_fetch_top_comments_respects_limit():
    children = [_comment(f"<p>comment {i}</p>") for i in range(10)]
    with patch("fetchers.hn.requests.get", return_value=_items_response(children)):
        comments = fetch_hn_top_comments(123, limit=3)
    assert len(comments) == 3


def test_fetch_top_comments_includes_shallow_replies():
    nested = _comment("<p>parent</p>", author="p", children=[
        _comment("<p>reply</p>", author="r"),
    ])
    with patch("fetchers.hn.requests.get", return_value=_items_response([nested])):
        comments = fetch_hn_top_comments(123, limit=10)
    authors = [c["author"] for c in comments]
    assert "p" in authors
    assert "r" in authors


def test_fetch_top_comments_returns_empty_on_http_error():
    with patch("fetchers.hn.requests.get", return_value=_items_response(status_code=500)):
        assert fetch_hn_top_comments(123) == []


def test_fetch_top_comments_returns_empty_on_network_error():
    import requests as req
    with patch("fetchers.hn.requests.get", side_effect=req.RequestException):
        assert fetch_hn_top_comments(123) == []


def test_fetch_top_comments_truncates_long_text():
    long_text = "<p>" + ("word " * 500) + "</p>"
    with patch("fetchers.hn.requests.get", return_value=_items_response([_comment(long_text)])):
        comments = fetch_hn_top_comments(123, limit=1)
    assert len(comments) == 1
    assert len(comments[0]["text"]) <= 500
