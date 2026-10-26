"""YouTube Music API client and small data helpers."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ytmusicapi import YTMusic
from ytmusicapi.continuations import get_continuation_token
from ytmusicapi.navigation import nav
from ytmusicapi.parsers.playlists import parse_playlist_items

from . import config as C


class AuthError(RuntimeError):
    """The stored session is not authenticated against YouTube Music."""


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #
def client(auth_file: Path | None = None) -> YTMusic:
    """Return an authenticated client built from ``auth.json``."""
    path = Path(auth_file or C.AUTH_FILE)
    if not path.exists():
        raise AuthError(
            f"{path} does not exist. Set up your session first:\n"
            "  ytmsplitter auth                    # read cookies from Firefox\n"
            "  ytmsplitter auth --browser chrome   # or another browser\n"
            "  ytmsplitter auth --headers headers.txt"
        )
    return YTMusic(str(path))


def is_authenticated(yt: YTMusic) -> bool:
    """Check the ``logged_in`` flag returned by the API itself."""
    try:
        response = yt._send_request("account/account_menu", {})
    except Exception:  # noqa: BLE001
        return False
    for params in walk(response, "params"):
        if isinstance(params, list):
            for param in params:
                if isinstance(param, dict) and param.get("key") == "logged_in":
                    return param.get("value") == "1"
    return False


def require_auth(yt: YTMusic) -> None:
    if not is_authenticated(yt):
        raise AuthError(
            "The session is not authenticated (the API returns logged_in=0).\n"
            "This usually means the cookies expired. Run `ytmsplitter auth` again."
        )


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #
def walk(obj: Any, key: str) -> Iterator[Any]:
    """Yield every value stored under ``key`` in an arbitrarily nested JSON object."""
    if isinstance(obj, dict):
        for k, value in obj.items():
            if k == key:
                yield value
            yield from walk(value, key)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value, key)


def first(obj: Any, key: str) -> Any | None:
    return next(walk(obj, key), None)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def load_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Library
# --------------------------------------------------------------------------- #
def get_liked_tracks(yt: YTMusic) -> tuple[list[dict], int]:
    """Return every song in "Liked Music" as ``(tracks, total_reported_by_yt)``."""
    playlist = yt.get_liked_songs(limit=None)
    tracks: list[dict] = []
    for track in playlist.get("tracks", []):
        if not track.get("videoId"):
            continue
        tracks.append(
            {
                "videoId": track["videoId"],
                "title": track.get("title"),
                "artists": [
                    artist["name"] for artist in track.get("artists") or [] if artist.get("name")
                ],
                "album": (track.get("album") or {}).get("name"),
                "duration_seconds": track.get("duration_seconds"),
                "year": track.get("year"),
            }
        )
    return tracks, playlist.get("trackCount", 0)


def get_chips(yt: YTMusic) -> list[dict[str, str]]:
    """Return the mood/genre chips on the "Liked Music" page."""
    response = yt._send_request("browse", {"browseId": C.LIKED_BROWSE_ID})
    cloud = first(response, "chipCloudRenderer")
    if cloud is None:
        raise AuthError(
            "The Liked Music page did not return a chipCloudRenderer.\n"
            "This usually means the session is not authenticated."
        )

    chips: list[dict[str, str]] = []
    for chip in cloud.get("chips", []):
        renderer = chip.get("chipCloudChipRenderer", {})
        label = nav(renderer, ["text", "runs", 0, "text"], True)
        token = nav(
            renderer,
            [
                "navigationEndpoint",
                "browseSectionListReloadEndpoint",
                "continuation",
                "reloadContinuationData",
                "continuation",
            ],
            True,
        ) or nav(
            renderer,
            [
                "navigationEndpoint",
                "browseSectionListReloadEndpoint",
                "continuation",
                "continuation",
            ],
            True,
        )
        if label and token:
            chips.append({"label": label, "token": token})
    return chips


def _shelf_contents(response: dict) -> list:
    shelf = first(response, "musicPlaylistShelfRenderer")
    return (shelf or {}).get("contents", []) or []


def fetch_chip_songs(
    yt: YTMusic, token: str, max_pages: int = 60, pause: float = 0.5
) -> list[dict]:
    """Return every song for a chip, following pagination until the end."""
    response = yt._send_request("browse", {"continuation": token})
    contents = _shelf_contents(response)
    if not contents:
        return []

    items = parse_playlist_items(contents)
    continuation = get_continuation_token(contents) or nav(
        response,
        [
            "continuationContents",
            "sectionListContinuation",
            "continuations",
            0,
            "next",
            "continuation",
        ],
        True,
    )

    pages = 1
    while continuation and pages < max_pages:
        time.sleep(pause)
        page = yt._send_request("browse", {"continuation": continuation})
        next_items = None
        for action in walk(page, "continuationItems"):
            if isinstance(action, list) and action:
                next_items = action
                break
        if next_items is None:
            shelf = first(page, "musicPlaylistShelfRenderer")
            next_items = (shelf or {}).get("contents") if shelf else None
        if not next_items:
            break
        parsed = parse_playlist_items(next_items)
        if not parsed:
            break
        items.extend(parsed)
        continuation = get_continuation_token(next_items)
        pages += 1
    return items


# --------------------------------------------------------------------------- #
# Playlists
# --------------------------------------------------------------------------- #
def list_playlists(yt: YTMusic) -> list[dict]:
    return yt.get_library_playlists(limit=None)


def create_playlist(
    yt: YTMusic, title: str, video_ids: list[str], privacy: str = "PRIVATE", description: str = ""
) -> str:
    """Create a playlist and add its songs, in batches when necessary."""
    playlist_id = yt.create_playlist(
        title, description, privacy_status=privacy, video_ids=video_ids[: C.BATCH_ADD]
    )
    for index in range(C.BATCH_ADD, len(video_ids), C.BATCH_ADD):
        yt.add_playlist_items(playlist_id, video_ids[index : index + C.BATCH_ADD])
    return playlist_id


def get_playlist_video_ids(yt: YTMusic, playlist_id: str) -> list[str]:
    """Return the videoIds already present in a playlist."""
    playlist = yt.get_playlist(playlist_id, limit=None)
    return [track["videoId"] for track in playlist.get("tracks", []) if track.get("videoId")]


def add_missing(yt: YTMusic, playlist_id: str, video_ids: list[str]) -> int:
    """Add only songs that are not in the playlist yet. Return how many were added."""
    current = set(get_playlist_video_ids(yt, playlist_id))
    to_add = [video_id for video_id in video_ids if video_id not in current]
    for index in range(0, len(to_add), C.BATCH_ADD):
        yt.add_playlist_items(playlist_id, to_add[index : index + C.BATCH_ADD])
    return len(to_add)


def delete_playlists_with_prefix(yt: YTMusic, prefix: str) -> list[str]:
    """Delete every library playlist whose title starts with ``prefix``."""
    removed = []
    for playlist in list_playlists(yt):
        if playlist["title"].startswith(prefix):
            yt.delete_playlist(playlist["playlistId"])
            removed.append(playlist["title"])
    return removed
