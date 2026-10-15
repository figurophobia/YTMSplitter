"""Cliente de la API de YouTube Music y utilidades de datos."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterator

from ytmusicapi import YTMusic
from ytmusicapi.continuations import get_continuation_token
from ytmusicapi.navigation import nav
from ytmusicapi.parsers.playlists import parse_playlist_items

from . import config as C


class AuthError(RuntimeError):
    """La sesión guardada no autentica contra YouTube Music."""


# --------------------------------------------------------------------------- #
# Sesión
# --------------------------------------------------------------------------- #
def client(auth_file: Path | None = None) -> YTMusic:
    """Devuelve un cliente autenticado a partir de ``auth.json``."""
    path = Path(auth_file or C.AUTH_FILE)
    if not path.exists():
        raise AuthError(
            f"No existe {path}. Configura la sesión primero:\n"
            "  ytmsplitter auth            # lee las cookies de Firefox\n"
            "  ytmsplitter auth --headers headers.txt"
        )
    return YTMusic(str(path))


def is_authenticated(yt: YTMusic) -> bool:
    """Comprueba el flag ``logged_in`` que devuelve la propia API."""
    try:
        resp = yt._send_request("account/account_menu", {})
    except Exception:  # noqa: BLE001
        return False
    for params in walk(resp, "params"):
        if isinstance(params, list):
            for p in params:
                if isinstance(p, dict) and p.get("key") == "logged_in":
                    return p.get("value") == "1"
    return False


def require_auth(yt: YTMusic) -> None:
    if not is_authenticated(yt):
        raise AuthError(
            "La sesión no autentica (la API responde logged_in=0).\n"
            "Suele ser caducidad de las cookies: ejecuta `ytmsplitter auth`."
        )


# --------------------------------------------------------------------------- #
# Utilidades JSON
# --------------------------------------------------------------------------- #
def walk(obj: Any, key: str) -> Iterator[Any]:
    """Recorre cualquier JSON y va devolviendo los valores bajo ``key``."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, key)


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
# Biblioteca
# --------------------------------------------------------------------------- #
def get_liked_tracks(yt: YTMusic) -> tuple[list[dict], int]:
    """Todas las canciones de "Me gusta". Devuelve (canciones, total_según_YT)."""
    playlist = yt.get_liked_songs(limit=None)
    tracks: list[dict] = []
    for t in playlist.get("tracks", []):
        if not t.get("videoId"):
            continue
        tracks.append(
            {
                "videoId": t["videoId"],
                "title": t.get("title"),
                "artists": [a["name"] for a in t.get("artists") or [] if a.get("name")],
                "album": (t.get("album") or {}).get("name"),
                "duration_seconds": t.get("duration_seconds"),
                "year": t.get("year"),
            }
        )
    return tracks, playlist.get("trackCount", 0)


def get_chips(yt: YTMusic) -> list[dict[str, str]]:
    """Chips (mood/género) de la página de "Me gusta": [{label, token}]."""
    resp = yt._send_request("browse", {"browseId": C.LIKED_BROWSE_ID})
    cloud = first(resp, "chipCloudRenderer")
    if cloud is None:
        raise AuthError(
            "La página de Me gusta no trajo chipCloudRenderer.\n"
            "Normalmente significa que la sesión no está autenticada."
        )

    chips: list[dict[str, str]] = []
    for chip in cloud.get("chips", []):
        r = chip.get("chipCloudChipRenderer", {})
        label = nav(r, ["text", "runs", 0, "text"], True)
        token = (
            nav(r, ["navigationEndpoint", "browseSectionListReloadEndpoint",
                    "continuation", "reloadContinuationData", "continuation"], True)
            or nav(r, ["navigationEndpoint", "browseSectionListReloadEndpoint",
                       "continuation", "continuation"], True)
        )
        if label and token:
            chips.append({"label": label, "token": token})
    return chips


def _shelf_contents(resp: dict) -> list:
    shelf = first(resp, "musicPlaylistShelfRenderer")
    return (shelf or {}).get("contents", []) or []


def fetch_chip_songs(yt: YTMusic, token: str, max_pages: int = 60,
                     pause: float = 0.5) -> list[dict]:
    """Todas las canciones de un chip, paginando hasta el final."""
    resp = yt._send_request("browse", {"continuation": token})
    contents = _shelf_contents(resp)
    if not contents:
        return []

    items = parse_playlist_items(contents)
    ctoken = get_continuation_token(contents) or nav(
        resp, ["continuationContents", "sectionListContinuation", "continuations", 0,
               "next", "continuation"], True)

    pages = 1
    while ctoken and pages < max_pages:
        time.sleep(pause)
        r = yt._send_request("browse", {"continuation": ctoken})
        next_items = None
        for action in walk(r, "continuationItems"):
            if isinstance(action, list) and action:
                next_items = action
                break
        if next_items is None:
            shelf = first(r, "musicPlaylistShelfRenderer")
            next_items = (shelf or {}).get("contents") if shelf else None
        if not next_items:
            break
        parsed = parse_playlist_items(next_items)
        if not parsed:
            break
        items.extend(parsed)
        ctoken = get_continuation_token(next_items)
        pages += 1
    return items


# --------------------------------------------------------------------------- #
# Playlists
# --------------------------------------------------------------------------- #
def list_playlists(yt: YTMusic) -> list[dict]:
    return yt.get_library_playlists(limit=None)


def create_playlist(yt: YTMusic, title: str, video_ids: list[str],
                    privacy: str = "PRIVATE", description: str = "") -> str:
    """Crea la playlist y añade las canciones (en lotes si hace falta)."""
    pid = yt.create_playlist(title, description, privacy_status=privacy,
                             video_ids=video_ids[:C.BATCH_ADD])
    for i in range(C.BATCH_ADD, len(video_ids), C.BATCH_ADD):
        yt.add_playlist_items(pid, video_ids[i:i + C.BATCH_ADD])
    return pid


def delete_playlists_with_prefix(yt: YTMusic, prefix: str) -> list[str]:
    removed = []
    for p in list_playlists(yt):
        if p["title"].startswith(prefix):
            yt.delete_playlist(p["playlistId"])
            removed.append(p["title"])
    return removed
