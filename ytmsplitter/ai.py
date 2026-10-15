"""Clasificación por IA: un LLM etiqueta cada canción con un estilo fino."""

from __future__ import annotations

import collections
import json
import time
from typing import Callable

import requests

from . import config as C

SYSTEM = (
    "Clasificas canciones por estilo. Usas tu conocimiento del mundo sobre el "
    "artista y el tema, no solo el texto. Respondes SOLO con un objeto JSON que "
    "mapea videoId -> etiqueta."
)

TAXONOMY = """Etiqueta CERRADA (una sola por canción, exactamente estas cadenas):
- game_ost: música de videojuegos / VGM / chiptune / remixes de juegos
- film_tv_ost: bandas sonoras de cine, series o documentales
- anime_jp: anime (OP/ED), J-pop, J-rock, city pop japonés, música japonesa
- chillhop_lofi: lo-fi, chillhop, hip hop instrumental relajado, edits tipo AMV, wave
- rap_hiphop: rap, hip hop, boom bap, trap, drill (con voces)
- rock_metal: rock, metal, punk, grunge, nu-metal, hard rock
- indie_alt: indie, alternativo, bedroom pop, psicodelia, shoegaze, noise, math
- electronic_dance: EDM, house, techno, drum&bass, synthwave, electro
- phonk: phonk, drift phonk
- hardcore_experimental: breakcore, hardcore, industrial, noise, experimental
- rnb_soul_funk: R&B, soul, funk, disco, groove
- jazz: jazz, jazz-funk, bossa, swing
- pop: pop mainstream y clásicos pop
- latin_spanish: música en español o latina (cualquier género)
- ambient_relax: ambient, drone, new age, relax/zen/dormir
- classical_orchestral: clásica, orquestal, piano solo
- meme_internet: música de internet/meme/weird/shonk
- other: no encaja en ninguna

Si es OST de un juego -> game_ost aunque sea electrónico. Canciones de anime -> anime_jp.
Instrumental de hip hop relajado -> chillhop_lofi; con rap cantado -> rap_hiphop.
Responde SOLO con el JSON, sin markdown."""


def _song_line(t: dict) -> str:
    art = "; ".join(t.get("artists") or []) or "?"
    return f"{t['videoId']} :: {t['title']} — {art} || album: {t.get('album') or '-'}"


def classify_batch(songs: list[dict], base_url: str, api_key: str,
                   model: str, timeout: int = 180) -> dict[str, str]:
    """Clasifica un lote. Devuelve {videoId: etiqueta}."""
    prompt = TAXONOMY + "\n\nCanciones:\n" + "\n".join(_song_line(t) for t in songs)
    r = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.lower().startswith("json") else text
    return json.loads(text)


def classify_all(
    liked: list[dict],
    base_url: str,
    api_key: str,
    model: str,
    batch_size: int = C.AI_BATCH_SIZE,
    progress: Callable[[str], None] = print,
) -> dict[str, str]:
    """Clasifica todas las canciones, en lotes. Devuelve {videoId: etiqueta}."""
    batches = [liked[i:i + batch_size] for i in range(0, len(liked), batch_size)]
    labels: dict[str, str] = {}
    for i, batch in enumerate(batches, 1):
        progress(f"  lote {i}/{len(batches)} ({len(batch)} canciones)")
        for attempt in range(3):
            try:
                res = classify_batch(batch, base_url, api_key, model)
                labels.update({k: v for k, v in res.items() if v in C.AI_TAGS})
                break
            except Exception as e:  # noqa: BLE001
                progress(f"    error ({attempt + 1}/3): {e}")
                time.sleep(2 * (attempt + 1))
        time.sleep(0.3)
    return labels


def build_buckets(labels: dict[str, str]) -> "collections.OrderedDict[str, list[str]]":
    """Agrupa las etiquetas finas en las playlists finales (``config.AI_BUCKETS``)."""
    tag_to_bucket = {tag: b for b, tags in C.AI_BUCKETS.items() for tag in tags}
    buckets: collections.OrderedDict[str, list[str]] = collections.OrderedDict(
        (b, []) for b in C.AI_BUCKETS
    )
    for vid, tag in labels.items():
        bucket = tag_to_bucket.get(tag)
        if bucket:
            buckets[bucket].append(vid)
    return buckets
