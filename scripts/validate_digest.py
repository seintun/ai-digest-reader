#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from schema import validate_summary, validate_v4_digest


def _all_posts(digest: dict[str, Any]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for key in ("r", "h", "rs", "o"):
        value = digest.get(key, [])
        if isinstance(value, list):
            posts.extend(post for post in value if isinstance(post, dict))
    return posts


def validate_digest_file(path: str, *, require_summary: bool = False) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        digest = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"could not read/parse digest JSON: {exc}"]

    if not validate_v4_digest(digest):
        errors.append("digest does not match v4 envelope")

    posts = _all_posts(digest)
    if not posts:
        errors.append("digest has no stories")

    summary = digest.get("summary")
    if require_summary and not summary:
        errors.append("summary is required but missing")
    if summary:
        if not validate_summary(summary):
            errors.append("summary does not match schema-v2")
        else:
            ids = {str(post.get("i", "")) for post in posts}
            urls = {str(post.get("i", "")): str(post.get("u", "")) for post in posts}
            for item in summary["structured"]["mustRead"]:
                story_id = item.get("id", "")
                if story_id not in ids:
                    errors.append(f"summary mustRead references missing story id: {story_id}")
                    continue
                expected_url = urls.get(story_id, "")
                if expected_url and item.get("url") != expected_url:
                    errors.append(f"summary mustRead URL for {story_id} does not match source story")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AI Digest JSON before deploy")
    parser.add_argument("path")
    parser.add_argument("--require-summary", action="store_true")
    args = parser.parse_args()
    ok, errors = validate_digest_file(args.path, require_summary=args.require_summary)
    if not ok:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Digest validation passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
