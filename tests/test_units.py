"""Network-free tests for pure helpers."""

from __future__ import annotations

from ytmsplitter import auth, labels
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


def _liked():
    return [
        {"videoId": "a", "title": "Song A", "artists": ["Artist"], "album": "Album"},
        {"videoId": "b", "title": "Song B", "artists": ["Artist"], "album": "Album"},
        {"videoId": "c", "title": "Song C", "artists": ["Artist"], "album": None},
    ]


def test_export_batches_writes_prompts_and_readme(tmp_path):
    paths, missing = labels.export_batches(_liked(), {"a": "pop"}, tmp_path, batch_size=1)

    assert missing == 2
    assert len(paths) == 2
    assert paths[0].name == "batch_001.md"
    first = paths[0].read_text(encoding="utf-8")
    assert "batch 001/002" in first
    assert "Song B" in first
    assert "game_ost" in first
    assert (tmp_path / "README.md").exists()
    second = (tmp_path / "batch_002.md").read_text(encoding="utf-8")
    assert "Song A" not in second
    assert "Song C" in second


def test_export_batches_with_everything_labelled(tmp_path):
    paths, missing = labels.export_batches(
        _liked(), {"a": "pop", "b": "rock_metal", "c": "jazz"}, tmp_path
    )
    assert paths == []
    assert missing == 0


def test_import_labels_accepts_object_and_list(tmp_path):
    object_file = tmp_path / "object.json"
    object_file.write_text('{"a": "game_ost", "b": "not_a_tag", "x": "pop"}', encoding="utf-8")
    list_file = tmp_path / "list.json"
    list_file.write_text(
        '```json\n[{"videoId": "c", "label": "jazz"}]\n```',
        encoding="utf-8",
    )

    imported, errors, skipped = labels.import_labels([object_file, list_file], {"a", "b", "c"})

    assert imported == {"a": "game_ost", "c": "jazz"}
    assert errors == []
    assert skipped == {"unknown_id": 1, "unknown_label": 1, "already_labelled": 0}


def test_import_labels_reports_broken_files(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")

    imported, errors, skipped = labels.import_labels([broken], {"a"})

    assert imported == {}
    assert len(errors) == 1
    assert skipped == {"unknown_id": 0, "unknown_label": 0, "already_labelled": 0}


def test_import_labels_does_not_overwrite_by_default(tmp_path):
    path = tmp_path / "labels.json"
    path.write_text('{"a": "pop"}', encoding="utf-8")

    imported, errors, skipped = labels.import_labels([path], {"a"}, {"a": "jazz"})
    assert imported == {}
    assert errors == []
    assert skipped["already_labelled"] == 1

    imported, _, _ = labels.import_labels([path], {"a"}, {"a": "jazz"}, overwrite=True)
    assert imported == {"a": "pop"}
