"""Tests que no tocan la red (utilidades puras)."""

from __future__ import annotations

from ytmsplitter import auth
from ytmsplitter.ai import build_buckets
from ytmsplitter.api import first, walk
from ytmsplitter.config import AI_BUCKETS, AI_TAGS


def test_tags_y_buckets_cubren_lo_mismo():
    en_buckets = {t for tags in AI_BUCKETS.values() for t in tags}
    assert en_buckets == set(AI_TAGS)


def test_build_buckets_agrupa_y_conserva_orden():
    labels = {
        "a": "game_ost",
        "b": "film_tv_ost",
        "c": "phonk",
        "d": "rock_metal",
        "e": "no_existe",  # se ignora
    }
    buckets = build_buckets(labels)
    assert list(buckets) == list(AI_BUCKETS)  # mismo orden que la config
    assert buckets["Videojuegos"] == ["a"]
    assert buckets["Cine, series y anime"] == ["b"]
    assert buckets["Rap & Hip-hop"] == ["c"]
    assert buckets["Rock & Metal"] == ["d"]
    assert sum(len(v) for v in buckets.values()) == 4


def test_build_browser_headers_genera_sapisidhash():
    headers = auth.build_browser_headers({
        "__Secure-3PAPISID": "papisid-de-prueba",
        "SID": "sid-de-prueba",
    })
    assert "Cookie: __Secure-3PAPISID=papisid-de-prueba" in headers
    assert "SAPISIDHASH" in headers
    assert "X-Goog-AuthUser: 0" in headers


def test_build_browser_headers_sin_sapisid_falla():
    import pytest
    with pytest.raises(RuntimeError):
        auth.build_browser_headers({"SID": "solo-sid"})


def test_walk_y_first_recorren_json_anidado():
    data = {"a": [{"k": 1}, {"x": {"k": 2}}], "k": 3}
    assert list(walk(data, "k")) == [1, 2, 3]
    assert first(data, "x") == {"k": 2}
    assert first(data, "no_existe") is None
