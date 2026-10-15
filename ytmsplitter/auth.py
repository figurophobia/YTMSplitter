"""Configuración de la sesión: cabeceras pegadas o cookies de Firefox."""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from . import config as C


def setup_from_headers(raw_headers: str, auth_file: Path | None = None) -> Path:
    """Genera ``auth.json`` a partir de cabeceras de una petición autenticada.

    Copia en el navegador las cabeceras de una petición a ``music.youtube.com``
    (DevTools > Network > clic derecho sobre una petición ``browse``/``next`` >
    Copy > Copy request headers).
    """
    from ytmusicapi import setup

    path = Path(auth_file or C.AUTH_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    setup(str(path), headers_raw=raw_headers)
    _chmod_600(path)
    return path


def read_firefox_cookies() -> dict[str, str]:
    """Lee de Firefox las cookies de YouTube. Requiere ``browser_cookie3``."""
    try:
        import browser_cookie3 as bc
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Para leer las cookies de Firefox instala browser_cookie3:\n"
            "  pip install browser_cookie3\n"
            "(o usa `ytmsplitter auth --headers fichero`)"
        ) from e

    from http.cookiejar import CookieJar

    jar: CookieJar = CookieJar()
    for domain in C.COOKIE_DOMAINS:
        try:
            for c in bc.firefox(domain_name=domain):
                jar.set_cookie(c)
        except Exception:  # noqa: BLE001
            continue
    cookies = {c.name: c.value for c in jar}
    if not cookies:
        raise RuntimeError(
            "No he encontrado cookies de YouTube en Firefox. "
            "¿Estás logueado en music.youtube.com en ese navegador?"
        )
    return cookies


def build_browser_headers(cookies: dict[str, str]) -> str:
    """Construye el bloque de cabeceras que espera ytmusicapi (auth de navegador)."""
    papisid = cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID")
    if not papisid:
        raise RuntimeError(
            "Faltan las cookies de sesión (__Secure-3PAPISID/SAPISID). "
            "¿Estás logueado en music.youtube.com?"
        )
    ts = str(int(datetime.datetime.now().timestamp()))
    digest = hashlib.sha1(f"{ts} {papisid} {C.ORIGIN}".encode()).hexdigest()
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return "\n".join([
        "Cookie: " + cookie_header,
        "X-Goog-AuthUser: 0",
        f"Authorization: SAPISIDHASH {ts}_{digest}_u",
        f"X-Origin: {C.ORIGIN}",
        f"Origin: {C.ORIGIN}",
        f"User-Agent: {C.BROWSER_UA}",
        "X-YouTube-Client-Name: 67",
        f"X-YouTube-Client-Version: {C.CLIENT_VERSION}",
    ])


def setup_from_firefox(auth_file: Path | None = None) -> Path:
    """Regenera ``auth.json`` con las cookies actuales de Firefox."""
    cookies = read_firefox_cookies()
    return setup_from_headers(build_browser_headers(cookies), auth_file)


def _chmod_600(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:  # pragma: no cover
        pass
