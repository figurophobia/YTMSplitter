"""YTMSplitter: divide tu playlist "Me gusta" de YouTube Music en playlists por estilo.

Dos motores de clasificación:

* **chips** — usa los *chips* (mood/género) que YouTube Music ya calcula sobre tu
  propia lista. Rápido y sin dependencias externas.
* **ia** — un LLM etiqueta cada canción con un estilo fino y luego se agrupan las
  etiquetas en unas pocas playlists. Requiere una API compatible con OpenAI.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
