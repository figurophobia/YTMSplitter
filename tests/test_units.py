"""Network-free tests for pure helpers."""

from __future__ import annotations

from ytmsplitter import auth
from ytmsplitter.ai import build_buckets
from ytmsplitter.api import first, walk
from ytmsplitter.cli import _load_created, build_parser
from ytmsplitter.config import AI_BUCKETS, AI_TAGS, LEGACY_AI_BUCKETS


def test_tags_and_buckets_cover_the_same_labels():
    in_buckets = {tag for tags in AI_BUCKETS.values() for tag in tags}
    assert in_buckets == set(AI_TAGS)


def test_build_buckets_groups_and_preserves_order():
    labels = {
        "a": "game_ost",
        "b": "film_tv_ost",
        "c": "phonk",
        "d": "rock_metal",
        "e": "does_not_exist",  # ignored
    }
    buckets = build_buckets(labels)
    assert list(buckets) == list(AI_BUCKETS)  # same order as the config
    assert buckets["Video Games"] == ["a"]
    assert buckets["Film, TV & Anime"] == ["b"]
    assert buckets["Rap & Hip-hop"] == ["c"]
    assert buckets["Rock & Metal"] == ["d"]
    assert sum(len(video_ids) for video_ids in buckets.values()) == 4


def test_build_browser_headers_generates_sapisidhash():
    headers = auth.build_browser_headers(
        {
            "__Secure-3PAPISID": "test-papisid",
            "SID": "test-sid",
        }
    )
    assert "Cookie: __Secure-3PAPISID=test-papisid" in headers
    assert "SAPISIDHASH" in headers
    assert "X-Goog-AuthUser: 0" in headers


def test_build_browser_headers_without_sapisid_fails():
    import pytest

    with pytest.raises(RuntimeError):
        auth.build_browser_headers({"SID": "only-sid"})


def test_walk_and_first_traverse_nested_json():
    data = {"a": [{"k": 1}, {"x": {"k": 2}}], "k": 3}
    assert list(walk(data, "k")) == [1, 2, 3]
    assert first(data, "x") == {"k": 2}
    assert first(data, "missing") is None


def test_load_created_migrates_legacy_bucket_names(tmp_path):
    import json

    path = tmp_path / "created_ai.json"
    path.write_text(
        json.dumps(
            {
                "Videojuegos": "PL-old-1",
                "En español": "PL-old-2",
                "Rock & Metal": "PL-old-3",
            }
        ),
        encoding="utf-8",
    )

    created = _load_created(path, LEGACY_AI_BUCKETS)

    assert created == {
        "Video Games": "PL-old-1",
        "Spanish & Latin": "PL-old-2",
        "Rock & Metal": "PL-old-3",
    }
    assert json.loads(path.read_text(encoding="utf-8"))["Video Games"] == "PL-old-1"


def test_privacy_flag_accepts_lowercase():
    args = build_parser().parse_args(["chips", "--privacy", "unlisted"])
    assert args.privacy == "UNLISTED"


def test_quickstart_defaults_to_chips_engine():
    args = build_parser().parse_args(["quickstart"])
    assert args.engine == "chips"
    assert args.func.__name__ == "cmd_quickstart"
