"""Rutas, constantes y configuración de YTMSplitter."""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Rutas
# --------------------------------------------------------------------------- #
DATA_DIR = Path(os.environ.get("YTMSPLITTER_DATA", "data")).expanduser().resolve()

AUTH_FILE = DATA_DIR / "auth.json"
HEADERS_FILE = DATA_DIR / "raw_headers.txt"
LIKED_FILE = DATA_DIR / "liked.json"

CHIPS_FILE = DATA_DIR / "chips.json"
BY_CHIP_DIR = DATA_DIR / "by_chip"
UNCOVERED_FILE = DATA_DIR / "uncovered_ids.json"
SUMMARY_FILE = DATA_DIR / "summary.json"
CREATED_CHIPS_FILE = DATA_DIR / "created_chips.json"

LABELS_FILE = DATA_DIR / "ai_labels.json"
BUCKETS_FILE = DATA_DIR / "ai_buckets.json"
CREATED_AI_FILE = DATA_DIR / "created_ai.json"

# Identificador interno de la playlist "Me gusta" en YouTube Music.
LIKED_BROWSE_ID = "VLLM"
LIKED_PLAYLIST_ID = "LM"

BATCH_ADD = 100  # canciones por llamada al añadir a una playlist

# --------------------------------------------------------------------------- #
# Motor "chips": etiquetas nativas de YT Music -> nombre de playlist
# --------------------------------------------------------------------------- #
CHIPS_PREFIX = "Me gusta · "

PLAYLIST_NAMES: dict[str, str] = {
    "Chill": "Chill",
    "Party": "Fiesta",
    "Focus": "Concentración",
    "Romance": "Romance",
    "Pump-up": "Motivación",
    "Sleep": "Para dormir",
    "Downbeat": "Downbeat",
    "Upbeat": "Upbeat",
    "Indie music": "Indie",
    "Hip-hop": "Hip-hop",
    "Rock": "Rock",
    "Pop music": "Pop",
    "J-pop": "J-pop",
    "Soundtrack": "Bandas sonoras",
    "Video game music": "Videojuegos",
    "Electronic dance music": "Electrónica",
}

MOODS = {"Chill", "Party", "Focus", "Romance", "Pump-up", "Sleep", "Downbeat", "Upbeat"}
GENRES = set(PLAYLIST_NAMES) - MOODS

# --------------------------------------------------------------------------- #
# Motor "ia": estilos finos y su agrupación en pocas playlists
# --------------------------------------------------------------------------- #
AI_PREFIX = "IA · "

#: Estilos finos que debe devolver el LLM (una etiqueta por canción).
AI_TAGS: list[str] = [
    "game_ost", "film_tv_ost", "anime_jp", "chillhop_lofi", "rap_hiphop",
    "rock_metal", "indie_alt", "electronic_dance", "phonk", "hardcore_experimental",
    "rnb_soul_funk", "jazz", "pop", "latin_spanish", "ambient_relax",
    "classical_orchestral", "meme_internet", "other",
]

#: Agrupación de etiquetas finas -> playlists finales (menos de 10).
#: Cámbiala a tu gusto y vuelve a ejecutar `ytmsplitter ai --create`.
AI_BUCKETS: dict[str, list[str]] = {
    "Videojuegos": ["game_ost"],
    "Cine, series y anime": ["film_tv_ost", "anime_jp", "classical_orchestral"],
    "Chillhop & Lo-fi": ["chillhop_lofi"],
    "Rap & Hip-hop": ["rap_hiphop", "phonk"],
    "Rock & Metal": ["rock_metal", "hardcore_experimental"],
    "Indie & Alternativo": ["indie_alt"],
    "Pop, Soul & Jazz": ["pop", "rnb_soul_funk", "jazz"],
    "En español": ["latin_spanish"],
    "Electrónica, ambiente y memes": ["electronic_dance", "ambient_relax",
                                      "meme_internet", "other"],
}

# --------------------------------------------------------------------------- #
# IA (LLM)
# --------------------------------------------------------------------------- #
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
AI_API_KEY = os.environ.get("AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL")
AI_BATCH_SIZE = 80

# --------------------------------------------------------------------------- #
# Navegador (auth desde cookies)
# --------------------------------------------------------------------------- #
ORIGIN = "https://music.youtube.com"
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0"
CLIENT_VERSION = "1.20261013.15.00"
COOKIE_DOMAINS = ("youtube.com", "music.youtube.com")
