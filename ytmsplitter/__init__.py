"""YTMSplitter — split your YouTube Music Liked Music into style playlists.

Two classification engines:

* **chips** — uses the mood/genre chips YouTube Music already computes for your
  own library. Fast, no API key and no external service.
* **ai** — an LLM labels every song with a fine-grained style, then those labels
  are grouped into a handful of playlists. Works with any OpenAI-compatible API.
"""

__version__ = "1.2.0"

__all__ = ["__version__"]
