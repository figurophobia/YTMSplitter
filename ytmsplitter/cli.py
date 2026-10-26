"""Command-line interface for YTMSplitter."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from . import __version__, ai, api, auth
from . import config as C

OK, BAD, ARROW, DOT = "✓", "✗", "→", "•"
PRIVACY_CHOICES = ("PRIVATE", "UNLISTED", "PUBLIC")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _songs(count: int) -> str:
    return f"{count} song" if count == 1 else f"{count} songs"


def _load_liked(auto_export: bool = True) -> list[dict]:
    liked = api.load_json(C.LIKED_FILE)
    if liked:
        return liked
    if not auto_export:
        raise SystemExit(f"Missing {C.LIKED_FILE}. Run `ytmsplitter export` first.")
    print(f"{DOT} No cached library found, downloading it now…")
    return cmd_export(argparse.Namespace())


def _load_created(path: Path, legacy_keys: dict[str, str] | None = None) -> dict:
    """Load the created-playlists map and migrate legacy bucket names in place."""
    created = api.load_json(path, {}) or {}
    if not legacy_keys:
        return created
    migrated = {legacy_keys.get(key, key): value for key, value in created.items()}
    if migrated != created:
        api.save_json(path, migrated)
    return migrated


def _create_playlist_once(
    yt,
    created: dict,
    key: str,
    title: str,
    video_ids: list[str],
    dry_run: bool,
    privacy: str,
    created_file: Path,
) -> None:
    """Create a playlist unless it already exists; never duplicate it."""
    if not video_ids:
        print(f"  {DOT} {title}: no songs, skipped")
        return
    if dry_run:
        state = "already created" if key in created else "new"
        print(f"  {DOT} {title}: {_songs(len(video_ids))} ({state})")
        return
    if key in created:
        print(f"  {OK} {title}: already exists, skipped")
        return
    playlist_id = api.create_playlist(yt, title, video_ids, privacy=privacy)
    created[key] = playlist_id
    api.save_json(created_file, created)
    print(f"  {OK} {title}: {_songs(len(video_ids))} → {playlist_id}")


def _delete_chip_playlists(yt, prefixes: tuple[str, ...], confirmed: bool) -> int:
    """Delete playlists matching ``prefixes`` once the user has opted in."""
    targets = [
        playlist
        for playlist in api.list_playlists(yt)
        if any(playlist["title"].startswith(prefix) for prefix in prefixes)
    ]
    if not targets:
        return 0
    if not confirmed:
        print(f"{BAD} This would delete {len(targets)} playlist(s). Re-run with --yes to confirm.")
        return 2
    for playlist in targets:
        yt.delete_playlist(playlist["playlistId"])
        print(f"  {DOT} deleted {playlist['title']}")
    api.save_json(C.CREATED_CHIPS_FILE, {})
    return 0


def _get_client():
    yt = api.client()
    api.require_auth(yt)
    return yt


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_auth(args) -> int:
    if args.headers:
        raw = Path(args.headers).read_text(encoding="utf-8")
        path = auth.setup_from_headers(raw)
        print(f"{OK} auth.json created from {args.headers}")
    else:
        browser = args.browser or C.DEFAULT_BROWSER
        path = auth.setup_from_browser(browser)
        print(f"{OK} auth.json refreshed from {browser}")

    try:
        yt = api.client(path)
        authenticated = api.is_authenticated(yt)
    except Exception as exc:  # noqa: BLE001 - report a friendly message instead
        print(f"{BAD} could not verify the session: {exc}")
        return 1

    if authenticated:
        print(f"{OK} session authenticated")
        return 0

    print(
        f"{BAD} the session is not authenticated (logged_in=0).\n"
        "  The cookies may have expired. Try again, or paste fresh headers:\n"
        "    ytmsplitter auth --headers headers.txt"
    )
    return 1


def cmd_doctor(args) -> int:
    print(f"YTMSplitter {__version__}")
    print(f"Python {platform.python_version()} · data directory: {C.DATA_DIR}")

    print(f"\n{DOT} Session")
    has_auth = C.AUTH_FILE.exists()
    print(f"  auth.json:          {OK if has_auth else BAD}")
    authenticated = False
    if has_auth:
        try:
            authenticated = api.is_authenticated(api.client())
        except Exception:  # noqa: BLE001 - doctor must never crash on bad auth
            authenticated = False
        print(f"  authenticated:      {OK if authenticated else BAD}")

    liked = api.load_json(C.LIKED_FILE) or []
    labels = api.load_json(C.LABELS_FILE) or {}
    liked_ids = {track["videoId"] for track in liked}
    labels = {key: value for key, value in labels.items() if key in liked_ids}
    missing = len(liked_ids) - len(labels)

    print(f"\n{DOT} Library")
    print(f"  liked songs:        {len(liked)}")
    print(f"  AI labels:          {len(labels)}{f' ({missing} pending)' if missing else ''}")

    chips_created = api.load_json(C.CREATED_CHIPS_FILE, {}) or {}
    ai_created = _load_created(C.CREATED_AI_FILE, C.LEGACY_AI_BUCKETS)
    print(f"\n{DOT} Playlists created")
    print(f"  chips engine:       {len(chips_created)}")
    print(f"  AI engine:          {len(ai_created)}")

    print(f"\n{DOT} AI configuration")
    print(f"  base URL:           {C.AI_BASE_URL}")
    print(f"  model:              {C.AI_MODEL or '(not set)'}")
    print(f"  API key:            {'set' if C.AI_API_KEY else 'not set'}")

    if not authenticated:
        print(f"\n{ARROW} Run `ytmsplitter auth` to fix the session.")
    elif not liked:
        print(f"\n{ARROW} Run `ytmsplitter export` to download your Liked Music.")
    elif not chips_created and not ai_created:
        print(
            f"\n{ARROW} Run `ytmsplitter chips --create` or "
            "`ytmsplitter ai --create` to build playlists."
        )
    return 0


def cmd_export(args) -> list[dict]:
    yt = _get_client()
    print(f"{DOT} Downloading your Liked Music…")
    tracks, total = api.get_liked_tracks(yt)
    api.save_json(C.LIKED_FILE, tracks)
    print(f"{OK} {_songs(len(tracks))} → {_relative(C.LIKED_FILE)} (YouTube Music reports {total})")
    return tracks


def cmd_chips(args) -> int:
    yt = _get_client()
    liked = _load_liked()
    liked_ids = [track["videoId"] for track in liked]

    chips = api.get_chips(yt)
    if not chips:
        print(f"{BAD} no chips were found on the Liked Music page")
        return 1

    print(f"{DOT} {len(chips)} chips found")
    for chip in chips:
        chip["kind"] = (
            "mood"
            if chip["label"] in C.MOODS
            else "genre"
            if chip["label"] in C.GENRES
            else "other"
        )
    api.save_json(C.CHIPS_FILE, chips)

    by_chip: dict[str, list[str]] = {}
    for index, chip in enumerate(chips, 1):
        items = api.fetch_chip_songs(yt, chip["token"])
        video_ids = list(dict.fromkeys(item["videoId"] for item in items if item.get("videoId")))
        by_chip[chip["label"]] = video_ids
        api.save_json(C.BY_CHIP_DIR / f"{chip['label']}.json", video_ids)
        print(f"  [{index:2d}/{len(chips)}] {chip['label']:26s} {len(video_ids):4d}")

    covered = set().union(*map(set, by_chip.values())) if by_chip else set()
    uncovered = [video_id for video_id in liked_ids if video_id not in covered]
    api.save_json(
        C.SUMMARY_FILE,
        {
            "liked_total": len(liked_ids),
            "covered": len(covered),
            "uncovered": len(uncovered),
            "by_chip": {label: len(video_ids) for label, video_ids in by_chip.items()},
        },
    )
    api.save_json(C.UNCOVERED_FILE, uncovered)
    print(f"{OK} covered by a chip: {len(covered)}/{len(liked_ids)} (uncovered: {len(uncovered)})")

    if not args.create:
        print(f"{ARROW} add --create to create the playlists")
        return 0

    print(f"\n{DOT} Playlists ({'dry run' if args.dry_run else 'creating'})")
    created = _load_created(C.CREATED_CHIPS_FILE)
    for label, video_ids in by_chip.items():
        title = C.CHIPS_PREFIX + C.PLAYLIST_NAMES.get(label, label)
        _create_playlist_once(
            yt,
            created,
            label,
            title,
            video_ids,
            args.dry_run,
            args.privacy,
            C.CREATED_CHIPS_FILE,
        )
    if args.uncovered:
        title = C.CHIPS_PREFIX + "Uncovered"
        _create_playlist_once(
            yt,
            created,
            "__uncovered__",
            title,
            uncovered,
            args.dry_run,
            args.privacy,
            C.CREATED_CHIPS_FILE,
        )
    if args.dry_run:
        print(f"{ARROW} re-run without --dry-run to apply the changes")
    return 0


def cmd_ai(args) -> int:
    liked = _load_liked()
    labels = api.load_json(C.LABELS_FILE, {}) or {}
    missing = [track["videoId"] for track in liked if track["videoId"] not in labels]

    if missing:
        base_url = args.base_url or C.AI_BASE_URL
        api_key = args.api_key or C.AI_API_KEY
        model = args.model or C.AI_MODEL
        if not api_key or not model:
            print(
                f"{BAD} {_songs(len(missing))} still need labels and no AI key is set.\n"
                "  Set AI_API_KEY and AI_MODEL (and optionally AI_BASE_URL), or:\n"
                "    AI_API_KEY=… AI_MODEL=gpt-4o-mini ytmsplitter ai --create\n"
                "  Any OpenAI-compatible endpoint works, including a local one:\n"
                "    AI_API_KEY=local AI_MODEL=llama3.1 \\\n"
                "      AI_BASE_URL=http://localhost:11434/v1 ytmsplitter ai --create\n"
                "  You can also reuse an existing data/ai_labels.json."
            )
            return 2
        print(f"{DOT} Classifying with AI ({model} at {base_url})…")
        labels.update(ai.classify_all(liked, base_url, api_key, model))
        api.save_json(C.LABELS_FILE, labels)
        print(f"{OK} labelled {len(labels)}/{len(liked)} songs")

    # Ignore labels for songs that are no longer in Liked Music.
    liked_ids = {track["videoId"] for track in liked}
    labels = {key: value for key, value in labels.items() if key in liked_ids}

    buckets = ai.build_buckets(labels)
    api.save_json(C.BUCKETS_FILE, buckets)
    total = sum(len(video_ids) for video_ids in buckets.values())
    prefix = "\n" if missing else ""
    print(
        f"{prefix}{DOT} {len(buckets)} playlists, {total} assignments across {_songs(len(labels))}"
    )
    for name, video_ids in buckets.items():
        print(f"  {len(video_ids):4d}  {name}")

    if not args.create and not args.update:
        print(
            f"\n{ARROW} add --create (new playlists) or --update (add new songs) "
            "to touch your account"
        )
        return 0

    if args.dry_run:
        print(f"\n{DOT} Dry run: no changes will be made")
        if args.delete_old_chips:
            print(f"  {DOT} --delete-old-chips: deletion is skipped in a dry run")

    created = _load_created(C.CREATED_AI_FILE, C.LEGACY_AI_BUCKETS)
    yt = None

    if args.create:
        if args.delete_old_chips and not args.dry_run:
            if yt is None:
                yt = _get_client()
            prefixes = (C.CHIPS_PREFIX, *C.LEGACY_CHIPS_PREFIXES)
            result = _delete_chip_playlists(yt, prefixes, args.yes)
            if result:
                return result

        if yt is None and not args.dry_run:
            yt = _get_client()
        print(f"\n{DOT} Playlists ({'dry run' if args.dry_run else 'creating'})")
        for name, video_ids in buckets.items():
            _create_playlist_once(
                yt,
                created,
                name,
                C.AI_PREFIX + name,
                video_ids,
                args.dry_run,
                args.privacy,
                C.CREATED_AI_FILE,
            )

    if args.update:
        if yt is None:
            yt = _get_client()
        print(
            f"\n{DOT} Updating existing playlists "
            f"({'dry run' if args.dry_run else 'adding missing songs'})"
        )
        for name, video_ids in buckets.items():
            playlist_id = created.get(name)
            if not playlist_id:
                print(f"  {DOT} {name}: not created yet (use --create)")
                continue
            if args.dry_run:
                current = set(api.get_playlist_video_ids(yt, playlist_id))
                new = [video_id for video_id in video_ids if video_id not in current]
                print(f"  {DOT} {name}: {len(new)} to add of {len(video_ids)}")
            else:
                added = api.add_missing(yt, playlist_id, video_ids)
                print(
                    f"  {OK} {name}: +{_songs(added)} ({len(video_ids)} total)"
                    if added
                    else f"  {OK} {name}: already up to date"
                )

    if args.dry_run:
        print(f"{ARROW} re-run without --dry-run to apply the changes")
    return 0


def cmd_quickstart(args) -> int:
    """Authenticate, download the library and classify it in one command."""
    print(f"{DOT} YTMSplitter quickstart")

    authenticated = False
    if C.AUTH_FILE.exists():
        try:
            authenticated = api.is_authenticated(api.client())
        except Exception:  # noqa: BLE001
            authenticated = False

    if authenticated:
        print(f"{OK} session ready")
    else:
        browser = args.browser or C.DEFAULT_BROWSER
        print(
            f"{DOT} reading YouTube cookies from {browser}… "
            "(use --browser chrome, brave or edge if needed)"
        )
        path = auth.setup_from_browser(browser)
        if not api.is_authenticated(api.client(path)):
            print(
                f"{BAD} the cookies did not authenticate.\n"
                f"  Sign in at music.youtube.com in {browser}, then try again:\n"
                "    ytmsplitter quickstart\n"
                "  Using another browser?\n"
                "    ytmsplitter quickstart --browser chrome\n"
                "  Or paste request headers with `ytmsplitter auth --headers FILE`."
            )
            return 1
        print(f"{OK} session authenticated")

    liked = api.load_json(C.LIKED_FILE) or []
    if liked and not args.refresh:
        print(
            f"{OK} {_songs(len(liked))} already cached "
            f"({_relative(C.LIKED_FILE)}); use --refresh to download again"
        )
    else:
        cmd_export(args)

    engine = args.engine
    print(f"\n{DOT} Classifying with the {engine} engine")
    if engine == "ai":
        namespace = argparse.Namespace(
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
            create=args.create,
            dry_run=args.dry_run,
            privacy=args.privacy,
            delete_old_chips=args.delete_old_chips,
            yes=args.yes,
            update=args.update,
        )
        result = cmd_ai(namespace)
    else:
        namespace = argparse.Namespace(
            create=args.create,
            dry_run=args.dry_run,
            privacy=args.privacy,
            uncovered=args.uncovered,
        )
        result = cmd_chips(namespace)

    if result == 0 and not args.create and not args.update:
        print("\nNext step:")
        print(f"  ytmsplitter quickstart --engine {engine} --create")
        if engine == "ai" and not args.update:
            print("  # later, add new likes without duplicates:")
            print("  ytmsplitter ai --update")
    return result


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytmsplitter",
        description=(
            "Split your YouTube Music Liked Music playlist into playlists that actually make sense."
        ),
        epilog=(
            "examples:\n"
            "  ytmsplitter quickstart\n"
            "  ytmsplitter quickstart --engine ai --create\n"
            "  ytmsplitter chips --create --dry-run\n"
            "  ytmsplitter ai --create --privacy UNLISTED\n"
            "  ytmsplitter ai --update\n"
            "  ytmsplitter doctor\n\n"
            f"documentation: {C.PROJECT_URL}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    auth_parser = sub.add_parser(
        "auth",
        help="set up the session with browser cookies or request headers",
        description=(
            "Create data/auth.json. By default, cookies are read from Firefox. "
            "Use --browser for Chrome, Chromium, Brave, Edge, Opera, Vivaldi, "
            "LibreWolf or Safari."
        ),
    )
    auth_source = auth_parser.add_mutually_exclusive_group()
    auth_source.add_argument(
        "--browser",
        choices=C.BROWSERS,
        metavar="NAME",
        help=f"browser to read cookies from (default: {C.DEFAULT_BROWSER})",
    )
    auth_source.add_argument(
        "--headers",
        metavar="FILE",
        help="file with request headers copied from the browser",
    )
    auth_parser.set_defaults(func=cmd_auth)

    doctor_parser = sub.add_parser(
        "doctor", help="check the session, cached data and playlist status"
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    export_parser = sub.add_parser("export", help="download your Liked Music playlist")
    export_parser.set_defaults(func=cmd_export)

    def add_classification_flags(
        command: argparse.ArgumentParser, with_delete: bool = False
    ) -> None:
        command.add_argument("--create", action="store_true", help="create the playlists")
        command.add_argument(
            "--dry-run",
            action="store_true",
            help="show what would happen without changing your account",
        )
        command.add_argument(
            "--privacy",
            default="PRIVATE",
            type=str.upper,
            choices=PRIVACY_CHOICES,
            help="playlist visibility (default: PRIVATE)",
        )
        if with_delete:
            command.add_argument(
                "--delete-old-chips",
                action="store_true",
                help="delete existing 'Liked · …' playlists before creating AI ones",
            )
            command.add_argument(
                "--yes",
                action="store_true",
                help="confirm destructive actions such as --delete-old-chips",
            )

    chips_parser = sub.add_parser(
        "chips",
        help="classify with YouTube Music's native mood/genre chips (no AI key)",
        description=(
            "Use the mood/genre chips that YouTube Music already computes for "
            "your Liked Music. Works without any API key."
        ),
    )
    add_classification_flags(chips_parser)
    chips_parser.add_argument(
        "--uncovered",
        action="store_true",
        help="add a playlist with songs that no chip covers",
    )
    chips_parser.set_defaults(func=cmd_chips)

    ai_parser = sub.add_parser(
        "ai",
        help="classify with an LLM and group songs into a few playlists",
        description=(
            "Ask any OpenAI-compatible model to label each song with a "
            "fine-grained style, then group those labels into a handful of "
            "playlists. Configure it with AI_API_KEY, AI_MODEL and AI_BASE_URL."
        ),
    )
    add_classification_flags(ai_parser, with_delete=True)
    ai_parser.add_argument(
        "--update",
        action="store_true",
        help="add only new songs to playlists that already exist",
    )
    ai_parser.add_argument("--model", help="model name (default: AI_MODEL)")
    ai_parser.add_argument("--base-url", help="OpenAI-compatible endpoint (default: AI_BASE_URL)")
    ai_parser.add_argument("--api-key", help="API key (default: AI_API_KEY)")
    ai_parser.set_defaults(func=cmd_ai)

    quick_parser = sub.add_parser(
        "quickstart",
        help="one command: authenticate, download likes and classify",
        description=(
            "The easiest way to start. It reuses an existing session and cached "
            "library when possible. Add --create to create the playlists."
        ),
    )
    quick_parser.add_argument(
        "--browser",
        choices=C.BROWSERS,
        metavar="NAME",
        help=f"browser to read cookies from (default: {C.DEFAULT_BROWSER})",
    )
    quick_parser.add_argument(
        "--engine",
        choices=("chips", "ai"),
        default="chips",
        help="classification engine (default: chips, no API key needed)",
    )
    quick_parser.add_argument(
        "--refresh",
        action="store_true",
        help="download Liked Music again even if it is already cached",
    )
    quick_parser.add_argument("--create", action="store_true", help="create the playlists")
    quick_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would happen without changing your account",
    )
    quick_parser.add_argument(
        "--privacy",
        default="PRIVATE",
        type=str.upper,
        choices=PRIVACY_CHOICES,
        help="playlist visibility (default: PRIVATE)",
    )
    quick_parser.add_argument(
        "--uncovered",
        action="store_true",
        help="(chips) add a playlist with songs that no chip covers",
    )
    quick_parser.add_argument(
        "--update",
        action="store_true",
        help="(ai) add only new songs to playlists that already exist",
    )
    quick_parser.add_argument(
        "--delete-old-chips",
        action="store_true",
        help="(ai) delete existing 'Liked · …' playlists before creating AI ones",
    )
    quick_parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm destructive actions such as --delete-old-chips",
    )
    quick_parser.add_argument("--model", help="(ai) model name (default: AI_MODEL)")
    quick_parser.add_argument(
        "--base-url", help="(ai) OpenAI-compatible endpoint (default: AI_BASE_URL)"
    )
    quick_parser.add_argument("--api-key", help="(ai) API key (default: AI_API_KEY)")
    quick_parser.set_defaults(func=cmd_quickstart)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except api.AuthError as exc:
        print(f"{BAD} {exc}", file=sys.stderr)
        return 1
    except (OSError, RuntimeError) as exc:
        print(f"{BAD} {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    return 0 if isinstance(result, list) else (result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
