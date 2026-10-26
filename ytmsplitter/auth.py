"""Session setup: pasted request headers or cookies from a local browser."""

from __future__ import annotations

import contextlib
import datetime
import hashlib
from pathlib import Path

from . import config as C


def setup_from_headers(raw_headers: str, auth_file: Path | None = None) -> Path:
    """Create ``auth.json`` from the headers of an authenticated request.

    In your browser, open ``music.youtube.com``, open DevTools > Network, click
    any ``browse``/``next`` request, right-click it and choose
    *Copy > Copy request headers*.
    """
    from ytmusicapi import setup

    path = Path(auth_file or C.AUTH_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    setup(str(path), headers_raw=raw_headers)
    _chmod_600(path)
    return path


def read_browser_cookies(browser: str = C.DEFAULT_BROWSER) -> dict[str, str]:
    """Read YouTube cookies from a locally installed browser.

    Requires the optional ``browser_cookie3`` dependency. Chrome-based browsers
    may need to be closed while their cookie database is read.
    """
    browser = browser.lower()
    if browser not in C.BROWSERS:
        raise RuntimeError(
            f"Unsupported browser: {browser!r}.\nChoose one of: {', '.join(C.BROWSERS)}."
        )

    try:
        import browser_cookie3 as bc
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Reading browser cookies requires browser_cookie3:\n"
            "  pip install 'ytmsplitter[firefox]'\n"
            "  # or: pip install browser_cookie3\n"
            "You can also paste request headers instead:\n"
            "  ytmsplitter auth --headers headers.txt"
        ) from exc

    from http.cookiejar import CookieJar

    read = getattr(bc, browser, None)
    if read is None:
        raise RuntimeError(f"This browser_cookie3 version does not support {browser}.")

    jar: CookieJar = CookieJar()
    for domain in C.COOKIE_DOMAINS:
        try:
            for cookie in read(domain_name=domain):
                jar.set_cookie(cookie)
        except Exception:  # noqa: BLE001 - a missing domain is not fatal
            continue

    cookies = {cookie.name: cookie.value for cookie in jar}
    if not cookies:
        raise RuntimeError(
            f"No YouTube cookies found in {browser}.\n"
            f"Make sure you are signed in at music.youtube.com in {browser}.\n"
            "Chrome, Chromium, Brave and Edge must be fully closed while reading "
            "their cookie database. Alternatively, use --headers."
        )
    return cookies


def read_firefox_cookies() -> dict[str, str]:
    """Backwards-compatible alias for :func:`read_browser_cookies`."""
    return read_browser_cookies("firefox")


def build_browser_headers(cookies: dict[str, str]) -> str:
    """Build the header block expected by ytmusicapi's browser auth."""
    papisid = cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID")
    if not papisid:
        raise RuntimeError(
            "The session cookies are missing (__Secure-3PAPISID/SAPISID).\n"
            "Are you signed in at music.youtube.com?"
        )
    timestamp = str(int(datetime.datetime.now().timestamp()))
    digest = hashlib.sha1(f"{timestamp} {papisid} {C.ORIGIN}".encode()).hexdigest()
    cookie_header = "; ".join(f"{name}={value}" for name, value in cookies.items())
    return "\n".join(
        [
            "Cookie: " + cookie_header,
            "X-Goog-AuthUser: 0",
            f"Authorization: SAPISIDHASH {timestamp}_{digest}_u",
            f"X-Origin: {C.ORIGIN}",
            f"Origin: {C.ORIGIN}",
            f"User-Agent: {C.BROWSER_UA}",
            "X-YouTube-Client-Name: 67",
            f"X-YouTube-Client-Version: {C.CLIENT_VERSION}",
        ]
    )


def setup_from_browser(browser: str = C.DEFAULT_BROWSER, auth_file: Path | None = None) -> Path:
    """Regenerate ``auth.json`` from the current cookies of ``browser``."""
    cookies = read_browser_cookies(browser)
    return setup_from_headers(build_browser_headers(cookies), auth_file)


def setup_from_firefox(auth_file: Path | None = None) -> Path:
    """Backwards-compatible alias for :func:`setup_from_browser`."""
    return setup_from_browser("firefox", auth_file)


def _chmod_600(path: Path) -> None:
    with contextlib.suppress(OSError):  # pragma: no cover
        path.chmod(0o600)
