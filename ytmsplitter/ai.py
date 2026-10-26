"""AI classification: an LLM labels every song with a fine-grained style."""

from __future__ import annotations

import collections
import json
import time
from collections.abc import Callable

import requests

from . import config as C

SYSTEM = (
    "You classify songs by style. Use your world knowledge about the artist and "
    "the track, not just the text. Reply with ONLY a JSON object mapping "
    "videoId -> label."
)

TAXONOMY = """CLOSED label set (exactly one label per song, exactly these strings):
- game_ost: video game music / VGM / chiptune / game remixes
- film_tv_ost: soundtracks for films, TV series or documentaries
- anime_jp: anime (OP/ED), J-pop, J-rock, Japanese city pop, Japanese music
- chillhop_lofi: lo-fi, chillhop, relaxed instrumental hip hop, AMV-style edits, wave
- rap_hiphop: rap, hip hop, boom bap, trap, drill (with vocals)
- rock_metal: rock, metal, punk, grunge, nu-metal, hard rock
- indie_alt: indie, alternative, bedroom pop, psychedelia, shoegaze, noise, math
- electronic_dance: EDM, house, techno, drum & bass, synthwave, electro
- phonk: phonk, drift phonk
- hardcore_experimental: breakcore, hardcore, industrial, noise, experimental
- rnb_soul_funk: R&B, soul, funk, disco, groove
- jazz: jazz, jazz-funk, bossa nova, swing
- pop: mainstream pop and pop classics
- latin_spanish: music in Spanish or Latin music (any genre)
- ambient_relax: ambient, drone, new age, relaxation/zen/sleep
- classical_orchestral: classical, orchestral, solo piano
- meme_internet: internet/meme/weird/shonk music
- other: none of the above

A game soundtrack is game_ost even if it is electronic. Anime songs are anime_jp.
Relaxed instrumental hip hop is chillhop_lofi; hip hop with rapped vocals is
rap_hiphop. Reply with ONLY the JSON, without markdown."""


def _song_line(track: dict) -> str:
    artists = "; ".join(track.get("artists") or []) or "?"
    return (
        f"{track['videoId']} :: {track['title']} — {artists} || album: {track.get('album') or '-'}"
    )


def classify_batch(
    songs: list[dict], base_url: str, api_key: str, model: str, timeout: int = C.AI_TIMEOUT
) -> dict[str, str]:
    """Classify one batch. Return ``{videoId: label}``."""
    prompt = TAXONOMY + "\n\nSongs:\n" + "\n".join(_song_line(track) for track in songs)
    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
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
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"].strip()
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
    """Classify every song in batches. Return ``{videoId: label}``."""
    batches = [liked[index : index + batch_size] for index in range(0, len(liked), batch_size)]
    labels: dict[str, str] = {}
    for index, batch in enumerate(batches, 1):
        progress(f"  batch {index}/{len(batches)} ({len(batch)} songs)")
        for attempt in range(3):
            try:
                result = classify_batch(batch, base_url, api_key, model)
                labels.update(
                    {video_id: label for video_id, label in result.items() if label in C.AI_TAGS}
                )
                break
            except Exception as exc:  # noqa: BLE001
                progress(f"    error ({attempt + 1}/3): {exc}")
                time.sleep(2 * (attempt + 1))
        time.sleep(0.3)
    return labels


def build_buckets(labels: dict[str, str]) -> collections.OrderedDict[str, list[str]]:
    """Group fine-grained labels into the final playlists (``config.AI_BUCKETS``)."""
    tag_to_bucket = {tag: bucket for bucket, tags in C.AI_BUCKETS.items() for tag in tags}
    buckets: collections.OrderedDict[str, list[str]] = collections.OrderedDict(
        (bucket, []) for bucket in C.AI_BUCKETS
    )
    for video_id, tag in labels.items():
        bucket = tag_to_bucket.get(tag)
        if bucket:
            buckets[bucket].append(video_id)
    return buckets
